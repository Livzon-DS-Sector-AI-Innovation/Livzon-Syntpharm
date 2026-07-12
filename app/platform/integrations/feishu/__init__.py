"""Feishu SSO, approval, IM, Bitable, notification and WebSocket integrations."""

from typing import Any

from app.platform.integrations.feishu.bitable import FeishuBitableSync
from app.platform.integrations.feishu.client import FeishuClient
from app.platform.integrations.feishu.datasource import BitableDataSource
from app.platform.integrations.feishu.employee_datasource import (
    EmployeeBitableDataSource,
    EmployeeRecord,
)
from app.platform.integrations.feishu.im import (
    FeishuMessageSendResult,
    build_callback_card_content,
    build_callback_status_card_content,
    build_simple_card_content,
    build_text_message_content,
    send_feishu_message,
    update_feishu_message,
)
from app.platform.integrations.feishu.notification import (
    build_card,
    send_user_card,
)
from app.platform.integrations.feishu.utils import (
    FEISHU_BITABLE_RECORD_CHANGED_EVENT,
    BitableReference,
    ConnectivityStep,
    get_tenant_access_token,
    normalize_app_token,
    normalize_table_id,
    parse_bitable_url,
    test_bitable_table,
)
from app.platform.integrations.feishu.ws_client import (
    start_ws_client,
    stop_ws_client,
)
from app.shared.lifecycle import register_background_worker

__all__ = [
    "FeishuClient",
    "FeishuBitableSync",
    "BitableDataSource",
    "EmployeeBitableDataSource",
    "EmployeeRecord",
    "FeishuMessageSendResult",
    "build_callback_card_content",
    "build_callback_status_card_content",
    "build_simple_card_content",
    "build_text_message_content",
    "send_feishu_message",
    "update_feishu_message",
    "build_card",
    "send_user_card",
    "BitableReference",
    "ConnectivityStep",
    "FEISHU_BITABLE_RECORD_CHANGED_EVENT",
    "get_tenant_access_token",
    "normalize_app_token",
    "normalize_table_id",
    "parse_bitable_url",
    "test_bitable_table",
    "start_ws_client",
    "stop_ws_client",
]


# ── Background worker registration ────────────────────────────


async def _start_platform_ws() -> Any:
    """Start platform-level Feishu WebSocket client."""
    import asyncio

    from app.platform.integrations.feishu.event_handler import set_main_loop
    from app.platform.integrations.feishu.ws_client import start_ws_client

    set_main_loop(asyncio.get_running_loop())
    await start_ws_client()  # type: ignore[func-returns-value,misc]


def _stop_platform_ws() -> Any:
    """Stop platform-level Feishu WebSocket client."""
    from app.platform.integrations.feishu.ws_client import stop_ws_client

    stop_ws_client()


register_background_worker(
    name="platform.feishu_ws",
    start=_start_platform_ws,
    stop=_stop_platform_ws,
)
