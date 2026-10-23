import logging
from typing import Annotated

import jwt
from fastapi import Cookie, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.exceptions import UnauthorizedException
from app.platform.identity.models import User
from app.platform.identity.repository import UserRepository

logger = logging.getLogger(__name__)


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
        return None

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return None

    # 会话吊销检查（踢下线）：jti 命中吊销黑名单即视为未登录。
    # 这里刻意保持 fail-open：Redis 故障时按「未吊销」放行，避免基础设施抖一下就把
    # 全员登出（ERP 可用性优先）。代价是 Redis 不可用期间，已被踢下线的 token 仍可用，
    # 该窗口已作为已知残留风险记录在 docs/ai-audit-findings.md（PR #121 第四轮）。
    try:
        from app.platform.identity.session import is_session_revoked

        if await is_session_revoked(payload.get("jti")):
            return None
    except Exception:
        logger.warning("会话吊销检查失败（Redis 不可用？），按未吊销处理", exc_info=True)

    repo = UserRepository()
    user: User | None = None

    subject: str | None = payload.get("sub")
    if subject:
        user = await repo.get_by_id(db, subject)  # type: ignore[arg-type]

    if user is None:
        open_id: str | None = payload.get("open_id")
        if open_id:
            user = await repo.get_by_feishu_open_id(db, open_id)

    if user is None or user.status == "disabled":
        return None

    return user


CurrentUser = Annotated[User | None, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_current_user)]


async def require_current_user(current_user: CurrentUser) -> User:
    if current_user is None:
        raise UnauthorizedException()
    return current_user


RequiredUser = Annotated[User, Depends(require_current_user)]
