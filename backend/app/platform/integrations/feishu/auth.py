"""Feishu tenant access token management."""

import asyncio
import logging
import time

import httpx

from app.core.config import get_settings

_settings = get_settings()
logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 3
_RETRY_BACKOFF_SECONDS = (1, 2, 4)


class FeishuAuth:
    _token: str | None = None
    _expire_at: float = 0.0

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

        app_id = _settings.feishu.platform.app_id
        app_secret = _settings.feishu.platform.app_secret
        if not app_id or not app_secret:
            raise RuntimeError("Feishu app_id or app_secret not configured")

        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                        json={"app_id": app_id, "app_secret": app_secret},
                        timeout=10.0,
                    )
                    resp.raise_for_status()
                    data = resp.json()

                if data.get("code") != 0:
                    raise RuntimeError(f"Feishu auth failed: code={data.get('code')}, msg={data.get('msg')}")
                break
            except Exception:
                if attempt == _MAX_ATTEMPTS:
                    logger.exception(
                        "获取飞书 tenant_access_token 失败（已尝试 %d 次）",
                        _MAX_ATTEMPTS,
                        extra={"biz_module": "platform"},
                    )
                    raise
                logger.warning(
                    "获取飞书 tenant_access_token 失败，%d 秒后重试（第 %d/%d 次）",
                    _RETRY_BACKOFF_SECONDS[attempt - 1],
                    attempt,
                    _MAX_ATTEMPTS,
                    extra={"biz_module": "platform"},
                    exc_info=True,
                )
                await asyncio.sleep(_RETRY_BACKOFF_SECONDS[attempt - 1])

        token = data["tenant_access_token"]
        cls._token = token
        cls._expire_at = time.time() + data.get("expire", 7200)
        return token  # type: ignore[no-any-return]
