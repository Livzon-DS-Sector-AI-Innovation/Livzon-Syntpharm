"""单条授权判定核心逻辑。

铁律（《权限体系设计对比报告》第五节）：动作权限与数据范围必须落在
同一条用户角色授权内同时满足，禁止「先合并所有动作权限、再合并所有
数据范围」的交叉组合。因此判定返回的 PermissionContext 只携带
「授予了目标权限码」的那些授权，数据范围过滤只基于这些授权。

2026-10: 接入 Redis 缓存（默认 60 秒 TTL），生效权限码集合与超管标记
缓存到 `perm:user:{id}:codes/super`，变更接口主动驱逐。
"""

import logging
from dataclasses import dataclass, field

from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException
from app.platform.identity.models import User
from app.platform.permission.models import UserRoleGrant
from app.platform.permission.repository import GrantRepository

logger = logging.getLogger(__name__)


@dataclass
class PermissionContext:
    """一次权限判定结果：用户 + 授予目标权限码的授权集合。"""

    user: User
    permission_code: str
    grants: list[UserRoleGrant] = field(default_factory=list)
    is_superuser: bool = False
    degraded: bool = False  # 权限表未迁移时的降级标记（仅登录）


def _is_missing_permission_table(exc: BaseException) -> bool:
    """判断异常是否为「permission schema 未迁移」。"""
    orig = getattr(exc, "orig", None)
    if orig is not None and orig.__class__.__name__ == "UndefinedTableError":
        return True
    message = str(orig if orig is not None else exc)
    return "does not exist" in message and "permission" in message


def _detach_user(db: AsyncSession, user: User) -> None:
    """把 user 从 session 摘出。

    原因：rollback 会 expire session 中所有 ORM 对象，之后调用方访问
    `ctx.user.id` 等属性会触发同步 IO（MissingGreenlet）。摘出后属性保持
    已加载状态，不再受影响。
    """
    try:
        if user in db:
            db.expunge(user)
    except Exception:  # noqa: BLE001 - 保护性操作，失败不影响主流程
        logger.warning("detach user failed during permission degradation", exc_info=True)


async def is_superuser_with_cache(db: AsyncSession, user: User) -> bool:
    """带缓存的超管判定。"""
    from app.platform.permission.cache import (
        get_cached_is_superuser,
        set_cached_is_superuser,
    )

    cached = await get_cached_is_superuser(user.id)
    if cached is not None:
        return cached
    result = await GrantRepository().is_superuser(db, user)
    await set_cached_is_superuser(user.id, result)
    return result


async def build_permission_context(
    db: AsyncSession,
    user: User,
    permission_code: str,
) -> PermissionContext:
    """构建权限上下文。无权限时抛 ForbiddenException。

    降级：权限表尚未迁移（权限体系未部署）时，退化为「仅登录」并记 ERROR 日志；
    迁移后自动恢复严格判定。不做静默放行——日志会明确提示需要执行的迁移。
    """
    from app.platform.permission.service.management import effective_permission_codes

    try:
        is_superuser = await is_superuser_with_cache(db, user)
    except ProgrammingError as exc:
        if not _is_missing_permission_table(exc):
            raise
        _detach_user(db, user)
        await db.rollback()
        logger.error(
            "权限表不存在（permission schema 未迁移），权限判定降级为仅登录；"
            "请执行: alembic upgrade 0082_create_permission_schema",
        )
        return PermissionContext(user=user, permission_code=permission_code, degraded=True)

    if is_superuser:
        return PermissionContext(user=user, permission_code=permission_code, is_superuser=True)

    try:
        codes = await effective_permission_codes(db, user)
    except ProgrammingError as exc:
        if not _is_missing_permission_table(exc):
            raise
        _detach_user(db, user)
        await db.rollback()
        logger.error(
            "权限表不存在（permission schema 未迁移），权限判定降级为仅登录；"
            "请执行: alembic upgrade 0082_create_permission_schema",
        )
        return PermissionContext(user=user, permission_code=permission_code, degraded=True)

    if permission_code not in codes:
        raise ForbiddenException(f"缺少权限：{permission_code}")

    # 缓存命中时仍需要具体授权以支持数据范围
    repo = GrantRepository()
    grants = await repo.get_grants_for_permission(db, user.id, permission_code)
    if not grants:
        raise ForbiddenException(f"缺少权限：{permission_code}")

    return PermissionContext(user=user, permission_code=permission_code, grants=grants)


async def has_permission(db: AsyncSession, user: User, permission_code: str) -> bool:
    """布尔查询：用户是否拥有某权限码（不抛异常）。"""
    from app.platform.permission.service.management import effective_permission_codes

    try:
        codes = await effective_permission_codes(db, user)
    except ProgrammingError as exc:
        if not _is_missing_permission_table(exc):
            raise
        _detach_user(db, user)
        await db.rollback()
        logger.error("权限表不存在，has_permission 降级为 True（请执行迁移 0082）")
        return True
    return permission_code in codes
