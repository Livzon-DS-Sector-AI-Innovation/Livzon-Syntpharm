"""委派式权限管理守卫（R1–R11）。

设计口径（Issue #221，2026-11 用户确认版）：

- 系统管理员（super_admin）只负责任命/移除模块负责人与模块管理员；
- 模块负责人（{module}:head）拥有本模块全部业务权限，可进入模块配置页；
- 模块管理员（{module}:manager）可进入模块配置页，管岗位角色与授权，
  但不自动带业务权限；
- 岗位角色（role_type=job，{module}:{name}）只能含本模块业务码，
  不能含模块管理入口码，也不能跨模块。

本模块只做判定，不写 HTTP、不提交事务；调用方（api.py）负责审计与 commit。
"""

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException
from app.platform.identity.models import User
from app.platform.permission.constants import (
    RESERVED_ROLE_NAMES,
    ROLE_TYPE_HEAD,
    ROLE_TYPE_MANAGER,
    ROLE_TYPE_SYSTEM,
)
from app.platform.permission.models import GRANT_ACTIVE, Role, RolePermission, UserRoleGrant
from app.platform.permission.registry import ADMIN_ENTRY_CODES
from app.platform.permission.service.authorization import is_superuser_with_cache
from app.platform.permission.service.management import effective_permission_codes

logger = logging.getLogger(__name__)

MANAGE_ENTRY_SUFFIX = ":admin:read"


@dataclass(frozen=True)
class ModuleScope:
    """操作者的权限管理范围。"""

    user_id: uuid.UUID
    is_system_admin: bool
    modules: frozenset[str]  # 可管理的模块编码集合（系统管理员不依赖此集合）
    head_modules: frozenset[str] = frozenset()  # 持有「模块负责人」的模块（可指定模块管理员）

    def can_manage(self, module_code: str | None) -> bool:
        if self.is_system_admin:
            return True
        if not module_code:
            return False
        return module_code in self.modules

    def can_assign_managers(self, module_code: str | None) -> bool:
        """模块内只有**负责人**能指定模块管理员（系统管理员不受限）。"""
        if self.is_system_admin:
            return True
        if not module_code:
            return False
        return module_code in self.head_modules


async def resolve_module_scope(db: AsyncSession, user: User) -> ModuleScope:
    """一次查询得出操作者可管理的模块集合 + 作为「模块负责人」的模块集合。

    系统管理员直接放行；其余账号取「持有 {module}:admin:read 的模块」，
    并额外标记哪些模块是自己当负责人的（负责人才能任命管理人）。
    """
    if await is_superuser_with_cache(db, user):
        return ModuleScope(user_id=user.id, is_system_admin=True, modules=frozenset(), head_modules=frozenset())

    codes = await effective_permission_codes(db, user)
    modules = frozenset(code.split(":", 1)[0] for code in codes if code.endswith(MANAGE_ENTRY_SUFFIX))
    head_rows = await db.execute(
        select(Role.module_code)
        .join(UserRoleGrant, UserRoleGrant.role_id == Role.id)
        .where(
            UserRoleGrant.user_id == user.id,
            UserRoleGrant.status == GRANT_ACTIVE,
            UserRoleGrant.is_deleted == False,  # noqa: E712
            Role.role_type == ROLE_TYPE_HEAD,
            Role.is_deleted == False,  # noqa: E712
        )
    )
    head_modules = frozenset(code for code in head_rows.scalars().all() if code)
    return ModuleScope(
        user_id=user.id,
        is_system_admin=False,
        modules=modules,
        head_modules=head_modules,
    )


def assert_module_manageable(scope: ModuleScope, module_code: str | None) -> None:
    """R5：跨模块操作一律拒绝（不是返回空列表）。"""
    if scope.can_manage(module_code):
        return
    logger.warning(
        "委派守卫拒绝：越模块操作",
        extra={"actor_id": str(scope.user_id), "module_code": module_code or ""},
    )
    raise ForbiddenException("无权管理该模块的权限")


def assert_target_role_operable(scope: ModuleScope, role: Role) -> None:
    """R2：内置管理角色的授权行，按身份分级。

    - 模块负责人：只有系统管理员能任命/移除；
    - 模块管理员：本模块负责人或系统管理员能任命/移除；
    - 平台级内置角色（系统管理员本身）：只有系统管理员。
    """
    if scope.is_system_admin:
        return
    if role.is_superuser or role.role_type == ROLE_TYPE_SYSTEM:
        logger.warning(
            "委派守卫拒绝：操作平台内置角色",
            extra={"actor_id": str(scope.user_id), "role_code": role.code},
        )
        raise ForbiddenException("系统管理员角色只能由系统管理员指派或移除")
    if role.role_type == ROLE_TYPE_MANAGER:
        if scope.can_assign_managers(role.module_code):
            return
        logger.warning(
            "委派守卫拒绝：非负责人指派模块管理员",
            extra={"actor_id": str(scope.user_id), "role_code": role.code},
        )
        raise ForbiddenException("只有本模块负责人（或系统管理员）可以指定模块管理员")
    if role.role_type == ROLE_TYPE_HEAD:
        logger.warning(
            "委派守卫拒绝：操作模块负责人",
            extra={"actor_id": str(scope.user_id), "role_code": role.code},
        )
        raise ForbiddenException("模块负责人只能由系统管理员任命或移除")


