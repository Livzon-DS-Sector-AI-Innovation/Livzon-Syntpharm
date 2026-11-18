"""权限依赖注入。

业务 API 用法：
    ctx: PermissionContext = Depends(require_permission("quality:deviation:approve"))

注意：这里直接从 identity.deps 导入 require_current_user，避免与
core.deps 的 re-export 形成循环依赖。
"""

from collections.abc import Awaitable, Callable

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenException

# 显式 re-export：本模块对外也提供 require_current_user，测试里按此路径覆盖依赖
from app.platform.identity.deps import require_current_user as require_current_user
from app.platform.identity.models import User
from app.platform.permission.service.authorization import (
    PermissionContext,
    build_permission_context,
    is_superuser_with_cache,
)
from app.platform.permission.service.delegation import MANAGE_ENTRY_SUFFIX
from app.platform.permission.service.management import effective_permission_codes

PLATFORM_ROLE_READ = "platform:role:read"
PLATFORM_ROLE_MANAGE = "platform:role:manage"
PLATFORM_GRANT_MANAGE = "platform:grant:manage"

PermissionDependency = Callable[..., Awaitable[PermissionContext]]


def require_permission(permission_code: str) -> PermissionDependency:
    """依赖工厂：要求当前用户拥有指定权限码（单条授权判定）。"""

    async def _dependency(
        user: User = Depends(require_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> PermissionContext:
        return await build_permission_context(db, user, permission_code)

    return _dependency


def require_any_permission(*permission_codes: str) -> PermissionDependency:
    """依赖工厂：拥有其中任意一个权限码即可通过。

    用于「有 manage 权限就应能读列表」这类场景 —— 否则只授予
    `platform:grant:manage` 的账号进得了页面，却因缺 `platform:grant:read`
    在列表接口上收到 403。
    """
    if not permission_codes:
        raise ValueError("require_any_permission 至少需要一个权限码")

    async def _dependency(
        user: User = Depends(require_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> PermissionContext:
        last_error: ForbiddenException | None = None
        for code in permission_codes:
            try:
                return await build_permission_context(db, user, code)
            except ForbiddenException as exc:
                last_error = exc
        raise last_error or ForbiddenException("权限不足")

    return _dependency


def require_route_permission(
    resolver: Callable[[str, str], str],
) -> PermissionDependency:
    """依赖工厂：由 `resolver(method, path)` 动态解析权限码。

    用于「一个子路由里读写混排、按导入时的静态码无法区分动作」的场景（如 safety
    模块：20 个子路由、220 个接口）。`resolver` 必须是模块内的纯函数，声明
    「哪个资源段 + 哪种方法 → 哪个权限码」，不要在 resolver 里做 IO。

    与 `require_permission` 的区别仅在于权限码来源；判定、降级与异常语义完全一致。
    """

    async def _dependency(
        request: Request,
        user: User = Depends(require_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> PermissionContext:
        return await build_permission_context(db, user, resolver(request.method, request.url.path))

    return _dependency


def require_module_management() -> PermissionDependency:
    """依赖工厂：允许「全局权限管理员」或「任一模块负责人/模块管理员」进入。

    通过后仍需由 `service/delegation.py` 按目标角色与目标模块做细粒度判定
    （本依赖只解决"有没有资格碰角色/授权接口"这一层，不代替 R1–R11）。
    """

    async def _dependency(
        user: User = Depends(require_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> PermissionContext:
        if await is_superuser_with_cache(db, user):
            return PermissionContext(user=user, permission_code=PLATFORM_ROLE_MANAGE, is_superuser=True)

        codes = await effective_permission_codes(db, user)
        if PLATFORM_ROLE_MANAGE in codes:
            return PermissionContext(user=user, permission_code=PLATFORM_ROLE_MANAGE)
        for code in sorted(codes):
            if code.endswith(MANAGE_ENTRY_SUFFIX):
                return PermissionContext(user=user, permission_code=code)
        raise ForbiddenException("缺少权限：platform:role:manage 或任一模块的模块管理入口")

    return _dependency


def require_role_catalog_read() -> PermissionDependency:
    """依赖工厂：「角色管理」只读目录接口（权限树 / 权限码接口清单）的准入。

    准入集合 = 系统管理员 / `platform:role:read` / `platform:role:manage` /
    任一模块的模块管理入口码。模块负责人、模块管理员不持有 `platform:role:read`
    （其权限只有本模块业务码 + `{module}:admin:read`），若沿用单码判定，他们在
    模块配置页「新建角色」时权限树会 403、界面表现为空树。
    """

    async def _dependency(
        user: User = Depends(require_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> PermissionContext:
        if await is_superuser_with_cache(db, user):
            return PermissionContext(user=user, permission_code=PLATFORM_ROLE_MANAGE, is_superuser=True)

        codes = await effective_permission_codes(db, user)
        for code in (PLATFORM_ROLE_READ, PLATFORM_ROLE_MANAGE):
            if code in codes:
                return PermissionContext(user=user, permission_code=code)
        for code in sorted(codes):
            if code.endswith(MANAGE_ENTRY_SUFFIX):
                return PermissionContext(user=user, permission_code=code)
        raise ForbiddenException("缺少权限：platform:role:read / platform:role:manage 或任一模块的模块管理入口")

    return _dependency


def require_assignment_admin() -> PermissionDependency:
    """依赖工厂：仅系统管理员（或既有平台授权管理员）可任命模块负责人/模块管理员。"""

    async def _dependency(
        user: User = Depends(require_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> PermissionContext:
        if await is_superuser_with_cache(db, user):
            return PermissionContext(user=user, permission_code=PLATFORM_GRANT_MANAGE, is_superuser=True)

        codes = await effective_permission_codes(db, user)
        if PLATFORM_GRANT_MANAGE in codes:
            return PermissionContext(user=user, permission_code=PLATFORM_GRANT_MANAGE)
        raise ForbiddenException("只有系统管理员能任命或移除模块负责人与模块管理员")

    return _dependency


__all__ = [
    "PermissionContext",
    "require_any_permission",
    "require_assignment_admin",
    "require_current_user",
    "require_module_management",
    "require_permission",
    "require_role_catalog_read",
    "require_route_permission",
]
