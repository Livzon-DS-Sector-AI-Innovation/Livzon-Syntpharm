"""飞书机器人客户端 - 支持从数据库配置获取凭证"""

import asyncio
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# `AGENTS.md:314` — 外部调用（LLM、飞书…）最多 3 次重试，指数退避（1s, 2s, 4s）.
# The same numbers the integrations client uses, applied here because this is the
# client that accepts per-call credentials — the reminder config stores its own
# AppID/AppSecret, which the integrations client's single `FeishuAuth` cannot express.
_MAX_RETRIES = 3
_RETRY_BACKOFF = (1, 2, 4)
# Retry 5xx (the far side is unwell) but not 4xx (the request is wrong — repeating it
# cannot help).
_RETRYABLE_STATUS = 500
#: 单次 HTTP 尝试超时（秒），与引入预算前的 ``httpx.AsyncClient(timeout=30.0)`` 一致
_HTTP_TIMEOUT = 30.0
#: 一次 ``send_message`` 的总外部等待预算 = 单次 ``_request`` 的原有上界（3×30s + 1+2+4s）。
#: 失效自愈的重发与首次发送共享这一预算，最坏耗时不再翻倍。
_CALL_BUDGET_SECONDS = _MAX_RETRIES * _HTTP_TIMEOUT + sum(_RETRY_BACKOFF)

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


