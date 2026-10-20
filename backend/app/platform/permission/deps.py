"""权限依赖注入。

业务 API 用法：
    ctx: PermissionContext = Depends(require_permission("quality:deviation:approve"))

注意：这里直接从 identity.deps 导入 require_current_user，避免与
core.deps 的 re-export 形成循环依赖。
"""

from collections.abc import Awaitable, Callable

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenException
from app.platform.identity.deps import require_current_user
from app.platform.identity.models import User
from app.platform.permission.service.authorization import (
    PermissionContext,
    build_permission_context,
)

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


__all__ = ["PermissionContext", "require_any_permission", "require_permission"]
