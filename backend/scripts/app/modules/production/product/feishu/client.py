"""Production module Feishu client — uses production module independent credentials."""

import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def get_production_tenant_token() -> str:
    """Get tenant_access_token for the production module Feishu app."""
    settings = get_settings()
    app_id = settings.feishu.product.credentials.app_id
    app_secret = settings.feishu.product.credentials.app_secret
    if not app_id or not app_secret:
        raise RuntimeError(
            "Production module Feishu config missing: set FEISHU__PRODUCT__CREDENTIALS__APP_ID "
            "and FEISHU__PRODUCT__CREDENTIALS__APP_SECRET"
        )
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": app_id, "app_secret": app_secret},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Production module Feishu token failed: {data}")
        return data["tenant_access_token"]  # type: ignore[no-any-return]
