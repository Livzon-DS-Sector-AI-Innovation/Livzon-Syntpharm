"""权限模块对外公共 API。

其他模块 / Agent 工具复用同一套授权判定时，从这里导入，
不要直接 import permission 模块内部实现。
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.identity.models import User
from app.platform.permission.repository import GrantRepository
from app.platform.permission.service.authorization import (
    PermissionContext,
    build_permission_context,
    has_permission,
)
from app.platform.permission.service.management import guard_manage_target


async def user_is_superuser(db: AsyncSession, user: User) -> bool:
    """目标用户是否持有超级管理员角色（只读判定，用于「超管账号受保护」这类场景）。"""
    return await GrantRepository().is_superuser(db, user)


async def list_superuser_user_ids(db: AsyncSession) -> list[uuid.UUID]:
    """所有超管用户 id（用户管理列表对非超管隐藏这些账号时使用）。"""
    return await GrantRepository().list_superuser_user_ids(db)


__all__ = [
    "PermissionContext",
    "build_permission_context",
    "has_permission",
    "guard_manage_target",
    "list_superuser_user_ids",
    "user_is_superuser",
]
