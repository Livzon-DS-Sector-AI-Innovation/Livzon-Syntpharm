"""飞书机器人客户端 - 支持从数据库配置获取凭证"""

import asyncio
import logging
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


class FeishuClient:
    """飞书机器人客户端"""

    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._tenant_access_token: str | None = None

    async def get_tenant_access_token(self) -> str:
        """获取 tenant_access_token"""
        if self._tenant_access_token:
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

        self._tenant_access_token = data["tenant_access_token"]
        return self._tenant_access_token

    async def send_message(
        self,
        receive_id_type: str,
        receive_id: str,
        msg_type: str,
        content: str,
    ) -> dict[str, Any]:
        """发送消息"""

        token = await self.get_tenant_access_token()
        url = f"{self.BASE_URL}/im/v1/messages"
        params = {
            "receive_id_type": receive_id_type,
        }
        payload = {
            "receive_id": receive_id,
            "msg_type": msg_type,
            "content": content,  # 必须是字符串
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = await self._request("POST", url, params=params, json=payload, headers=headers)
        data = response.json()

        if data.get("code") != 0:
            raise ValueError(f"发送消息失败: {data.get('msg')}")

        return data  # type: ignore[no-any-return]

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

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """One HTTP call, retried per `AGENTS.md:314`.

        Every call in this class goes through here, so the 3-attempt / 1-2-4s policy
        lives in one place instead of being repeated at each of the six call sites.

        Retries timeouts, connection errors and protocol errors — failures where
        repeating can genuinely help — plus 5xx, where the far side is unwell. A 4xx
        is not retried: repeating a malformed request cannot fix it.
        """
        last_exc: Exception | None = None

        for attempt in range(_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
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
                    response.raise_for_status()
                # 5xx: the far side is unwell — retry it.
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
                        "method": method,
                        "url": url,
                        "error": str(last_exc),
                    },
                )
                await asyncio.sleep(_RETRY_BACKOFF[attempt])

        assert last_exc is not None
        raise last_exc

    def invalidate_token(self) -> Any:
        """使 token 失效，下次请求会重新获取"""
        self._tenant_access_token = None


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
                            "tag": "a",
                            "text": {
                                "tag": "lark_md",
                                "content": action.get("text", ""),
                            },
                            "href": {"url": action.get("url", "")},
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
