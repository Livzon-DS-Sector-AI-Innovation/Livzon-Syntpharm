"""会话管理：基于 JWT `jti` 的 Redis 索引与吊销（踢下线）。

设计：
- 登录成功时用 `record_session` 把 `jti → 会话信息` 写入 Redis，并按用户建索引；
- 踢下线 = `revoke_session` 删除会话并写入吊销黑名单（TTL 覆盖 token 剩余有效期）；
- 认证依赖 `get_current_user` 在解析 JWT 后查 `is_session_revoked`，命中即视为未登录。
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.redis import get_redis
from app.platform.identity.models import User

logger = logging.getLogger(__name__)

SESSION_PREFIX = "session:"
USER_SESSIONS_PREFIX = "user_sessions:"
REVOKED_PREFIX = "revoked_jti:"


def _ttl() -> int:
    return int(get_settings().JWT_EXPIRE_SECONDS)


def _session_data(jti: str, user: User, ip_address: str | None, user_agent: str | None) -> dict[str, Any]:
    return {
        "jti": jti,
        "user_id": str(user.id),
        "name": user.name,
        "username": user.username,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "created_at": datetime.now(UTC).isoformat(),
    }


async def record_session(*, jti: str, user: User, ip_address: str | None, user_agent: str | None) -> None:
    """登录成功后登记一个在线会话（jti 索引）。"""
    r = await get_redis()
    ttl = _ttl()
    payload = json.dumps(_session_data(jti, user, ip_address, user_agent), ensure_ascii=False)
    await r.set(f"{SESSION_PREFIX}{jti}", payload, ex=ttl)
    await r.sadd(f"{USER_SESSIONS_PREFIX}{user.id}", jti)
    await r.expire(f"{USER_SESSIONS_PREFIX}{user.id}", ttl)


def _jti_str(value: bytes | str) -> str:
    """Redis 集合成员可能是 bytes，统一转成 str 再拼 key。"""
    return value.decode() if isinstance(value, bytes) else value


async def list_user_sessions(user_id: Any) -> list[dict[str, Any]]:
    """列出某用户的在线会话（按登录时间倒序）。"""
    r = await get_redis()
    jtis = await r.smembers(f"{USER_SESSIONS_PREFIX}{user_id}")
    sessions: list[dict[str, Any]] = []
    for jti in jtis:
        raw = await r.get(f"{SESSION_PREFIX}{_jti_str(jti)}")
        if raw:
            sessions.append(json.loads(raw))
    sessions.sort(key=lambda s: s.get("created_at", ""), reverse=True)
    return sessions


async def list_all_sessions() -> list[dict[str, Any]]:
    """列出全部在线会话（运维/审计用）。"""
    r = await get_redis()
    sessions: list[dict[str, Any]] = []
    async for key in r.scan_iter(match=f"{SESSION_PREFIX}*"):
        raw = await r.get(key)
        if raw:
            sessions.append(json.loads(raw))
    sessions.sort(key=lambda s: s.get("created_at", ""), reverse=True)
    return sessions


async def _record_revocation_persistent(jti: str, user_id: str | None) -> None:
    """吊销记录落库（Redis 故障时认证侧降级查库的兜底），并顺手清理已过期记录。"""
    from datetime import timedelta
    from uuid import UUID

    from sqlalchemy import delete, select

    from app.core.database import async_session_factory
    from app.platform.identity.models import RevokedSession

    expires_at = datetime.now(UTC) + timedelta(seconds=_ttl())
    async with async_session_factory() as db:
        exists = await db.scalar(select(RevokedSession.id).where(RevokedSession.jti == jti))
        if not exists:
            db.add(
                RevokedSession(
                    jti=jti,
                    user_id=UUID(user_id) if user_id else None,
                    expires_at=expires_at,
                )
            )
        # 惰性清理已过期记录（expires_at 有索引，代价低）
        await db.execute(delete(RevokedSession).where(RevokedSession.expires_at < datetime.now(UTC)))
        await db.commit()


async def revoke_session(jti: str) -> None:
    """吊销单个会话（删会话 + 从用户索引移除 + 写吊销黑名单 + 持久化吊销记录）。"""
    r = await get_redis()
    raw = await r.get(f"{SESSION_PREFIX}{jti}")
    user_id: str | None = None
    if raw:
        data = json.loads(raw)
        user_id = data.get("user_id")
        if user_id:
            await r.srem(f"{USER_SESSIONS_PREFIX}{user_id}", jti)
    await r.delete(f"{SESSION_PREFIX}{jti}")
    await r.set(f"{REVOKED_PREFIX}{jti}", "1", ex=_ttl())

    # 吊销记录落库：失败不阻塞吊销（Redis 黑名单仍是主存储），只记日志
    try:
        await _record_revocation_persistent(jti, user_id)
    except Exception:
        logger.warning("会话吊销记录落库失败 jti=%s", jti, exc_info=True)


async def revoke_all_user_sessions(user_id: Any) -> int:
    """吊销某用户的全部会话，返回吊销数量。"""
    r = await get_redis()
    jtis = await r.smembers(f"{USER_SESSIONS_PREFIX}{user_id}")
    for jti in jtis:
        await revoke_session(_jti_str(jti))
    return len(jtis)


async def is_session_revoked(jti: str | None, db: AsyncSession | None = None) -> bool:
    """jti 是否已被吊销（旧 token 无 jti 时返回 False，向后兼容）。

    fail-closed：Redis 故障时降级查 `identity.revoked_sessions` 持久化吊销记录；
    查库也失败则向上抛异常（认证依赖层不做兜底放行）。
    """
    if not jti:
        return False
    try:
        r = await get_redis()
        return bool(await r.exists(f"{REVOKED_PREFIX}{jti}"))
    except Exception:
        logger.warning("会话吊销黑名单 Redis 不可用，降级查库判定", exc_info=True)

    from sqlalchemy import select

    from app.core.database import async_session_factory
    from app.platform.identity.models import RevokedSession

    async def _query_db(session: AsyncSession) -> bool:
        found = await session.scalar(
            select(RevokedSession.id).where(
                RevokedSession.jti == jti,
                RevokedSession.expires_at > datetime.now(UTC),
            )
        )
        return found is not None

    if db is not None:
        return await _query_db(db)
    async with async_session_factory() as own_db:
        return await _query_db(own_db)
