"""权限判定缓存层。

把用户维度的权限快照缓存到 Redis，减少每次请求都重查授权表的开销。
缓存内容：
- `perm:user:{user_id}:super` → 是否超级管理员
- `perm:user:{user_id}:codes` → 当前生效权限码集合（JSON 列表）

失效策略：
- 写 TTL（默认 60 秒），兜底自动过期。
- 授权/角色变更时主动驱逐相关用户的缓存。
- Redis 不可用时降级为直接查库，不阻塞业务。
"""

import json
import logging
import uuid
from typing import cast

from app.core.redis import cache_delete, cache_get, cache_set

logger = logging.getLogger(__name__)

_CACHE_PREFIX = "perm:user"
_CODES_SUFFIX = "codes"
_SUPER_SUFFIX = "super"
_DEFAULT_TTL = 60


def _codes_key(user_id: uuid.UUID) -> str:
    return f"{_CACHE_PREFIX}:{user_id}:{_CODES_SUFFIX}"


def _super_key(user_id: uuid.UUID) -> str:
    return f"{_CACHE_PREFIX}:{user_id}:{_SUPER_SUFFIX}"


async def get_cached_permission_codes(user_id: uuid.UUID) -> set[str] | None:
    try:
        raw = await cache_get(_codes_key(user_id))
    except Exception:  # noqa: BLE001 - Redis 故障时降级
        logger.warning("读取权限码缓存失败，降级为查库", exc_info=True)
        return None

    if raw is None:
        return None
    try:
        return set(json.loads(raw))
    except json.JSONDecodeError:
        logger.warning("权限码缓存格式异常，忽略缓存")
        return None


async def set_cached_permission_codes(user_id: uuid.UUID, codes: set[str]) -> None:
    try:
        await cache_set(_codes_key(user_id), json.dumps(sorted(codes)), ex=_DEFAULT_TTL)
    except Exception:  # noqa: BLE001
        logger.warning("写入权限码缓存失败", exc_info=True)


async def get_cached_is_superuser(user_id: uuid.UUID) -> bool | None:
    try:
        raw = await cache_get(_super_key(user_id))
    except Exception:  # noqa: BLE001
        logger.warning("读取超管缓存失败，降级为查库", exc_info=True)
        return None

    if raw is None:
        return None
    return raw == "1"


async def set_cached_is_superuser(user_id: uuid.UUID, value: bool) -> None:
    try:
        await cache_set(_super_key(user_id), "1" if value else "0", ex=_DEFAULT_TTL)
    except Exception:  # noqa: BLE001
        logger.warning("写入超管缓存失败", exc_info=True)


async def evict_user_permission_cache(user_id: uuid.UUID) -> None:
    """驱逐单个用户的权限缓存。"""
    try:
        await cache_delete(_codes_key(user_id))
        await cache_delete(_super_key(user_id))
    except Exception:  # noqa: BLE001
        logger.warning("驱逐权限缓存失败", exc_info=True)
