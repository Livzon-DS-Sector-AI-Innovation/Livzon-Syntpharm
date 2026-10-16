"""权限依赖注入。

业务 API 用法：
    ctx: PermissionContext = Depends(require_permission("quality:deviation:approve"))

注意：这里直接从 identity.deps 导入 require_current_user，避免与
core.deps 的 re-export 形成循环依赖。
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.platform.identity.deps import require_current_user
from app.platform.identity.models import User
from app.platform.permission.service.authorization import (
    PermissionContext,
    build_permission_context,
)


def require_permission(permission_code: str):
    """依赖工厂：要求当前用户拥有指定权限码（单条授权判定）。"""

    async def _dependency(
        user: User = Depends(require_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> PermissionContext:
        return await build_permission_context(db, user, permission_code)

    return _dependency


__all__ = ["PermissionContext", "require_permission"]
