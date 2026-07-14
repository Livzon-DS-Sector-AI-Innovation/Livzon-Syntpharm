"""Simplified permission control - all logged-in users have same permissions."""

from typing import Annotated, Any

from fastapi import Depends, HTTPException, status

from app.platform.identity.deps import get_current_user
from app.platform.identity.models import User


def require_login() -> Any:
    """Dependency: require user to be logged in."""

    async def dependency(current_user: User | None = Depends(get_current_user)) -> User:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="请先登录",
            )
        return current_user

    return dependency


# Convenient type alias
RequireLogin = Annotated[User, Depends(require_login())]
