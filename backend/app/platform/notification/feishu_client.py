"""飞书机器人客户端 - 使用 App ID 和 App Secret 获取 tenant_access_token"""

import asyncio
import json
import logging
import time
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# `AGENTS.md` — 外部调用（LLM、飞书…）最多 3 次重试，指数退避（1s, 2s, 4s）。
# 与 feishu_client_config.FeishuClient 保持同一策略：两个客户端行为一致。
_MAX_RETRIES = 3
_RETRY_BACKOFF = (1, 2, 4)
_RETRYABLE_STATUS = 500

#: tenant_access_token 有效期（秒）兜底值，响应里缺 ``expire`` 时使用
_TOKEN_DEFAULT_EXPIRE = 7200
#: 提前刷新余量（秒）：避免 token 在发送途中过期
_TOKEN_REFRESH_MARGIN = 300
#: 飞书 access token 失效错误码（invalid / expired），命中后丢弃缓存重取并重发一次
_INVALID_TOKEN_CODES = frozenset({99991663, 99991661, 99991668})
#: 4xx 响应体写入日志时的最大长度
_ERROR_BODY_LIMIT = 500


class _InvalidTokenError(Exception):
    """内部信号：飞书判定 access token 失效，需重取后重发。"""


def _error_payload(response: httpx.Response) -> dict[str, Any]:
    """解析飞书错误响应体；非 JSON 时返回空 dict（仅用于错误码判断与日志）。"""
    try:
        payload = response.json()
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


