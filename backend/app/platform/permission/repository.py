"""权限仓储：授权查询与 CRUD。"""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.identity.models import User
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
        """所有持有 active 超级管理员角色的用户 id。

        用户管理列表用它把超管账号对非超管隐藏：即使对方有
        `platform:user:read`，也不应该看到超管的资料与角色。
        """
        stmt = (
            select(UserRoleGrant.user_id)
            .join(Role, Role.id == UserRoleGrant.role_id)
            .where(
                UserRoleGrant.status == GRANT_ACTIVE,
                UserRoleGrant.is_deleted == False,  # noqa: E712
                Role.is_superuser.is_(True),
                Role.status == GRANT_ACTIVE,
                Role.is_deleted == False,  # noqa: E712
            )
            .distinct()
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

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
        """查询授权列表，join 角色与用户以填充展示字段。"""
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
        result = await db.execute(
            select(Role)
            .where(Role.is_deleted == False)  # noqa: E712
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
        """全量设置角色权限码（软删旧关联 + 新增缺失项）。"""
        wanted = set(permission_codes)

        # 删除不再需要的
        result = await db.execute(
            select(RolePermission).where(
                RolePermission.role_id == role_id,
                RolePermission.is_deleted == False,  # noqa: E712
            )
        )
        for rp in result.scalars().all():
            if rp.permission_code not in wanted:
                rp.is_deleted = True
            else:
                wanted.discard(rp.permission_code)

        # 新增缺失的
        for code in wanted:
            db.add(RolePermission(role_id=role_id, permission_code=code))

    async def soft_delete_role(self, db: AsyncSession, role: Role) -> None:
        role.is_deleted = True
        role.status = "disabled"


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