def _remaining(deadline: float | None) -> float | None:
    """距离 ``deadline`` 的剩余秒数；没有预算时返回 ``None``，保持原有行为。"""
    return None if deadline is None else deadline - time.monotonic()


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

    async def get_tenant_access_token(self, *, deadline: float | None = None) -> str:
        """获取 tenant_access_token（到期前 5 分钟自动重取）。

        ``deadline`` 是调用方给的总时长预算（``time.monotonic()`` 基准）：冷缓存时
        取 token 的这次 HTTP 也算在预算内，不回退成「额外一份 97s」。
        """
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

            response = await self._request("POST", url, json=payload, deadline=deadline)
            data = response.json()

            if data.get("code") != 0:
                raise ValueError(f"获取 tenant_access_token 失败: {data.get('msg')}")

            token = str(data["tenant_access_token"])
            expire = int(data.get("expire") or _TOKEN_DEFAULT_EXPIRE)
            self._tenant_access_token = token
            self._token_expires_at = time.monotonic() + max(expire - _TOKEN_REFRESH_MARGIN, 60)
            return token

    async def send_message(
        self,
        receive_id_type: str,
        receive_id: str,
        msg_type: str,
        content: str,
    ) -> dict[str, Any]:
        """发送消息"""

        url = f"{self.BASE_URL}/im/v1/messages"
        params = {
            "receive_id_type": receive_id_type,
        }
        payload = {
            "receive_id": receive_id,
            "msg_type": msg_type,
            "content": content,  # 必须是字符串
        }

        # 首次发送与自愈重发共享同一份总时长预算，避免最坏耗时翻倍
        deadline = time.monotonic() + _CALL_BUDGET_SECONDS
        try:
            data = await self._send_once(url, params, payload, deadline=deadline)
        except _InvalidTokenError:
            # tenant_access_token 被吊销或提前过期：丢弃缓存重取，只重发一次
            self.invalidate_token()
            try:
                data = await self._send_once(url, params, payload, deadline=deadline)
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
        *,
        deadline: float | None = None,
    ) -> dict[str, Any]:
        """发送一次；token 失效时抛 ``_InvalidTokenError``，其余错误原样上抛。"""
        token = await self.get_tenant_access_token(deadline=deadline)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            response = await self._request("POST", url, params=params, json=payload, headers=headers, deadline=deadline)
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
            content=f'{{"text": "{text}"}}',
        )

    async def send_card_message(
        self, receive_id_type: str, receive_id: str, card_content: dict[str, Any]
    ) -> dict[str, Any]:
        """发送卡片消息"""
        import json

        # 飞书API要求content是JSON字符串
        content_str = json.dumps(card_content, ensure_ascii=False)
        return await self.send_message(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            msg_type="interactive",
            content=content_str,
        )

    async def get_user_by_mobile_or_email(
        self,
        mobile: str = None,  # type: ignore[assignment]
        email: str = None,  # type: ignore[assignment]
    ) -> str | None:
        """通过手机号或邮箱获取用户的 open_id

        Args:
            mobile: 手机号
            email: 邮箱

        Returns:
            用户的 open_id，如果未找到返回 None
        """
        token = await self.get_tenant_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # 先尝试手机号
        if mobile:
            url = f"{self.BASE_URL}/contact/v3/users/batch_get_id"
            payload = {
                "mobiles": [mobile],
                "user_id_type": "open_id",
            }
            response = await self._request("POST", url, headers=headers, json=payload)
            data = response.json()

            if data.get("code") == 0:
                user_list = data.get("data", {}).get("user_list", [])
                if user_list and user_list[0].get("user_id"):
                    return user_list[0].get("user_id")  # type: ignore[no-any-return]

        # 再尝试邮箱
        if email:
            url = f"{self.BASE_URL}/contact/v3/users/batch_get_id"
            payload = {
                "emails": [email],
                "user_id_type": "open_id",
            }
            response = await self._request("POST", url, headers=headers, json=payload)
            data = response.json()

            if data.get("code") == 0:
                user_list = data.get("data", {}).get("user_list", [])
                if user_list and user_list[0].get("user_id"):
                    return user_list[0].get("user_id")  # type: ignore[no-any-return]

        return None

    async def get_contact_users(self, department_id: str = "0", page_size: int = 100) -> list[Any]:
        """获取通讯录用户列表

        Args:
            department_id: 部门ID，默认为根部门(0)
            page_size: 每页数量，默认100

        Returns:
            用户列表，每个用户包含 id, name, en_name, avatar, email, mobile, department_ids 等
        """
        token = await self.get_tenant_access_token()
        url = f"{self.BASE_URL}/contact/v3/users"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        users: list[dict[str, Any]] = []
        page_token = None

        while True:
            params = {
                "department_id": department_id,
                "department_id_type": "open_department_id",
                "user_id_type": "open_id",
                "page_size": page_size,
            }
            if page_token:
                params["page_token"] = page_token

            response = await self._request("GET", url, headers=headers, params=params)
            data = response.json()

            if data.get("code") != 0:
                raise ValueError(f"获取通讯录用户失败: {data.get('msg')}")

            items = data.get("data", {}).get("items", [])
            for user in items:
                users.append(
                    {
                        "open_id": user.get("open_id"),
                        "name": user.get("name"),
                        "en_name": user.get("en_name"),
                        "email": user.get("email"),
                        "mobile": user.get("mobile"),
                        "avatar": user.get("avatar", {}).get("avatar_72") if user.get("avatar") else None,
                        "department_ids": user.get("department_ids"),
                    }
                )

            # 检查是否还有下一页
            page_token = data.get("data", {}).get("page_token")
            has_more = data.get("data", {}).get("has_more", False)
            if not has_more or not page_token:
                break

        return users

    async def get_departments(self, parent_department_id: str = "0") -> list[Any]:
        """获取部门列表"""
        token = await self.get_tenant_access_token()
        url = f"{self.BASE_URL}/contact/v3/departments"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        departments: list[dict[str, Any]] = []
        page_token = None

        while True:
            params = {
                "parent_department_id": parent_department_id,
                "department_id_type": "open_department_id",
                "user_id_type": "open_id",
                "page_size": 100,
            }
            if page_token:
                params["page_token"] = page_token

            response = await self._request("GET", url, headers=headers, params=params)
            data = response.json()

            if data.get("code") != 0:
                raise ValueError(f"获取部门列表失败: {data.get('msg')}")

            items = data.get("data", {}).get("items", [])
            for dept in items:
                departments.append(
                    {
                        "open_department_id": dept.get("open_department_id"),
                        "name": dept.get("name"),
                        "parent_department_id": dept.get("parent_department_id"),
                    }
                )

            page_token = data.get("data", {}).get("page_token")
            has_more = data.get("data", {}).get("has_more", False)
            if not has_more or not page_token:
                break

        return departments

    async def _request(
        self,
        method: str,
        url: str,
        *,
        deadline: float | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """One HTTP call, retried per `AGENTS.md:314`.

        Every call in this class goes through here, so the 3-attempt / 1-2-4s policy
        lives in one place instead of being repeated at each of the six call sites.

        Retries timeouts, connection errors and protocol errors — failures where
        repeating can genuinely help — plus 5xx, where the far side is unwell. A 4xx
        is not retried: repeating a malformed request cannot fix it.

        ``deadline``（``time.monotonic()`` 基准）把这次调用计入调用方的总时长预算：
        每次尝试的超时压到 ``min(_HTTP_TIMEOUT, 剩余)``，剩余预算不足以覆盖退避 +
        下一次尝试时直接收尾，不再发起新请求。
        """
        last_exc: Exception | None = None

        for attempt in range(_MAX_RETRIES):
            remaining = _remaining(deadline)
            if remaining is not None and remaining <= 0:
                logger.warning(
                    "Feishu call budget exhausted",
                    extra={"attempt": attempt + 1, "method": method, "url": url},
                )
                break
            timeout = _HTTP_TIMEOUT if remaining is None else min(_HTTP_TIMEOUT, remaining)
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.request(method, url, **kwargs)
            except (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError) as exc:
                last_exc = exc
            else:
                # Not a transport failure, so the status decides — and it decides
                # *outside* the retry path, because the two cases differ:
                if response.status_code < 400:
                    return response
                if response.status_code < _RETRYABLE_STATUS:
                    # 4xx: a malformed request. Repeating it cannot help, and the
                    # caller needs the status, not a JSON parse error from an error
                    # page. Raise the same exception the old `raise_for_status()` did.
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
                # 5xx: the far side is unwell — retry it.
                last_exc = httpx.HTTPStatusError(
                    f"HTTP {response.status_code}",
                    request=response.request,
                    response=response,
                )

            if attempt < _MAX_RETRIES - 1:
                remaining = _remaining(deadline)
                if remaining is not None and remaining <= _RETRY_BACKOFF[attempt]:
                    logger.warning(
                        "Feishu retry skipped: budget exhausted",
                        extra={"attempt": attempt + 1, "method": method, "url": url},
                    )
                    break
                logger.warning(
                    "Feishu request retry",
                    extra={
                        "attempt": attempt + 1,
                        "method": method,
                        "url": url,
                        "error": str(last_exc),
                    },
                )
                await asyncio.sleep(_RETRY_BACKOFF[attempt])

        if last_exc is None:
            # 预算在首次尝试前就耗尽：没有原始异常可抛，用 httpx 超时族表达。
            raise httpx.TimeoutException("飞书调用超出总时长预算")
        raise last_exc

    def invalidate_token(self) -> None:
        """使 token 失效，下次请求会重新获取"""
        self._tenant_access_token = None
        self._token_expires_at = 0.0


async def send_feishu_card_from_config(
    app_id: str | None,
    app_secret: str | None,
    receive_id: str,
    receive_id_type: str = "chat_id",
    title: str = "",
    content: str = "",
    actions: list[Any] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """从数据库配置发送飞书卡片消息

    如果 app_id 和 app_secret 为空，则使用环境变量中的配置
    """
    from app.core.config import get_settings

    if app_id and app_secret:
        client = FeishuClient(app_id, app_secret)
    else:
        # 使用环境变量中的配置
        settings = get_settings()
        app_id = settings.feishu.platform.app_id
        app_secret = settings.feishu.platform.app_secret

        if not app_id or not app_secret:
            raise ValueError("飞书配置未设置，请在提醒配置中填写 AppID 和 AppSecret，或设置环境变量")
        client = FeishuClient(app_id, app_secret)

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
