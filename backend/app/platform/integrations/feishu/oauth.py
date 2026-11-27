"""Feishu OAuth client for SSO login.

Uses raw httpx because the OAuth endpoints are not fully covered by the
lark-oapi SDK.  The flow follows the official Feishu documentation:

  Step 1 – Authorize:  GET  https://accounts.feishu.cn/open-apis/authen/v1/authorize
  Step 2 – Token:      POST https://open.feishu.cn/open-apis/authen/v2/oauth/token
  Step 3 – User Info:  GET  https://open.feishu.cn/open-apis/authen/v1/user_info
  Step 4 – Refresh:    POST https://open.feishu.cn/open-apis/authen/v2/oauth/token

Ref: https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/authen-v1/login-overview
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# 外部调用重试策略：最多 3 次，指数退避 1/2/4 秒（与 feishu/auth.py 保持一致）
_MAX_ATTEMPTS = 3
_RETRY_BACKOFF_SECONDS = (1, 2, 4)

_AUTHORIZE_URL = "https://accounts.feishu.cn/open-apis/authen/v1/authorize"
_TOKEN_URL = "https://open.feishu.cn/open-apis/authen/v2/oauth/token"
_USER_INFO_URL = "https://open.feishu.cn/open-apis/authen/v1/user_info"
# 旧版“登录预授权码换 user_access_token”接口：网页应用免登官方示例用它，
# 作为 v2/oauth/token 不接受免登码时的兜底（Header 走 app_access_token）。
_PREAUTH_TOKEN_URL = "https://open.feishu.cn/open-apis/authen/v1/access_token"


class FeishuOAuthClient:
    """Handles the OAuth 2.0 authorization-code flow against Feishu."""

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        redirect_uri: str,
        scopes: str,
    ):
        self.app_id = app_id
        self.app_secret = app_secret
        self.redirect_uri = redirect_uri
        self.scopes = scopes

    @classmethod
    def from_settings(cls) -> FeishuOAuthClient:
        s = get_settings()
        return cls(
            app_id=s.feishu.platform.app_id,
            app_secret=s.feishu.platform.app_secret,
            redirect_uri=s.feishu.platform.redirect_uri,
            scopes=s.feishu.platform.scopes,
        )

    # ── URL builders ────────────────────────────────────────────────

    def build_authorize_url(self, state: str) -> str:
        """Return the full Feishu authorization URL to redirect the user to."""
        params = {
            "client_id": self.app_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "state": state,
            "scope": self.scopes,
        }
        return f"{_AUTHORIZE_URL}?{urlencode(params)}"

    # ── Token operations ────────────────────────────────────────────

    async def exchange_code(self, code: str, *, include_redirect_uri: bool = True) -> dict[str, Any]:
        """Exchange an authorization code for tokens.

        Returns dict with keys: access_token, token_type, expires_in,
        refresh_token, refresh_token_expires_in, scope.

        `include_redirect_uri=False` 用于网页应用免登：预授权码来自 H5 JSSDK
        （`tt.requestAccess`），没有经过授权页跳转，因此兑换时不能带 redirect_uri。
        """
        payload = {
            "grant_type": "authorization_code",
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "code": code,
        }
        if include_redirect_uri:
            payload["redirect_uri"] = self.redirect_uri
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _TOKEN_URL,
                json=payload,
                headers={"Content-Type": "application/json; charset=utf-8"},
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()

        if data.get("code", 0) != 0:
            raise OAuthError(
                f"Token exchange failed: code={data.get('code')}, "
                f"error={data.get('error')}, "
                f"desc={data.get('error_description', '')}",
            )
        return data  # type: ignore[no-any-return]

    async def exchange_preauth_code(self, code: str) -> dict[str, Any]:
        """用网页应用免登预授权码换 user_access_token（旧版 authen/v1 接口）。

        v2/oauth/token 不接受 H5 JSSDK 得到的免登码时走这里：
        Header 用 app_access_token，body 只需 grant_type + code。

        返回值与 `exchange_code` 对齐（access_token / refresh_token / ...），
        因为 v1 接口把结果放在 `data` 里，这里直接返回 `data`。
        """
        from app.platform.integrations.feishu.auth import FeishuAuth

        app_access_token = await FeishuAuth.get_app_access_token()
        payload = {"grant_type": "authorization_code", "code": code}
        data: dict[str, Any] = {}
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        _PREAUTH_TOKEN_URL,
                        json=payload,
                        headers={
                            "Authorization": f"Bearer {app_access_token}",
                            "Content-Type": "application/json; charset=utf-8",
                        },
                        timeout=10.0,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                break
            except httpx.HTTPError:
                # 只重试网络层 / 5xx 这类可恢复错误；飞书业务码错误在下面单独抛，不重试
                if attempt == _MAX_ATTEMPTS:
                    logger.exception(
                        "飞书免登预授权码兑换失败（已尝试 %d 次）",
                        _MAX_ATTEMPTS,
                        extra={"biz_module": "platform", "step": "exchange_preauth_code"},
                    )
                    raise
                logger.warning(
                    "飞书免登预授权码兑换失败，%d 秒后重试（第 %d/%d 次）",
                    _RETRY_BACKOFF_SECONDS[attempt - 1],
                    attempt,
                    _MAX_ATTEMPTS,
                    extra={"biz_module": "platform", "step": "exchange_preauth_code"},
                    exc_info=True,
                )
                await asyncio.sleep(_RETRY_BACKOFF_SECONDS[attempt - 1])

        if data.get("code", 0) != 0:
            raise OAuthError(
                f"Preauth code exchange failed: code={data.get('code')}, msg={data.get('msg')}",
            )
        result = data.get("data") or {}
        if not result.get("access_token"):
            raise OAuthError("Preauth code exchange returned no access_token")
        return result

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """Refresh a user_access_token using a refresh_token."""
        payload = {
            "grant_type": "refresh_token",
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "refresh_token": refresh_token,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _TOKEN_URL,
                json=payload,
                headers={"Content-Type": "application/json; charset=utf-8"},
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()

        if data.get("code", 0) != 0:
            raise OAuthError(
                f"Token refresh failed: code={data.get('code')}, "
                f"error={data.get('error')}, "
                f"desc={data.get('error_description', '')}",
            )
        return data  # type: ignore[no-any-return]

    # ── User info ───────────────────────────────────────────────────

    async def get_user_info(self, user_access_token: str) -> dict[str, Any]:
        """Fetch the authenticated user's profile from Feishu.

        Returns dict with keys: name, en_name, avatar_url, avatar_thumb,
        avatar_middle, avatar_big, open_id, union_id, email,
        enterprise_email, user_id, mobile, tenant_key.
        """
        headers = {"Authorization": f"Bearer {user_access_token}"}
        data: dict[str, Any] = {}
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        _USER_INFO_URL,
                        headers=headers,
                        timeout=10.0,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                break
            except httpx.HTTPError:
                # 只重试网络层 / HTTP 层错误；飞书业务码错误在下面单独抛，不重试
                if attempt == _MAX_ATTEMPTS:
                    logger.exception(
                        "获取飞书用户信息失败（已尝试 %d 次）",
                        _MAX_ATTEMPTS,
                        extra={"biz_module": "platform", "step": "get_user_info"},
                    )
                    raise
                logger.warning(
                    "获取飞书用户信息失败，%d 秒后重试（第 %d/%d 次）",
                    _RETRY_BACKOFF_SECONDS[attempt - 1],
                    attempt,
                    _MAX_ATTEMPTS,
                    extra={"biz_module": "platform", "step": "get_user_info"},
                    exc_info=True,
                )
                await asyncio.sleep(_RETRY_BACKOFF_SECONDS[attempt - 1])

        if data.get("code") != 0:
            raise OAuthError(
                f"get_user_info failed: code={data.get('code')}, msg={data.get('msg')}",
            )
        return data.get("data", {})  # type: ignore[no-any-return]


class OAuthError(Exception):
    """Raised when an OAuth operation fails."""
