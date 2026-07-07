"""飞书机器人客户端 - 使用 App ID 和 App Secret 获取 tenant_access_token"""

import logging
from typing import Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class FeishuClient:
    """飞书机器人客户端"""

    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._tenant_access_token: Optional[str] = None

    async def get_tenant_access_token(self) -> str:
        """获取 tenant_access_token"""
        if self._tenant_access_token:
            return self._tenant_access_token

        url = f"{self.BASE_URL}/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
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
        content: dict,
    ) -> dict:
        """发送消息

        Args:
            receive_id_type: 接收者类型 - open_id/user_id/union_id/email/chat_id
            receive_id: 接收者 ID
            msg_type: 消息类型 - text/post/image/interactive/ark
            content: 消息内容（JSON 字符串）
        """
        token = await self.get_tenant_access_token()
        url = f"{self.BASE_URL}/im/v1/messages"
        params = {
            "receive_id_type": receive_id_type,
        }
        payload = {
            "receive_id": receive_id,
            "msg_type": msg_type,
            "content": content if isinstance(content, str) else content,
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url, params=params, json=payload, headers=headers
            )
            response.raise_for_status()
            data = response.json()

            if data.get("code") != 0:
                raise ValueError(f"发送消息失败: {data.get('msg')}")

            return data

    async def send_text_message(self, receive_id_type: str, receive_id: str, text: str) -> dict:
        """发送文本消息"""
        return await self.send_message(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            msg_type="text",
            content=f'{{"text": "{text}"}}',
        )

    async def send_card_message(
        self, receive_id_type: str, receive_id: str, card_content: dict
    ) -> dict:
        """发送卡片消息"""
        return await self.send_message(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            msg_type="interactive",
            content=card_content,
        )

    async def send_text_to_chat(self, chat_id: str, text: str) -> dict:
        """发送文本消息到群组"""
        return await self.send_text_message(
            receive_id_type="chat_id",
            receive_id=chat_id,
            text=text,
        )

    async def send_text_to_user(self, user_id: str, text: str) -> dict:
        """发送文本消息给用户"""
        return await self.send_text_message(
            receive_id_type="user_id",
            receive_id=user_id,
            text=text,
        )

    def invalidate_token(self):
        """使 token 失效，下次请求会重新获取"""
        self._tenant_access_token = None


# 全局客户端实例
_feishu_client: Optional[FeishuClient] = None


def get_feishu_client() -> FeishuClient:
    """获取飞书客户端实例"""
    global _feishu_client
    if _feishu_client is None:
        settings = get_settings()
        app_id = getattr(settings, "FEISHU_APP_ID", None)
        app_secret = getattr(settings, "FEISHU_APP_SECRET", None)

        if not app_id or not app_secret:
            raise ValueError(
                "飞书配置未设置，请设置 FEISHU_APP_ID 和 FEISHU_APP_SECRET 环境变量"
            )

        _feishu_client = FeishuClient(app_id, app_secret)

    return _feishu_client


async def send_feishu_notification(
    receive_id: str,
    receive_id_type: str = "chat_id",
    title: str = "",
    content: str = "",
) -> dict:
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
    actions: list = None,
) -> dict:
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
                            "tag": "a",
                            "text": {"tag": "lark_md", "content": action.get("text", "")},
                            "href": {"url": action.get("url", "")},
                        }
                    ],
                }
            )
        card_elements.extend(action_elements)

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