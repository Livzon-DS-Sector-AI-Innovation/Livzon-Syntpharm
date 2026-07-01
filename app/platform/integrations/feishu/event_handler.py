"""飞书事件处理器 — 全局飞书应用。

事件处理器在 WebSocket 线程中同步调用，
通过 asyncio.run_coroutine_threadsafe 桥接到主 async event loop。

注意：设备模块巡检交互已迁移到独立的设备交互机器人，
见 app/modules/equipment/feishu/handler.py。
"""

import asyncio
import logging

import lark_oapi as lark
from lark_oapi.api.drive.v1 import P2DriveFileBitableRecordChangedV1
from lark_oapi.api.im.v1 import P2ImMessageReceiveV1

from app.core.events import event_bus
from app.platform.integrations.feishu.utils import FEISHU_BITABLE_RECORD_CHANGED_EVENT

logger = logging.getLogger(__name__)

_main_loop: asyncio.AbstractEventLoop | None = None


def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    """设置主 event loop 引用，供异步桥接使用。"""
    global _main_loop
    _main_loop = loop


def build_event_handler() -> lark.EventDispatcherHandler:
    """构建飞书事件处理器，注册所有事件监听。"""
    return (
        lark.EventDispatcherHandler.builder("", "")
        .register_p2_im_message_receive_v1(_on_message_receive)
        .register_p2_drive_file_bitable_record_changed_v1(_on_bitable_record_changed)
        .build()
    )


def _on_message_receive(data: P2ImMessageReceiveV1) -> None:
    """消息接收事件处理（同步入口，在 WS 线程中调用）。"""
    event = data.event
    if not event or not event.message:
        return

    message = event.message
    sender = event.sender
    msg_type = message.message_type
    message_id = message.message_id
    chat_type = message.chat_type or ""
    sender_id = ""

    if sender and sender.sender_id:
        sender_id = sender.sender_id.open_id or ""

    logger.info(
        "全局飞书收到消息: type=%s, sender=%s, chat_type=%s, message_id=%s",
        msg_type,
        sender_id,
        chat_type,
        message_id,
    )

    if _main_loop is None:
        logger.error("主 event loop 未设置，无法处理消息")
        return

    future = asyncio.run_coroutine_threadsafe(
        _handle_message_async(
            msg_type=msg_type,
            message_id=message_id,
            content=message.content or "{}",
        ),
        _main_loop,
    )
    try:
        future.result(timeout=120)
    except Exception:
        logger.exception("异步处理消息超时或异常")


async def _handle_message_async(
    *,
    msg_type: str,
    message_id: str,
    content: str,
) -> None:
    """异步处理消息（在主 event loop 中运行）。"""
    if _main_loop is None:
        set_main_loop(asyncio.get_running_loop())

    # 消息去重
    from app.core.redis import redis_client

    dedup_key = f"feishu:msg:{message_id}"
    is_new = await redis_client.set(dedup_key, "1", ex=120, nx=True)
    if not is_new:
        logger.info("重复消息已忽略: message_id=%s", message_id)
        return

    logger.info("全局飞书消息已记录: type=%s, message_id=%s", msg_type, message_id)


def _on_bitable_record_changed(data: P2DriveFileBitableRecordChangedV1) -> None:
    event = data.event
    if not event:
        return

    file_token = event.file_token or ""
    table_id = event.table_id or ""
    actions = [
        {
            "record_id": action.record_id,
            "action": action.action,
        }
        for action in (event.action_list or [])
    ]

    logger.info(
        "全局飞书收到多维表变更: file_token=%s table_id=%s revision=%s actions=%s",
        file_token,
        table_id,
        event.revision,
        len(actions),
    )

    if _main_loop is None:
        logger.error("主 event loop 未设置，无法处理多维表变更事件")
        return

    future = asyncio.run_coroutine_threadsafe(
        _handle_bitable_record_changed_async(
            file_token=file_token,
            table_id=table_id,
            revision=event.revision,
            update_time=event.update_time,
            actions=actions,
        ),
        _main_loop,
    )
    try:
        future.result(timeout=120)
    except Exception:
        logger.exception("异步处理多维表变更事件超时或异常")


async def _handle_bitable_record_changed_async(
    *,
    file_token: str,
    table_id: str,
    revision: int | None,
    update_time: int | None,
    actions: list[dict[str, str | None]],
) -> None:
    await event_bus.publish(
        FEISHU_BITABLE_RECORD_CHANGED_EVENT,
        {
            "file_token": file_token,
            "table_id": table_id,
            "revision": revision,
            "update_time": update_time,
            "actions": actions,
        },
    )
