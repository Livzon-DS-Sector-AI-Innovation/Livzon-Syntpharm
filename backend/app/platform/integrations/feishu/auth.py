"""Feishu access token management（tenant / app 两种应用级凭证）。"""

import asyncio
import logging
import time
from typing import Any

import httpx

from app.core.config import get_settings

_settings = get_settings()
logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 3
_RETRY_BACKOFF_SECONDS = (1, 2, 4)

_TENANT_TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
_APP_TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal"


class FeishuAuth:
    """access token 缓存：tenant 代表企业，app 代表应用本身。"""

    _token: str | None = None
    _expire_at: float = 0.0
    _app_token: str | None = None
    _app_expire_at: float = 0.0

    @classmethod
    def default(cls) -> "FeishuAuth":
        """Return a compatibility instance for callers that inject auth objects."""
        return cls()

    async def get_token(self) -> str:
        """Compatibility wrapper around the shared tenant token cache."""
        return await self.get_tenant_access_token()

    @classmethod
    async def get_tenant_access_token(cls) -> str:
        """Fetch the tenant token, retrying transient failures.

        3 attempts with exponential backoff (1s/2s/4s). The call is idempotent
        (same app credentials), so retrying is safe.
        """
        if cls._token and time.time() < cls._expire_at - 60:
            return cls._token

        token, expire_at = await cls._request_token(
            url=_TENANT_TOKEN_URL,
            token_field="tenant_access_token",
            label="tenant_access_token",
        )
        cls._token = token
        cls._expire_at = expire_at
        return token

    @classmethod
    async def get_app_access_token(cls) -> str:
        """获取 app_access_token（网页应用免登换 user_access_token 用）。

        与 tenant token 同一套缓存 + 重试策略；app_access_token 只代表应用本身，
        不能代替用户身份。
        """
        if cls._app_token and time.time() < cls._app_expire_at - 60:
            return cls._app_token

        token, expire_at = await cls._request_token(
            url=_APP_TOKEN_URL,
            token_field="app_access_token",
            label="app_access_token",
        )
        cls._app_token = token
        cls._app_expire_at = expire_at
        return token

    @classmethod
    async def _request_token(cls, *, url: str, token_field: str, label: str) -> tuple[str, float]:
        """请求飞书 access token（重试 + 指数退避），返回 (token, 过期时间戳)。

        两个接口的请求体与响应结构一致，只有 URL、token 字段和日志文案不同。
        """
        app_id = _settings.feishu.platform.app_id
        app_secret = _settings.feishu.platform.app_secret
        if not app_id or not app_secret:
            raise RuntimeError("Feishu app_id or app_secret not configured")

        data: dict[str, Any] = {}
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        url,
                        json={"app_id": app_id, "app_secret": app_secret},
                        timeout=10.0,
                    )
                    resp.raise_for_status()
                    data = resp.json()

                if data.get("code") != 0:
                    raise RuntimeError(f"Feishu {label} failed: code={data.get('code')}, msg={data.get('msg')}")
                break
            except Exception:
                if attempt == _MAX_ATTEMPTS:
                    logger.exception(
                        "获取飞书 %s 失败（已尝试 %d 次）",
                        label,
                        _MAX_ATTEMPTS,
                        extra={"biz_module": "platform"},
                    )
                    raise
                logger.warning(
                    "获取飞书 %s 失败，%d 秒后重试（第 %d/%d 次）",
                    label,
                    _RETRY_BACKOFF_SECONDS[attempt - 1],
                    attempt,
                    _MAX_ATTEMPTS,
                    extra={"biz_module": "platform"},
                    exc_info=True,
                )
                await asyncio.sleep(_RETRY_BACKOFF_SECONDS[attempt - 1])

        return str(data[token_field]), time.time() + float(data.get("expire", 7200))
