"""Role-based permission control."""

from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.platform.identity.deps import get_current_user
from app.platform.identity.models import User

# Role hierarchy: admin > manager > member > viewer
ROLE_HIERARCHY = {
    "admin": 4,
    "manager": 3,
    "member": 2,
    "viewer": 1,
}

# Permission definitions: what each role can do
PERMISSIONS = {
    "admin": ["read", "write", "delete", "manage", "approve"],
    "manager": ["read", "write", "delete", "approve"],
    "member": ["read", "write"],
    "viewer": ["read"],
}


def has_role(user: User | None, required_role: str) -> bool:
    """Check if user has the required role (or higher)."""
    if not user:
        return False
    user_level = ROLE_HIERARCHY.get(user.role, 0)
    required_level = ROLE_HIERARCHY.get(required_role, 0)
    return user_level >= required_level


def has_permission(user: User | None, permission: str) -> bool:
    """Check if user has the specified permission."""
    if not user:
        return False
    user_perms = PERMISSIONS.get(user.role, [])
    return permission in user_perms


def require_role(required_role: str):
    """Dependency: require user to have at least the specified role."""

    async def dependency(current_user: User | None = Depends(get_current_user)) -> User:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="请先登录",
            )
        if not has_role(current_user, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要 {required_role} 及以上角色权限",
            )
        return current_user

    return dependency


def require_permission(permission: str):
    """Dependency: require user to have the specified permission."""

    async def dependency(current_user: User | None = Depends(get_current_user)) -> User:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="请先登录",
            )
        if not has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"没有 {permission} 权限",
            )
        return current_user

    return dependency


# Convenient type aliases for FastAPI dependencies
RequireAdmin = Annotated[User, Depends(require_role("admin"))]
RequireManager = Annotated[User, Depends(require_role("manager"))]
RequireMember = Annotated[User, Depends(require_role("member"))]
RequireViewer = Annotated[User, Depends(require_role("viewer"))]
