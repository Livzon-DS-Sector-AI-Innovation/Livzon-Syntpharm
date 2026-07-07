"""Livzon assistant Feishu card callback WebSocket client.

This client is only for Livzon assistant interactive card callbacks. It uses
the Livzon assistant Feishu app saved in identity.feishu_configs and keeps the
HTTP callback path available for production deployments with a public URL.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import ssl
import time
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import websockets
from fastapi import HTTPException

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.core.secrets import decrypt_secret
from app.platform.identity.repository import FeishuConfigRepository
from app.platform.identity.service import handle_livzon_feishu_card_action_event

logger = logging.getLogger(__name__)

FEISHU_DOMAIN = "https://open.feishu.cn"
WS_ENDPOINT_URL = f"{FEISHU_DOMAIN}/callback/ws/endpoint"

_stop: asyncio.Event | None = None
_ws_task: asyncio.Task | None = None
_ping_interval: int = 120
_last_error: str | None = None
_last_connected_at: float | None = None
_frame_count: dict[str, int] = {
    "received": 0,
    "control": 0,
    "data": 0,
    "event": 0,
    "card_action": 0,
    "error": 0,
}


async def _active_credentials() -> tuple[str | None, str | None]:
    async with async_session_factory() as db:
        config = await FeishuConfigRepository().get_active(db)
        if config is None:
            return None, None
        try:
            app_secret = decrypt_secret(config.encrypted_app_secret)
        except RuntimeError:
            logger.exception("Livzon 助手飞书 App Secret 解密失败，无法启动卡片长连接")
            return None, None
        return config.app_id, app_secret


async def _get_ws_url_and_config() -> tuple[str | None, int]:
    app_id, app_secret = await _active_credentials()
    if not app_id or not app_secret:
        return None, 0

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            WS_ENDPOINT_URL,
            json={"AppID": app_id, "AppSecret": app_secret},
        )
    if response.status_code != 200:
        logger.error("Livzon 飞书卡片 WS URL 获取失败 HTTP %s", response.status_code)
        return None, 0

    data = response.json()
    if data.get("code") != 0:
        logger.error(
            "Livzon 飞书卡片 WS URL 获取失败: code=%s msg=%s",
            data.get("code"),
            data.get("msg"),
        )
        return None, 0

    url = data.get("data", {}).get("URL", "")
    query = parse_qs(urlparse(url).query)
    service_id = int(query.get("service_id", ["0"])[0] or 0)

    client_config = data.get("data", {}).get("ClientConfig", {})
    global _ping_interval
    if isinstance(client_config, dict):
        interval = client_config.get("PingInterval", 0)
        if interval > 0:
            _ping_interval = interval

    logger.info(
        "Livzon 飞书卡片 WS URL 获取成功 service_id=%s ping_interval=%s",
        service_id,
        _ping_interval,
    )
    return url, service_id


def _build_ping_frame(service_id: int) -> bytes:
    from lark_oapi.ws.const import HEADER_TYPE
    from lark_oapi.ws.enum import FrameType, MessageType
    from lark_oapi.ws.pb.pbbp2_pb2 import Frame

    frame = Frame()
    header = frame.headers.add()
    header.key = HEADER_TYPE
    header.value = MessageType.PING.value
    frame.service = service_id
    frame.method = FrameType.CONTROL.value
    frame.SeqID = 0
    frame.LogID = 0
    return frame.SerializeToString()


def _build_ack_frame(frame, payload: dict[str, Any], biz_rt: int) -> bytes:
    from lark_oapi.ws.const import HEADER_BIZ_RT

    header = frame.headers.add()
    header.key = HEADER_BIZ_RT
    header.value = str(biz_rt)
    frame.payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return frame.SerializeToString()


async def _ping_loop(ws, service_id: int) -> None:
    while _stop is not None and not _stop.is_set():
        try:
            await ws.send(_build_ping_frame(service_id))
        except Exception:
            logger.warning("Livzon 飞书卡片 WS PING 失败")
            return
        try:
            await asyncio.wait_for(_stop.wait(), timeout=_ping_interval)
            return
        except TimeoutError:
            pass


def _event_type(payload: dict[str, Any]) -> str:
    header = payload.get("header")
    if isinstance(header, dict) and isinstance(header.get("event_type"), str):
        return header["event_type"]
    event = payload.get("event")
    if isinstance(event, dict):
        return str(event.get("type") or "")
    return str(payload.get("type") or "")


async def _handle_card_action_event(payload: dict[str, Any]) -> dict[str, Any]:
    async with async_session_factory() as db:
        try:
            result = await handle_livzon_feishu_card_action_event(db, payload=payload)
            await db.commit()
            return result
        except HTTPException as exc:
            await db.rollback()
            return {
                "toast": {
                    "type": "warning",
                    "content": str(exc.detail),
                }
            }
        except Exception:
            await db.rollback()
            logger.exception("Livzon 飞书卡片动作处理失败")
            return {
                "toast": {
                    "type": "error",
                    "content": "Livzon 助手记录卡片动作失败",
                }
            }


async def _dispatch_event(payload: dict[str, Any]) -> dict[str, Any]:
    event_type = _event_type(payload)
    if event_type != "card.action.trigger":
        return {"code": 200}

    _frame_count["card_action"] += 1
    result = await _handle_card_action_event(payload)
    card_json = json.dumps(result, ensure_ascii=False)
    return {
        "code": 200,
        "data": base64.b64encode(card_json.encode("utf-8")).decode("ascii"),
    }


async def _handle_binary_message(ws, message: bytes) -> None:
    _frame_count["received"] += 1
    start_ms = int(round(time.time() * 1000))
    try:
        from lark_oapi.ws.client import _get_by_key
        from lark_oapi.ws.const import HEADER_TYPE
        from lark_oapi.ws.enum import FrameType, MessageType
        from lark_oapi.ws.pb.pbbp2_pb2 import Frame

        frame = Frame()
        frame.ParseFromString(message)
        frame_type = FrameType(frame.method)

        if frame_type == FrameType.CONTROL:
            _frame_count["control"] += 1
            return

        if frame_type != FrameType.DATA:
            return

        _frame_count["data"] += 1
        message_type = MessageType(_get_by_key(frame.headers, HEADER_TYPE))
        if message_type == MessageType.EVENT:
            _frame_count["event"] += 1
            payload = json.loads(frame.payload.decode("utf-8"))
            ack_payload = await _dispatch_event(payload)
        else:
            ack_payload = {"code": 200}

        biz_rt = int(round(time.time() * 1000)) - start_ms
        await ws.send(_build_ack_frame(frame, ack_payload, biz_rt))
    except Exception as exc:
        _frame_count["error"] += 1
        global _last_error
        _last_error = f"{type(exc).__name__}: {exc}"
        logger.exception("Livzon 飞书卡片 WS 帧处理失败 (%d bytes)", len(message))


async def start_livzon_card_ws() -> None:
    """Start Livzon assistant Feishu card callback long connection."""
    settings = get_settings()
    if not settings.LIVZON_FEISHU_CARD_CALLBACK_WS_ENABLED:
        logger.info("Livzon 飞书卡片长连接未启用，跳过")
        return

    global _stop, _ws_task, _last_connected_at, _last_error
    _stop = asyncio.Event()
    _ws_task = asyncio.current_task()
    logger.info("启动 Livzon 助手飞书卡片长连接")

    while _stop is not None and not _stop.is_set():
        try:
            ws_url, service_id = await _get_ws_url_and_config()
            if not ws_url:
                _last_error = "Livzon 助手飞书配置缺失或无法获取 WS URL"
                await asyncio.wait_for(_stop.wait(), timeout=15)
                continue

            ssl_context = ssl.create_default_context()
            async with websockets.connect(
                ws_url,
                ssl=ssl_context,
                max_size=2**23,
                ping_interval=None,
                ping_timeout=None,
                close_timeout=5,
            ) as ws:
                _last_error = None
                _last_connected_at = time.time()
                logger.info("Livzon 助手飞书卡片长连接已连接")
                ping_task = asyncio.create_task(_ping_loop(ws, service_id))
                try:
                    while _stop is not None and not _stop.is_set():
                        try:
                            message = await asyncio.wait_for(ws.recv(), timeout=180)
                        except TimeoutError:
                            continue
                        if isinstance(message, bytes):
                            await _handle_binary_message(ws, message)
                finally:
                    ping_task.cancel()
        except asyncio.CancelledError:
            break
        except websockets.exceptions.ConnectionClosed as exc:
            _last_error = f"ConnectionClosed: {exc}"
            logger.warning("Livzon 飞书卡片长连接关闭，5 秒后重连: %s", exc)
        except TimeoutError:
            continue
        except Exception as exc:
            _last_error = f"{type(exc).__name__}: {exc}"
            logger.exception("Livzon 飞书卡片长连接异常，10 秒后重连")

        try:
            await asyncio.wait_for(_stop.wait(), timeout=10)
        except TimeoutError:
            pass

    logger.info("Livzon 助手飞书卡片长连接已停止")


async def stop_livzon_card_ws() -> None:
    global _stop
    if _stop is not None:
        _stop.set()


async def restart_livzon_card_ws() -> dict[str, Any]:
    global _ws_task
    await stop_livzon_card_ws()
    if _ws_task and not _ws_task.done():
        _ws_task.cancel()
        try:
            await _ws_task
        except asyncio.CancelledError:
            pass
    _ws_task = asyncio.create_task(start_livzon_card_ws())
    return await get_livzon_card_ws_status()


async def get_livzon_card_ws_status() -> dict[str, Any]:
    settings = get_settings()
    return {
        "enabled": settings.LIVZON_FEISHU_CARD_CALLBACK_WS_ENABLED,
        "running": _ws_task is not None and not _ws_task.done(),
        "last_connected_at": _last_connected_at,
        "last_error": _last_error,
        "ping_interval": _ping_interval,
        "frames": dict(_frame_count),
        "event_type": "card.action.trigger",
    }
