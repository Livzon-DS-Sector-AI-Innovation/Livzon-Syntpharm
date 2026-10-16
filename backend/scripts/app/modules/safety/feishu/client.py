"""安全模块专属飞书客户端。

使用独立凭证，通过 app.core.config 获取。
"""

import json as _json
import logging

import lark_oapi as lark

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _get_safety_app_id() -> str:
    return get_settings().feishu.safety.credentials.app_id


def _get_safety_app_secret() -> str:
    return get_settings().feishu.safety.credentials.app_secret


async def get_safety_feishu_client() -> lark.Client:
    """获取安全模块专属的飞书客户端。"""
    app_id = _get_safety_app_id()
    app_secret = _get_safety_app_secret()
    if not app_id or not app_secret:
        raise RuntimeError(
            "安全模块飞书配置缺失：请设置 FEISHU__SAFETY__CREDENTIALS__APP_ID "
            "和 FEISHU__SAFETY__CREDENTIALS__APP_SECRET 环境变量"
        )
    return (
        lark.Client.builder()
        .app_id(app_id)
        .app_secret(app_secret)
        .domain(lark.FEISHU_DOMAIN)
        .app_type(lark.AppType.SELF)
        .build()
    )


async def get_safety_tenant_token(client: lark.Client | None = None) -> str:
    """获取安全模块飞书应用的 tenant_access_token。"""
    from lark_oapi.api.auth.v3 import (
        InternalTenantAccessTokenRequest,
        InternalTenantAccessTokenRequestBody,
    )

    if client is None:
        client = await get_safety_feishu_client()

    app_id = _get_safety_app_id()
    app_secret = _get_safety_app_secret()
    req = (
        InternalTenantAccessTokenRequest.builder()
        .request_body(InternalTenantAccessTokenRequestBody.builder().app_id(app_id).app_secret(app_secret).build())
        .build()
    )
    resp = await client.auth.v3.tenant_access_token.ainternal(req)
    if not resp.success():
        raise RuntimeError(f"获取安全模块飞书 tenant token 失败: code={resp.code}, msg={resp.msg}")
    if resp.raw and resp.raw.content:
        data = _json.loads(resp.raw.content.decode("utf-8"))
        token = data.get("tenant_access_token", "")
        logger.debug("安全模块飞书 tenant token 获取成功")
        return token  # type: ignore[no-any-return]
    raise RuntimeError("安全模块飞书 tenant token 响应为空")
