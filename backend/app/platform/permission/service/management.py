"""权限服务：注册表同步 + 初始超管挂载 + 授权/角色业务规则。

sync_registry 是「代码注册表为唯一权威、DB 只读镜像」的落地：
启动时幂等同步，不物理删除、不复活已退役项。
"""

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.core.exceptions import ForbiddenException
from app.platform.identity.models import User
from app.platform.permission.models import (
    GRANT_ACTIVE,
    PERMISSION_ACTIVE,
    SCOPE_ALL,
    SCOPE_SELF,
    ApiBinding,
    Permission,
    Role,
    RolePermission,
    UserRoleGrant,
)
from app.platform.permission.registry import (
    ALL_BUILTIN_ROLES,
    ALL_PERMISSIONS,
    API_BINDINGS,
    BUILTIN_ROLE_PERMISSIONS,
)
from app.platform.permission.repository import GrantRepository, RoleRepository

logger = logging.getLogger(__name__)


async def _get_permission_by_code(db: AsyncSession, code: str) -> Permission | None:
    result = await db.execute(
        select(Permission).where(
            Permission.code == code,
            Permission.is_deleted == False,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def _get_role_by_code(db: AsyncSession, code: str) -> Role | None:
    result = await db.execute(
        select(Role).where(
            Role.code == code,
            Role.is_deleted == False,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def sync_registry() -> None:
    """幂等同步 registry 声明到 DB（权限码 / 角色 / 角色权限 / 接口绑定）。"""
    async with async_session_factory() as db:
        await _sync_permissions(db)
        await _sync_roles(db)
        await _sync_role_permissions(db)
        await _sync_api_bindings(db)
        await db.commit()
    logger.info("Permission registry synced")


async def _sync_permissions(db: AsyncSession) -> None:
    # 注意：遍历 ALL_PERMISSIONS（= 平台码 + 业务模块访问码）。
    # 历史上这里写死 PLATFORM_PERMISSIONS，导致往 ALL_PERMISSIONS 里加的业务码
    # 无法同步进 permission 表（权限目录里看不到、无法授权）。
    for p in ALL_PERMISSIONS:
        existing = await _get_permission_by_code(db, p.code)
        if existing is None:
            db.add(
                Permission(
                    code=p.code,
                    name=p.name,
                    module=p.module,
                    resource=p.resource,
                    action=p.action,
                    description=p.description or None,
                    status=PERMISSION_ACTIVE,
                    is_builtin=True,
                )
            )
            continue
        # 只更新描述性字段，不改 status（退役不可复活）
        existing.name = p.name
        existing.module = p.module
        existing.resource = p.resource
        existing.action = p.action
        if p.description:
            existing.description = p.description


async def _sync_roles(db: AsyncSession) -> None:
    for r in ALL_BUILTIN_ROLES:
        existing = await _get_role_by_code(db, r.code)
        if existing is None:
            db.add(
                Role(
                    code=r.code,
                    name=r.name,
                    category=r.category,
                    module_code=r.module_code,
                    description=r.description,
                    is_builtin=True,
                    is_superuser=r.is_superuser,
                    status=GRANT_ACTIVE,
                )
            )
            continue
        existing.name = r.name
        existing.category = r.category
        existing.module_code = r.module_code
        existing.description = r.description
        existing.is_superuser = r.is_superuser
        existing.is_builtin = True


async def _sync_role_permissions(db: AsyncSession) -> None:
    for role_code, codes in BUILTIN_ROLE_PERMISSIONS.items():
        role = await _get_role_by_code(db, role_code)
        if role is None:
            continue
        for code in codes:
            result = await db.execute(
                select(RolePermission.id).where(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_code == code,
                    RolePermission.is_deleted == False,  # noqa: E712
                )
            )
            if result.scalar_one_or_none() is None:
                db.add(RolePermission(role_id=role.id, permission_code=code))


async def _sync_api_bindings(db: AsyncSession) -> None:
    for b in API_BINDINGS:
        result = await db.execute(
            select(ApiBinding.id).where(
                ApiBinding.method == b.method,
                ApiBinding.route_template == b.route_template,
                ApiBinding.is_deleted == False,  # noqa: E712
            )
        )
        if result.scalar_one_or_none() is None:
            db.add(
                ApiBinding(
                    permission_code=b.permission_code,
                    method=b.method,
                    route_template=b.route_template,
                    scope_required=b.scope_required,
                    status=PERMISSION_ACTIVE,
                )
            )
            continue


async def ensure_superadmin(db: AsyncSession, username: str) -> None:
    """给指定用户名挂 super_admin 角色（幂等，无则创建授权）。"""
    from app.platform.identity.repository import UserRepository

    if not username:
        return

    user_repo = UserRepository()
    user = await user_repo.get_by_username(db, username)
    if user is None:
        return

    super_role = await _get_role_by_code(db, "super_admin")
    if super_role is None:
        logger.warning("super_admin role missing, skip bootstrap")
        return

    result = await db.execute(
        select(UserRoleGrant.id).where(
            UserRoleGrant.user_id == user.id,
            UserRoleGrant.role_id == super_role.id,
            UserRoleGrant.is_deleted == False,  # noqa: E712
        )
    )
    if result.scalar_one_or_none() is not None:
        return

    db.add(
        UserRoleGrant(
            user_id=user.id,
            role_id=super_role.id,
            scope_type=SCOPE_ALL,
            status=GRANT_ACTIVE,
            version=1,
        )
    )
    logger.info("Granted super_admin to %s", username)


async def bootstrap_initial_superadmin() -> None:
    """给初始管理员（BOOTSTRAP_ADMIN_USERNAME）挂 super_admin 角色（幂等）。"""
    settings = get_settings()
    async with async_session_factory() as db:
        await ensure_superadmin(db, settings.BOOTSTRAP_ADMIN_USERNAME)
        await db.commit()


# ── 防自我提权 guard ─────────────────────────────────────────────


async def get_role(db: AsyncSession, role_id: uuid.UUID) -> Role | None:
    result = await db.execute(
        select(Role).where(
            Role.id == role_id,
            Role.is_deleted == False,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def count_active_superadmins(db: AsyncSession) -> int:
    stmt = (
        select(func.count())
        .select_from(UserRoleGrant)
        .join(Role, Role.id == UserRoleGrant.role_id)
        .where(
            Role.is_superuser.is_(True),
            Role.is_deleted == False,  # noqa: E712
            UserRoleGrant.status == GRANT_ACTIVE,
            UserRoleGrant.is_deleted == False,  # noqa: E712
        )
    )
    return int((await db.execute(stmt)).scalar_one())


def guard_self_escalation(actor_id: uuid.UUID, grant: UserRoleGrant) -> None:
    """禁止修改 / 删除自己的授权。"""
    if grant.user_id == actor_id:
        raise ForbiddenException("不能修改自己的授权")


async def guard_last_superadmin(db: AsyncSession, grant: UserRoleGrant) -> None:
    """删除 super_admin 授权前，确保系统中还有其他超级管理员。"""
    role = await get_role(db, grant.role_id)
    if role is None or not role.is_superuser:
        return
    if await count_active_superadmins(db) <= 1:
        raise ForbiddenException("不能移除最后一个超级管理员")


# ── 管理员分级：防越级提权 + 超管账号保护 ─────────────────────────────


async def effective_permission_codes(db: AsyncSession, user: User) -> set[str]:
    """用户当前有效权限码集合；超级管理员返回全部已登记权限码。

    用于「管理员分级」判定：下级管理员只能管理权限严格低于自己的账号。
    结果会缓存到 Redis（默认 60 秒），减少每次请求都重查授权表的开销。
    """
    from app.platform.permission.cache import (
        get_cached_is_superuser,
        get_cached_permission_codes,
        set_cached_is_superuser,
        set_cached_permission_codes,
    )

    cached_super = await get_cached_is_superuser(user.id)
    if cached_super is None:
        cached_super = await GrantRepository().is_superuser(db, user)
        await set_cached_is_superuser(user.id, cached_super)

    if cached_super:
        result = await db.execute(
            select(Permission.code).where(Permission.is_deleted == False)  # noqa: E712
        )
        return set(result.scalars().all())

    cached_codes = await get_cached_permission_codes(user.id)
    if cached_codes is not None:
        return cached_codes

    result = await db.execute(
        select(RolePermission.permission_code)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRoleGrant, UserRoleGrant.role_id == Role.id)
        .where(
            UserRoleGrant.user_id == user.id,
            UserRoleGrant.status == GRANT_ACTIVE,
            UserRoleGrant.is_deleted == False,  # noqa: E712
            Role.status == GRANT_ACTIVE,
            Role.is_deleted == False,  # noqa: E712
            RolePermission.is_deleted == False,  # noqa: E712
        )
        .distinct()
    )
    codes = set(result.scalars().all())
    await set_cached_permission_codes(user.id, codes)
    return codes


async def guard_manage_target(
    db: AsyncSession,
    actor: User,
    target: User,
    *,
    resource_label: str = "账号",
) -> None:
    """管理目标账号前的分级校验（用户管理 / 授权管理通用）。

    - 目标是超级管理员 → 仅允许超级管理员操作（超管平级可互管）；
    - 非超级管理员操作者 → 目标权限码必须是操作者权限码的**真子集**（只能向下管理，
      平级 / 上级 / 权限不重叠的账号一律不允许）。
    """
    if await GrantRepository().is_superuser(db, target):
        if not await GrantRepository().is_superuser(db, actor):
            raise ForbiddenException(f"不能操作超级管理员的{resource_label}")
        return

    if await GrantRepository().is_superuser(db, actor):
        return

    actor_perms = await effective_permission_codes(db, actor)
    target_perms = await effective_permission_codes(db, target)
    if not (target_perms < actor_perms):
        raise ForbiddenException(f"不能操作权限不低于你的{resource_label}")


async def assert_actor_can_grant_role(db: AsyncSession, actor: User, role: Role) -> None:
    """授角色前的防越权校验。

    - 授予超级管理员角色 → 操作者本人必须是超级管理员；
    - 其余角色 → 该角色所含权限码必须 ⊆ 操作者权限码（否则授出自己都没有的权限）。
    """
    if role.is_superuser:
        if not await GrantRepository().is_superuser(db, actor):
            raise ForbiddenException("只有超级管理员能授予超级管理员角色")
        return

    if await GrantRepository().is_superuser(db, actor):
        return

    actor_perms = await effective_permission_codes(db, actor)
    role_perms = set(await RoleRepository().list_role_permission_codes(db, role.id))
    if not (role_perms <= actor_perms):
        raise ForbiddenException("不能授予超出你权限范围的角色")


def _scope_covers(
    actor_scope: str,
    actor_codes: list[str] | None,
    target_scope: str,
    target_codes: list[str],
) -> bool:
    """操作者的数据范围是否覆盖目标范围。

    all 覆盖一切；部门档要求目标部门码 ⊆ 操作者部门码；self 只能覆盖 self。
    """
    if actor_scope == SCOPE_ALL:
        return True
    if target_scope == SCOPE_ALL:
        return False
    if target_scope == SCOPE_SELF:
        return True
    if actor_scope == SCOPE_SELF:
        return False
    # 剩余都是部门档：目标部门码必须落在操作者部门码内
    target_set = set(target_codes or [])
    if not target_set:
        return False
    return target_set <= set(actor_codes or [])


async def assert_actor_can_grant_scope(
    db: AsyncSession,
    actor: User,
    *,
    scope_type: str,
    scope_dept_codes: list[str] | None,
) -> None:
    """数据范围上限：非超管授出的范围不能超过自己「授予 grant:manage」那条授权的范围。"""
    if await GrantRepository().is_superuser(db, actor):
        return

    grants = await GrantRepository().get_grants_for_permission(db, actor.id, "platform:grant:manage")
    if not grants:
        raise ForbiddenException("无法确定你的数据范围，拒绝授权")

    for grant in grants:
        if _scope_covers(
            grant.scope_type,
            grant.scope_dept_codes,
            scope_type,
            scope_dept_codes or [],
        ):
            return
    raise ForbiddenException("不能授予超出你数据范围的范围")