class FeishuClient:
    """飞书机器人客户端"""

    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._tenant_access_token: str | None = None
        #: token 过期时刻（``time.monotonic()`` 基准，便于测试替换）
        self._token_expires_at: float = 0.0
        #: 并发首取只打一次飞书
        self._token_lock = asyncio.Lock()

    async def get_tenant_access_token(self) -> str:
        """获取 tenant_access_token（到期前 5 分钟自动重取）。"""
        if self._tenant_access_token and time.monotonic() < self._token_expires_at:
            return self._tenant_access_token

        async with self._token_lock:
            # 锁内二次判断：并发首取时只有第一个协程真正请求飞书
            if self._tenant_access_token and time.monotonic() < self._token_expires_at:
                return self._tenant_access_token

            url = f"{self.BASE_URL}/auth/v3/tenant_access_token/internal"
            payload = {
                "app_id": self.app_id,
                "app_secret": self.app_secret,
            }

            response = await self._request("POST", url, json=payload)
            data = response.json()

            if data.get("code") != 0:
                raise ValueError(f"获取 tenant_access_token 失败: {data.get('msg')}")

            token = str(data["tenant_access_token"])
            expire = int(data.get("expire") or _TOKEN_DEFAULT_EXPIRE)
            self._tenant_access_token = token
            self._token_expires_at = time.monotonic() + max(expire - _TOKEN_REFRESH_MARGIN, 60)
            return token

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """One HTTP call, retried per AGENTS.md（最多 3 次、指数退避 1-2-4s）.

        Retries timeouts, connection errors and protocol errors — failures where
        repeating can genuinely help — plus 5xx, where the far side is unwell.
        A 4xx is not retried: repeating a malformed request cannot help.
        """
        last_exc: Exception | None = None

        for attempt in range(_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.request(method, url, **kwargs)
            except (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError) as exc:
                last_exc = exc
            else:
                if response.status_code < 400:
                    return response
                if response.status_code < _RETRYABLE_STATUS:
                    # 4xx：请求本身有问题，重试无意义，直接抛出与 raise_for_status() 一致的异常。
                    # 先记录飞书响应体，否则日志里只剩裸 400，看不到 code/msg（如 99991663）。
                    body = _error_payload(response)
                    logger.warning(
                        "Feishu request rejected",
                        extra={
                            "status_code": response.status_code,
                            "feishu_code": body.get("code"),
                            "feishu_msg": str(body.get("msg") or "")[:_ERROR_BODY_LIMIT],
                            "method": method,
                            "url": url,
                        },
                    )
                    response.raise_for_status()
                # 5xx：远端异常，重试。
                last_exc = httpx.HTTPStatusError(
                    f"HTTP {response.status_code}",
                    request=response.request,
                    response=response,
                )

            if attempt < _MAX_RETRIES - 1:
                logger.warning(
                    "Feishu request retry",
                    extra={
                        "attempt": attempt + 1,
                        "url": url,
                        "error": str(last_exc),
                    },
                )
                await asyncio.sleep(_RETRY_BACKOFF[attempt])

        assert last_exc is not None
        raise last_exc

    async def send_message(
        self,
        receive_id_type: str,
        receive_id: str,
        msg_type: str,
        content: dict[str, Any],
    ) -> dict[str, Any]:
        """发送消息

        Args:
            receive_id_type: 接收者类型 - open_id/user_id/union_id/email/chat_id
            receive_id: 接收者 ID
            msg_type: 消息类型 - text/post/image/interactive/ark
            content: 消息内容（JSON 字符串）
        """
        url = f"{self.BASE_URL}/im/v1/messages"
        params = {
            "receive_id_type": receive_id_type,
        }
        payload = {
            "receive_id": receive_id,
            "msg_type": msg_type,
            # 飞书要求 content 为 JSON 字符串；直接传 dict 会被拒（9499 invalid content）
            "content": content if isinstance(content, str) else json.dumps(content, ensure_ascii=False),
        }

        try:
            data = await self._send_once(url, params, payload)
        except _InvalidTokenError:
            # tenant_access_token 被吊销或提前过期：丢弃缓存重取，只重发一次
            self.invalidate_token()
            try:
                data = await self._send_once(url, params, payload)
            except _InvalidTokenError as retry_exc:
                raise ValueError(f"发送消息失败: {retry_exc}") from None

        if data.get("code") != 0:
            raise ValueError(f"发送消息失败: {data.get('msg')}")

        return data

    async def _send_once(
        self,
        url: str,
        params: dict[str, str],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """发送一次；token 失效时抛 ``_InvalidTokenError``，其余错误原样上抛。"""
        token = await self.get_tenant_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            response = await self._request("POST", url, params=params, json=payload, headers=headers)
        except httpx.HTTPStatusError as exc:
            # 飞书对失效 token 返回 HTTP 400，响应体里才是 99991663
            body = _error_payload(exc.response)
            if body.get("code") not in _INVALID_TOKEN_CODES:
                raise
            raise _InvalidTokenError(str(body.get("msg") or "tenant_access_token 失效")) from None

        data: dict[str, Any] = response.json()
        if data.get("code") in _INVALID_TOKEN_CODES:
            raise _InvalidTokenError(str(data.get("msg") or "tenant_access_token 失效"))
        return data

    async def send_text_message(self, receive_id_type: str, receive_id: str, text: str) -> dict[str, Any]:
        """发送文本消息"""
        return await self.send_message(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            msg_type="text",
            content=f'{{"text": "{text}"}}',  # type: ignore[arg-type]
        )

    async def send_card_message(
        self, receive_id_type: str, receive_id: str, card_content: dict[str, Any]
    ) -> dict[str, Any]:
        """发送卡片消息"""
        return await self.send_message(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            msg_type="interactive",
            content=card_content,
        )

    async def send_text_to_chat(self, chat_id: str, text: str) -> dict[str, Any]:
        """发送文本消息到群组"""
        return await self.send_text_message(
            receive_id_type="chat_id",
            receive_id=chat_id,
            text=text,
        )

    async def send_text_to_user(self, user_id: str, text: str) -> dict[str, Any]:
        """发送文本消息给用户"""
        return await self.send_text_message(
            receive_id_type="user_id",
            receive_id=user_id,
            text=text,
        )

    def invalidate_token(self) -> None:
        """使 token 失效，下次请求会重新获取"""
        self._tenant_access_token = None
        self._token_expires_at = 0.0


# 全局客户端实例
_feishu_client: FeishuClient | None = None


def get_feishu_client() -> FeishuClient:
    """获取飞书客户端实例"""
    global _feishu_client
    if _feishu_client is None:
        settings = get_settings()
        app_id = settings.feishu.platform.app_id
        app_secret = settings.feishu.platform.app_secret

        if not app_id or not app_secret:
            raise ValueError("飞书配置未设置，请设置 FEISHU__PLATFORM__APP_ID 和 FEISHU__PLATFORM__APP_SECRET 环境变量")

        _feishu_client = FeishuClient(app_id, app_secret)

    return _feishu_client


async def send_feishu_notification(
    receive_id: str,
    receive_id_type: str = "chat_id",
    title: str = "",
    content: str = "",
) -> dict[str, Any]:
    """发送飞书通知（简化接口）

    Args:
        receive_id: 接收者 ID
        receive_id_type: 接收者类型 - chat_id/user_id/email 等
        title: 标题
        content: 内容
    """
    client = get_feishu_client()

    # 构建富文本消息
    text = f"{title}\n{content}" if title else content

    return await client.send_text_message(
        receive_id_type=receive_id_type,
        receive_id=receive_id,
        text=text,
    )


async def send_feishu_card(
    receive_id: str,
    receive_id_type: str = "chat_id",
    title: str = "",
    content: str = "",
    actions: list[Any] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """发送飞书卡片消息

    Args:
        receive_id: 接收者 ID
        receive_id_type: 接收者类型
        title: 标题
        content: 内容
        actions: 按钮配置 [{"text": "按钮文本", "url": "链接"}]
    """
    client = get_feishu_client()

    card_elements = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": content,
            },
        }
    ]

    if actions:
        action_elements = []
        for action in actions:
            action_elements.append(
                {
                    "tag": "action",
                    "actions": [
                        {
                            # 卡片 v1 的 action 模块只支持 button，不支持 a（11310）
                            "tag": "button",
                            "text": {
                                "tag": "lark_md",
                                "content": action.get("text", ""),
                            },
                            "type": "primary",
                            "url": action.get("url", ""),
                        }
                    ],
                }
            )
        card_elements.extend(action_elements)  # type: ignore[arg-type]

    card_content = {
        "config": {"wide_screen_mode": True},
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**{title}**" if title else "",
                },
            },
            {"tag": "hr"},
            *card_elements,
        ],
    }

    return await client.send_card_message(
        receive_id_type=receive_id_type,
        receive_id=receive_id,
        card_content=card_content,
    )
