"""权限仓储：授权查询与 CRUD。"""

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.identity.models import User
from app.platform.permission.constants import RETIRED_ROLE_TYPES
from app.platform.permission.models import (
    GRANT_ACTIVE,
    GRANT_DISABLED,
    ApiBinding,
    Permission,
    Role,
    RolePermission,
    UserRoleGrant,
)


class GrantRepository:
    """授权查询仓储。"""

    async def is_superuser(self, db: AsyncSession, user: User) -> bool:
        """判断用户是否拥有超级管理员角色（任一 active 授权绑定 super_admin）。"""
        stmt = (
            select(Role.id)
            .join(UserRoleGrant, UserRoleGrant.role_id == Role.id)
            .where(
                UserRoleGrant.user_id == user.id,
                UserRoleGrant.status == GRANT_ACTIVE,
                UserRoleGrant.is_deleted == False,  # noqa: E712
                Role.is_superuser.is_(True),
                Role.status == GRANT_ACTIVE,
                Role.is_deleted == False,  # noqa: E712
            )
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def list_superuser_user_ids(self, db: AsyncSession) -> list[uuid.UUID]:
        """所有持有 active 超级管理员角色、且账号仍生效的用户 id。

        用户管理列表用它把超管账号对非超管隐藏：即使对方有
        `platform:user:read`，也不应该看到超管的资料与角色。

        同时 join `identity.users` 过滤已删除 / 已停用账号：这两类账号已经无法登录，
        若继续计入「生效超管」，会让「至少保留 N 名超管」的守卫被空账号占位而失效
        （TC-007：删掉一名超管后，守卫仍以为还有足够名额）。
        """
        stmt = (
            select(UserRoleGrant.user_id)
            .join(Role, Role.id == UserRoleGrant.role_id)
            .join(User, User.id == UserRoleGrant.user_id)
            .where(
                UserRoleGrant.status == GRANT_ACTIVE,
                UserRoleGrant.is_deleted == False,  # noqa: E712
                Role.is_superuser.is_(True),
                Role.status == GRANT_ACTIVE,
                Role.is_deleted == False,  # noqa: E712
                User.is_deleted == False,  # noqa: E712
                User.status != "disabled",
            )
            .distinct()
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def count_active_superusers(self, db: AsyncSession) -> int:
        """生效超管数量（口径与 list_superuser_user_ids 完全一致）。"""
        stmt = (
            select(func.count(func.distinct(UserRoleGrant.user_id)))
            .select_from(UserRoleGrant)
            .join(Role, Role.id == UserRoleGrant.role_id)
            .join(User, User.id == UserRoleGrant.user_id)
            .where(
                UserRoleGrant.status == GRANT_ACTIVE,
                UserRoleGrant.is_deleted == False,  # noqa: E712
                Role.is_superuser.is_(True),
                Role.status == GRANT_ACTIVE,
                Role.is_deleted == False,  # noqa: E712
                User.is_deleted == False,  # noqa: E712
                User.status != "disabled",
            )
        )
        return int((await db.execute(stmt)).scalar_one())

    async def get_grants_for_permission(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        permission_code: str,
    ) -> list[UserRoleGrant]:
        """查询授予了指定权限码的 active 授权（用于单条授权判定）。"""
        stmt = (
            select(UserRoleGrant)
            .join(Role, Role.id == UserRoleGrant.role_id)
            .join(RolePermission, RolePermission.role_id == Role.id)
            .where(
                UserRoleGrant.user_id == user_id,
                UserRoleGrant.status == GRANT_ACTIVE,
                UserRoleGrant.is_deleted == False,  # noqa: E712
                Role.status == GRANT_ACTIVE,
                Role.is_deleted == False,  # noqa: E712
                RolePermission.permission_code == permission_code,
                RolePermission.is_deleted == False,  # noqa: E712
            )
            .distinct()
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def list_grants(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID | None = None,
    ) -> list[UserRoleGrant]:
        """查询授权列表，join 角色与用户以填充展示字段。

        注意：**不要**在这里过滤退役角色类型（`RETIRED_ROLE_TYPES`）。
        本方法唯一调用方是「不能修改自己所属角色的权限」防自提权校验
        （`api.update_role`），过滤会削弱该校验的覆盖面。
        展示层的退役过滤在 `api.list_grants` 的查询里。
        """
        stmt = (
            select(UserRoleGrant)
            .join(Role, Role.id == UserRoleGrant.role_id)
            .outerjoin(User, User.id == UserRoleGrant.user_id)
            .where(UserRoleGrant.is_deleted == False)  # noqa: E712
            .order_by(UserRoleGrant.created_at.desc())
        )
        if user_id is not None:
            stmt = stmt.where(UserRoleGrant.user_id == user_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_grant(self, db: AsyncSession, grant_id: uuid.UUID) -> UserRoleGrant | None:
        result = await db.execute(
            select(UserRoleGrant).where(
                UserRoleGrant.id == grant_id,
                UserRoleGrant.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def list_active_user_ids_by_role(self, db: AsyncSession, role_id: uuid.UUID) -> list[uuid.UUID]:
        """查询拥有某角色 active 授权的用户 ID（用于权限缓存失效）。"""
        result = await db.execute(
            select(UserRoleGrant.user_id)
            .where(
                UserRoleGrant.role_id == role_id,
                UserRoleGrant.status == GRANT_ACTIVE,
                UserRoleGrant.is_deleted == False,  # noqa: E712
            )
            .distinct()
        )
        return list(result.scalars().all())

    async def soft_delete_user_grants(self, db: AsyncSession, user_id: uuid.UUID) -> int:
        """清空某用户的全部有效授权（账号被删除时调用），返回受影响行数。

        授权是「一条授权 = 一个角色 + 数据范围」的最小单元，账号删除后必须一并失效，
        否则已删账号的权限仍会被授权判定读到（且列表里可能继续展示其角色）。
        """
        stmt = (
            update(UserRoleGrant)
            .where(
                UserRoleGrant.user_id == user_id,
                UserRoleGrant.is_deleted == False,  # noqa: E712
            )
            .values(is_deleted=True, status=GRANT_DISABLED)
        )
        result = await db.execute(stmt)
        return int(result.rowcount or 0)  # type: ignore[attr-defined]

    async def create_grant(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        scope_type: str,
        scope_dept_codes: list[str] | None,
        granted_by: uuid.UUID | None,
    ) -> UserRoleGrant:
        grant = UserRoleGrant(
            user_id=user_id,
            role_id=role_id,
            scope_type=scope_type,
            scope_dept_codes=scope_dept_codes,
            status=GRANT_ACTIVE,
            granted_by=granted_by,
            version=1,
        )
        db.add(grant)
        await db.flush()
        return grant


class RoleRepository:
    """角色仓储。"""

    async def list_roles(self, db: AsyncSession) -> list[Role]:
        """列出角色（已退役的历史角色类型不返回）。

        只按 `role_type` 过滤，**不按** `status` 过滤：人工禁用的岗位角色仍要
        出现在列表里（前端按禁用态展示并允许恢复）。
        """
        result = await db.execute(
            select(Role)
            .where(
                Role.is_deleted == False,  # noqa: E712
                Role.role_type.notin_(RETIRED_ROLE_TYPES),
            )
            .order_by(Role.category, Role.code)
        )
        return list(result.scalars().all())

    async def get_role(self, db: AsyncSession, role_id: uuid.UUID) -> Role | None:
        result = await db.execute(
            select(Role).where(
                Role.id == role_id,
                Role.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def get_role_by_code(self, db: AsyncSession, code: str) -> Role | None:
        result = await db.execute(
            select(Role).where(
                Role.code == code,
                Role.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def list_role_permission_codes(self, db: AsyncSession, role_id: uuid.UUID) -> list[str]:
        result = await db.execute(
            select(RolePermission.permission_code).where(
                RolePermission.role_id == role_id,
                RolePermission.is_deleted == False,  # noqa: E712
            )
        )
        return list(result.scalars().all())

    async def set_role_permissions(
        self,
        db: AsyncSession,
        role_id: uuid.UUID,
        permission_codes: list[str],
    ) -> None:
        """全量设置角色权限码（复用/复活已有行 + 软删多余 + 新增缺失）。

        注意 `(role_id, permission_code)` 有唯一约束，所以**不能**先软删再插入同一权限码：
        必须把历史行复活复用，否则会撞唯一键（`重置内置角色权限` 时必然触发）。
        """
        wanted = set(permission_codes)

        result = await db.execute(select(RolePermission).where(RolePermission.role_id == role_id))
        for rp in result.scalars().all():
            if rp.permission_code in wanted:
                rp.is_deleted = False  # 复活历史行
                wanted.discard(rp.permission_code)
            elif not rp.is_deleted:
                rp.is_deleted = True

        # 新增缺失的
        for code in wanted:
            db.add(RolePermission(role_id=role_id, permission_code=code))

    async def soft_delete_role(self, db: AsyncSession, role: Role) -> None:
        role.is_deleted = True
        role.status = "disabled"

    async def disable_grants_for_role(self, db: AsyncSession, role_id: uuid.UUID) -> int:
        """停用某角色的全部活跃授权（删除角色时调用，返回受影响行数）。

        停用而不是软删：授权列表里仍能看到"已停用"的行，判错时可一键恢复。
        """
        result = await db.execute(
            select(UserRoleGrant).where(
                UserRoleGrant.role_id == role_id,
                UserRoleGrant.status == "active",
                UserRoleGrant.is_deleted == False,  # noqa: E712
            )
        )
        grants = list(result.scalars().all())
        for grant in grants:
            grant.status = "disabled"
        await db.flush()
        return len(grants)


class PermissionRepository:
    """权限目录仓储。"""

    async def list_permissions(self, db: AsyncSession) -> list[Permission]:
        result = await db.execute(
            select(Permission)
            .where(Permission.is_deleted == False)  # noqa: E712
            .order_by(Permission.module, Permission.resource, Permission.action)
        )
        return list(result.scalars().all())


class ApiBindingRepository:
    """接口绑定登记簿仓储。"""

    async def list_bindings(self, db: AsyncSession) -> list[ApiBinding]:
        result = await db.execute(
            select(ApiBinding)
            .where(ApiBinding.is_deleted == False)  # noqa: E712
            .order_by(ApiBinding.method, ApiBinding.route_template)
        )
        return list(result.scalars().all())
