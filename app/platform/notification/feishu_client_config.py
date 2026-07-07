"""飞书机器人客户端 - 支持从数据库配置获取凭证"""

import logging
from typing import Optional

import httpx

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
        content: str,
    ) -> dict:
        """发送消息"""
        import json
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
        import json
        # 飞书API要求content是JSON字符串
        content_str = json.dumps(card_content, ensure_ascii=False)
        return await self.send_message(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            msg_type="interactive",
            content=content_str,
        )

    async def get_user_by_mobile_or_email(self, mobile: str = None, email: str = None) -> Optional[str]:
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

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 先尝试手机号
            if mobile:
                url = f"{self.BASE_URL}/contact/v3/users/batch_get_id"
                payload = {
                    "mobiles": [mobile],
                    "user_id_type": "open_id",
                }
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()

                if data.get("code") == 0:
                    user_list = data.get("data", {}).get("user_list", [])
                    if user_list and user_list[0].get("user_id"):
                        return user_list[0].get("user_id")

            # 再尝试邮箱
            if email:
                url = f"{self.BASE_URL}/contact/v3/users/batch_get_id"
                payload = {
                    "emails": [email],
                    "user_id_type": "open_id",
                }
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()

                if data.get("code") == 0:
                    user_list = data.get("data", {}).get("user_list", [])
                    if user_list and user_list[0].get("user_id"):
                        return user_list[0].get("user_id")

        return None

    async def get_contact_users(self, department_id: str = "0", page_size: int = 100) -> list:
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

        users = []
        page_token = None

        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                params = {
                    "department_id": department_id,
                    "department_id_type": "open_department_id",
                    "user_id_type": "open_id",
                    "page_size": page_size,
                }
                if page_token:
                    params["page_token"] = page_token

                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                if data.get("code") != 0:
                    raise ValueError(f"获取通讯录用户失败: {data.get('msg')}")

                items = data.get("data", {}).get("items", [])
                for user in items:
                    users.append({
                        "open_id": user.get("open_id"),
                        "name": user.get("name"),
                        "en_name": user.get("en_name"),
                        "email": user.get("email"),
                        "mobile": user.get("mobile"),
                        "avatar": user.get("avatar", {}).get("avatar_72") if user.get("avatar") else None,
                        "department_ids": user.get("department_ids"),
                    })

                # 检查是否还有下一页
                page_token = data.get("data", {}).get("page_token")
                has_more = data.get("data", {}).get("has_more", False)
                if not has_more or not page_token:
                    break

        return users

    async def get_departments(self, parent_department_id: str = "0") -> list:
        """获取部门列表"""
        token = await self.get_tenant_access_token()
        url = f"{self.BASE_URL}/contact/v3/departments"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        departments = []
        page_token = None

        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                params = {
                    "parent_department_id": parent_department_id,
                    "department_id_type": "open_department_id",
                    "user_id_type": "open_id",
                    "page_size": 100,
                }
                if page_token:
                    params["page_token"] = page_token

                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                if data.get("code") != 0:
                    raise ValueError(f"获取部门列表失败: {data.get('msg')}")

                items = data.get("data", {}).get("items", [])
                for dept in items:
                    departments.append({
                        "open_department_id": dept.get("open_department_id"),
                        "name": dept.get("name"),
                        "parent_department_id": dept.get("parent_department_id"),
                    })

                page_token = data.get("data", {}).get("page_token")
                has_more = data.get("data", {}).get("has_more", False)
                if not has_more or not page_token:
                    break

        return departments

    def invalidate_token(self):
        """使 token 失效，下次请求会重新获取"""
        self._tenant_access_token = None


async def send_feishu_card_from_config(
    app_id: Optional[str],
    app_secret: Optional[str],
    receive_id: str,
    receive_id_type: str = "chat_id",
    title: str = "",
    content: str = "",
    actions: list = None,
) -> dict:
    """从数据库配置发送飞书卡片消息

    如果 app_id 和 app_secret 为空，则使用环境变量中的配置
    """
    from app.core.config import get_settings

    if app_id and app_secret:
        client = FeishuClient(app_id, app_secret)
    else:
        # 使用环境变量中的配置
        settings = get_settings()
        app_id = getattr(settings, "FEISHU_APP_ID", None)
        app_secret = getattr(settings, "FEISHU_APP_SECRET", None)

        if not app_id or not app_secret:
            raise ValueError(
                "飞书配置未设置，请在提醒配置中填写 AppID 和 AppSecret，或设置环境变量"
            )
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
