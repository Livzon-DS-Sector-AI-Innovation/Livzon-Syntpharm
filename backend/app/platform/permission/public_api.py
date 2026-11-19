"""权限模块对外公共 API。

其他模块 / Agent 工具复用同一套授权判定时，从这里导入，
不要直接 import permission 模块内部实现。
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException
from app.platform.identity.models import User
from app.platform.permission.cache import evict_user_permission_cache
from app.platform.permission.constants import MIN_ACTIVE_SUPERADMINS
from app.platform.permission.repository import GrantRepository
from app.platform.permission.service.authorization import (
    PermissionContext,
    build_permission_context,
    has_permission,
)
from app.platform.permission.service.management import ensure_superadmin, guard_manage_target


async def user_is_superuser(db: AsyncSession, user: User) -> bool:
    """目标用户是否持有超级管理员角色（只读判定，用于「超管账号受保护」这类场景）。"""
    return await GrantRepository().is_superuser(db, user)


async def list_superuser_user_ids(db: AsyncSession) -> list[uuid.UUID]:
    """所有生效超管用户 id（已删除 / 已停用账号不计入）。

    用户管理列表对非超管隐藏这些账号；identity 侧删除账号也用它判断
    「移除后是否仍有足够超管」。
    """
    return await GrantRepository().list_superuser_user_ids(db)


async def count_active_superusers(db: AsyncSession) -> int:
    """生效超管数量（口径与 list_superuser_user_ids 一致）。"""
    return await GrantRepository().count_active_superusers(db)


async def assert_superadmin_removal_allowed(db: AsyncSession, target_user_id: uuid.UUID) -> None:
    """删除超管账号前校验：移除后仍须保留 `MIN_ACTIVE_SUPERADMINS` 名生效超管。

    与撤销超管授权（`guard_last_superadmin`）同一口径。此前 identity 侧只判断
    「是否最后一名」，导致 2 名超管时能删掉 1 名、把系统降到 1 名（TC-007）。
    """
    super_ids = await list_superuser_user_ids(db)
    if target_user_id in super_ids and len(super_ids) <= MIN_ACTIVE_SUPERADMINS:
        raise ForbiddenException(f"系统管理员至少保留 {MIN_ACTIVE_SUPERADMINS} 名，无法删除该账号")


async def assert_superadmin_disable_allowed(db: AsyncSession, target_user_id: uuid.UUID) -> None:
    """停用超管账号前校验：停用后仍须保留 `MIN_ACTIVE_SUPERADMINS` 名生效超管。

    计数口径已排除已停用账号，因此停用与删除共用同一套判定；按钮上的「禁用」
    此前绕过保底，导致 2 名超管时禁用 1 名即可把系统降到 1 名（TC-007）。
    """
    super_ids = await list_superuser_user_ids(db)
    if target_user_id in super_ids and len(super_ids) <= MIN_ACTIVE_SUPERADMINS:
        raise ForbiddenException(f"系统管理员至少保留 {MIN_ACTIVE_SUPERADMINS} 名，无法停用该账号")


async def get_role_names_by_user_ids(
    db: AsyncSession,
    user_ids: list[uuid.UUID],
) -> dict[uuid.UUID, list[str]]:
    """批量取用户的有效角色名（用户管理列表「角色」列据此显示）。

    只统计生效中的授权（status=active 且未软删）。授权数据的读写收敛到 permission 模块，
    identity 只通过本函数消费，不再反向 import permission 的 models/repository。
    """
    if not user_ids:
        return {}
    from app.platform.permission.models import GRANT_ACTIVE, Role, UserRoleGrant

    stmt = (
        select(UserRoleGrant.user_id, Role.name)
        .join(Role, Role.id == UserRoleGrant.role_id)
        .where(
            UserRoleGrant.user_id.in_(user_ids),
            UserRoleGrant.is_deleted == False,  # noqa: E712
            UserRoleGrant.status == GRANT_ACTIVE,
        )
        .order_by(Role.name)
    )
    rows = (await db.execute(stmt)).all()
    result: dict[uuid.UUID, list[str]] = {}
    for user_id, role_name in rows:
        result.setdefault(user_id, []).append(role_name)
    return result


@dataclass(frozen=True)
class RoleBriefData:
    """角色简要信息（跨模块消费用，避免暴露 permission 的 ORM 模型）。"""

    id: uuid.UUID
    name: str
    module_code: str | None


async def get_role_briefs_by_user_ids(
    db: AsyncSession,
    user_ids: list[uuid.UUID],
) -> dict[uuid.UUID, list[RoleBriefData]]:
    """批量取用户的有效角色（含所属模块编码），供用户管理列表「角色」列展示。"""
    if not user_ids:
        return {}
    from app.platform.permission.models import GRANT_ACTIVE, Role, UserRoleGrant

    stmt = (
        select(UserRoleGrant.user_id, Role.id, Role.name, Role.module_code)
        .join(Role, Role.id == UserRoleGrant.role_id)
        .where(
            UserRoleGrant.user_id.in_(user_ids),
            UserRoleGrant.is_deleted == False,  # noqa: E712
            UserRoleGrant.status == GRANT_ACTIVE,
            Role.is_deleted == False,  # noqa: E712
        )
        .order_by(Role.module_code, Role.name)
    )
    rows = (await db.execute(stmt)).all()
    result: dict[uuid.UUID, list[RoleBriefData]] = {}
    for user_id, role_id, role_name, module_code in rows:
        result.setdefault(user_id, []).append(RoleBriefData(id=role_id, name=role_name, module_code=module_code))
    return result


async def migrate_user_grants(
    db: AsyncSession,
    *,
    source_user_id: uuid.UUID,
    target_user_id: uuid.UUID,
    operator_id: uuid.UUID | None,
) -> tuple[int, int]:
    """把 source 用户的生效授权迁移到 target，按 (role_id, scope_type) 去重。

    同款已存在则软删源侧那条（deduplicated），否则把 user_id 改挂到 target（moved）。
    返回 (moved, deduplicated)。**不提交事务**，由调用方（identity 绑定飞书流程）统一 commit。
    """
    from app.platform.permission.models import UserRoleGrant

    target_grants = (
        (
            await db.execute(
                select(UserRoleGrant).where(
                    UserRoleGrant.user_id == target_user_id,
                    UserRoleGrant.is_deleted == False,  # noqa: E712
                )
            )
        )
        .scalars()
        .all()
    )
    existing_keys = {(grant.role_id, grant.scope_type) for grant in target_grants}

    source_grants = (
        (
            await db.execute(
                select(UserRoleGrant).where(
                    UserRoleGrant.user_id == source_user_id,
                    UserRoleGrant.is_deleted == False,  # noqa: E712
                )
            )
        )
        .scalars()
        .all()
    )

    moved = 0
    deduplicated = 0
    for grant in source_grants:
        if (grant.role_id, grant.scope_type) in existing_keys:
            grant.is_deleted = True
            deduplicated += 1
        else:
            grant.user_id = target_user_id
            grant.version += 1
            moved += 1
        grant.updated_by = operator_id
    return moved, deduplicated


async def revoke_all_user_grants(db: AsyncSession, user_id: uuid.UUID) -> int:
    """清空某用户的全部有效授权并驱逐其权限缓存（删除账号时调用）。

    缓存驱逐放在 flush 之后：即使外层事务最终回滚，也只是多一次回源计算，不会留下
    「已删账号仍被判为有权限」的窗口。
    """
    count = await GrantRepository().soft_delete_user_grants(db, user_id)
    await db.flush()
    await evict_user_permission_cache(user_id)
    return count


__all__ = [
    "PermissionContext",
    "assert_superadmin_disable_allowed",
    "assert_superadmin_removal_allowed",
    "build_permission_context",
    "count_active_superusers",
    "ensure_superadmin",
    "evict_user_permission_cache",
    "get_role_names_by_user_ids",
    "guard_manage_target",
    "has_permission",
    "list_superuser_user_ids",
    "migrate_user_grants",
    "revoke_all_user_grants",
    "user_is_superuser",
]