def assert_role_code_valid(module_code: str, code: str) -> None:
    """R7：岗位角色编码固定两段 `{module}:{name}`，第二段不含冒号且非保留字。"""
    parts = code.split(":")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ForbiddenException("角色编码必须是「模块:名称」两段格式")
    if parts[0] != module_code:
        raise ForbiddenException(f"角色编码必须以「{module_code}:」开头")
    if parts[1] in RESERVED_ROLE_NAMES:
        raise ForbiddenException(f"「{parts[1]}」是本模块保留角色名，不能用于岗位角色")


def assert_job_role_permissions(module_code: str, codes: list[str] | tuple[str, ...]) -> None:
    """R6：岗位角色只能含本模块业务码，不能含模块管理入口码。"""
    for code in codes:
        if code in ADMIN_ENTRY_CODES:
            raise ForbiddenException("模块管理入口权限不可授予岗位角色")
        if not code.startswith(f"{module_code}:"):
            raise ForbiddenException(f"岗位角色只能包含本模块（{module_code}）的权限码：{code}")


def assert_can_create_role(
    scope: ModuleScope,
    module_code: str | None,
    code: str,
    codes: list[str],
) -> None:
    """新建角色：系统管理员建平台/全局角色时跳过模块约束，其余按岗位角色规则校验。"""
    if not module_code:
        if scope.is_system_admin:
            return
        raise ForbiddenException("模块角色必须指定模块编码")
    assert_module_manageable(scope, module_code)
    if scope.is_system_admin:
        return
    assert_role_code_valid(module_code, code)
    assert_job_role_permissions(module_code, codes)


def assert_can_edit_role(scope: ModuleScope, role: Role, *, allow_builtin: bool = False) -> None:
    """编辑 / 删除角色的准入。

    - 系统管理员：**可以**编辑内置角色（模块负责人 / 模块管理员）的权限内容，
      前提是调用方显式声明 `allow_builtin=True`（编辑权限时用；删除角色时不用）；
    - 系统管理员角色本身（super_admin）永远不可改；
    - 其他人：只能改本模块的岗位角色。
    """
    if role.is_superuser or role.role_type == ROLE_TYPE_SYSTEM:
        raise ForbiddenException("系统管理员角色不可修改")
    if role.is_builtin:
        if allow_builtin and scope.is_system_admin:
            return
        raise ForbiddenException("内置角色只能由系统管理员在「系统管理 → 角色管理」中修改")
    if scope.is_system_admin:
        return
    assert_module_manageable(scope, role.module_code)


async def is_platform_admin(db: AsyncSession, user: User) -> bool:
    """是否「平台级权限管理员」：系统管理员，或持有 platform:grant:manage 的既有管理员。

    平台级管理员走原有的分级校验（子集比较）；模块负责人/管理人只在本模块内作业，
    不能按子集比较——模块管理员本身不一定持有业务权限码，否则"给员工开偏差查看权限"
    会因为他自己没有该权限码而被拒。
    """
    if await is_superuser_with_cache(db, user):
        return True
    codes = await effective_permission_codes(db, user)
    return "platform:grant:manage" in codes or "platform:role:manage" in codes


async def assert_role_permissions_subset(
    db: AsyncSession,
    actor: User,
    codes: list[str],
) -> None:
    """R3：平台级管理员授出/写入的权限必须 ⊆ 自己已有权限。

    模块管理员不适用本条：其可授范围已由 `assert_job_role_permissions`
    （只能是本模块业务码）与模块作用域共同限定。
    """
    if not await is_platform_admin(db, actor):
        return
    if await is_superuser_with_cache(db, actor):
        return
    actor_perms = await effective_permission_codes(db, actor)
    if not set(codes) <= actor_perms:
        raise ForbiddenException("不能授予超出你权限范围的角色")


async def assert_no_duplicate_grant(db: AsyncSession, user_id: uuid.UUID, role_id: uuid.UUID) -> None:
    """R9：同一人 + 同一角色不允许重复活跃授权。"""
    result = await db.execute(
        select(UserRoleGrant.id).where(
            UserRoleGrant.user_id == user_id,
            UserRoleGrant.role_id == role_id,
            UserRoleGrant.status == GRANT_ACTIVE,
            UserRoleGrant.is_deleted == False,  # noqa: E712
        )
    )
    if result.scalar_one_or_none() is not None:
        raise ForbiddenException("该用户已持有此角色")


def assert_not_self(actor_id: uuid.UUID, target_user_id: uuid.UUID) -> None:
    """R4：不能给自己授权。"""
    if actor_id == target_user_id:
        raise ForbiddenException("不能给自己授权")


async def role_permission_codes(db: AsyncSession, role_id: uuid.UUID) -> list[str]:
    result = await db.execute(
        select(RolePermission.permission_code).where(
            RolePermission.role_id == role_id,
            RolePermission.is_deleted == False,  # noqa: E712
        )
    )
    return list(result.scalars().all())


__all__ = [
    "MANAGE_ENTRY_SUFFIX",
    "ModuleScope",
    "is_platform_admin",
    "assert_can_create_role",
    "assert_can_edit_role",
    "assert_job_role_permissions",
    "assert_module_manageable",
    "assert_no_duplicate_grant",
    "assert_not_self",
    "assert_role_code_valid",
    "assert_role_permissions_subset",
    "assert_target_role_operable",
    "resolve_module_scope",
    "role_permission_codes",
]
