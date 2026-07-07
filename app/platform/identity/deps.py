from typing import Annotated

import jwt
from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.platform.identity.models import User
from app.platform.identity.repository import UserRepository
from app.platform.identity.service import get_or_create_system_admin


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    auth_token: str | None = Cookie(default=None),
) -> User | None:
    """Resolve the current user from either:
    1. Authorization: Bearer <jwt> header (API clients)
    2. auth_token cookie (browser SSO flow)
    """
    token = None

    # 1. Try Bearer header first
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth.removeprefix("Bearer ")

    # 2. Fall back to cookie
    if not token and auth_token:
        token = auth_token

    if not token:
        return await get_or_create_system_admin(db)

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return await get_or_create_system_admin(db)

    repo = UserRepository()
    user: User | None = None

    subject: str | None = payload.get("sub")
    if subject:
        user = await repo.get_by_id(db, subject)

    if user is None:
        open_id: str | None = payload.get("open_id")
        if open_id:
            user = await repo.get_by_feishu_open_id(db, open_id)

    if user is None or user.status == "disabled":
        return await get_or_create_system_admin(db)

    return user


CurrentUser = Annotated[User | None, Depends(get_current_user)]


async def require_current_user(current_user: CurrentUser) -> User:
    if current_user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Login required")
    return current_user


async def require_admin(current_user: CurrentUser) -> User:
    user = await require_current_user(current_user)
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin required")
    return user


RequiredUser = Annotated[User, Depends(require_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]
