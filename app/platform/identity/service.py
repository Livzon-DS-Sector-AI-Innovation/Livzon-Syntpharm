"""Authentication service — handles OAuth callback, JWT generation, user upsert."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.platform.identity.models import User
from app.platform.identity.repository import UserRepository
from app.platform.integrations.feishu.oauth import FeishuOAuthClient

logger = logging.getLogger(__name__)

_repo = UserRepository()


async def handle_oauth_callback(
    db: AsyncSession,
    code: str,
) -> tuple[User, str]:
    """Complete the OAuth flow: exchange code → get user info → upsert → JWT.

    Returns (user, jwt_token).
    """
    oauth = FeishuOAuthClient.from_settings()

    # 1. Exchange authorization code for tokens (v2 endpoint)
    token_data = await oauth.exchange_code(code)
    user_access_token = token_data["access_token"]

    # 2. Fetch user profile from Feishu (v1 user_info endpoint)
    #    Response fields: name, en_name, avatar_url, avatar_thumb,
    #    avatar_middle, avatar_big, open_id, union_id, email,
    #    enterprise_email, user_id, mobile, tenant_key
    info = await oauth.get_user_info(user_access_token)

    open_id = info.get("open_id", "")
    user_id = info.get("user_id") or None  # Convert empty to None
    union_id = info.get("union_id") or None  # Convert empty to None
    name = info.get("name", "")
    en_name = info.get("en_name")
    avatar_url = info.get("avatar_url") or info.get("avatar_middle")
    avatar_thumb = info.get("avatar_thumb")
    avatar_middle = info.get("avatar_middle")
    avatar_big = info.get("avatar_big")
    email = info.get("email") or info.get("enterprise_email")
    enterprise_email = info.get("enterprise_email")
    mobile = info.get("mobile")
    tenant_key = info.get("tenant_key")

    if not open_id:
        raise ValueError("Feishu user info missing open_id")

    # 3. Upsert user in local DB
    user = await _repo.get_by_feishu_open_id(db, open_id)
    if user is None:
        # Also try matching by feishu_user_id in case user was synced earlier
        user = await _repo.get_by_feishu_user_id(db, user_id) if user_id else None

    if user is None:
        user = await _repo.create(
            db,
            name=name,
            feishu_user_id=user_id,
            feishu_open_id=open_id,
            feishu_union_id=union_id,
            en_name=en_name,
            email=email,
            enterprise_email=enterprise_email,
            mobile=mobile,
            avatar_url=avatar_url,
            avatar_thumb=avatar_thumb,
            avatar_middle=avatar_middle,
            avatar_big=avatar_big,
            tenant_key=tenant_key,
        )
        logger.info("Created new user: %s (open_id=%s)", name, open_id)
    else:
        # Update profile info on each login
        user.name = name or user.name
        user.feishu_user_id = user_id or user.feishu_user_id
        user.feishu_union_id = union_id or user.feishu_union_id
        user.en_name = en_name or user.en_name
        user.email = email or user.email
        user.enterprise_email = enterprise_email or user.enterprise_email
        user.mobile = mobile or user.mobile
        user.avatar_url = avatar_url or user.avatar_url
        user.avatar_thumb = avatar_thumb or user.avatar_thumb
        user.avatar_middle = avatar_middle or user.avatar_middle
        user.avatar_big = avatar_big or user.avatar_big
        user.tenant_key = tenant_key or user.tenant_key
        logger.info("Updated user: %s (open_id=%s)", user.name, open_id)

    await db.commit()

    # 4. Generate JWT
    token = generate_jwt(user)
    return user, token


def generate_jwt(user: User) -> str:
    """Generate a JWT token for the given user."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user.id),
        "open_id": user.feishu_open_id,
        "name": user.name,
        "iat": now,
        "exp": now + timedelta(seconds=settings.JWT_EXPIRE_SECONDS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def generate_state_token() -> str:
    """Generate a short-lived state token for CSRF protection."""
    import secrets

    settings = get_settings()
    nonce = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    payload = {
        "nonce": nonce,
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def validate_state_token(state: str) -> bool:
    """Validate a state token. Returns True if valid and not expired."""
    settings = get_settings()
    try:
        jwt.decode(state, settings.SECRET_KEY, algorithms=["HS256"])
        return True
    except jwt.InvalidTokenError:
        return False
