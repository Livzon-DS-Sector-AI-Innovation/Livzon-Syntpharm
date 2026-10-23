"""权限模块对外公共 API。

其他模块 / Agent 工具复用同一套授权判定时，从这里导入，
不要直接 import permission 模块内部实现。
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.identity.models import User
from app.platform.permission.cache import evict_user_permission_cache
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
    """所有超管用户 id（用户管理列表对非超管隐藏这些账号时使用）。"""
    return await GrantRepository().list_superuser_user_ids(db)


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
    "build_permission_context",
    "ensure_superadmin",
    "has_permission",
    "guard_manage_target",
    "list_superuser_user_ids",
    "revoke_all_user_grants",
    "user_is_superuser",
]
