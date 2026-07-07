"""Feishu IM message sending."""

import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.platform.integrations.feishu.auth import FeishuAuth
from app.platform.integrations.feishu.utils import OPEN_API_BASE_URL

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FeishuMessageSendResult:
    ok: bool
    message_id: str | None = None
    code: int | None = None
    error_message: str | None = None
    raw: dict[str, Any] | None = None


def build_text_message_content(text: str) -> str:
    return json.dumps({"text": text}, ensure_ascii=False)


def build_simple_card_content(
    *,
    title: str,
    markdown: str,
    header_template: str = "blue",
    button_text: str | None = None,
    button_url: str | None = None,
) -> str:
    card: dict[str, Any] = {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": header_template,
            "title": {"tag": "plain_text", "content": title},
        },
        "elements": [{"tag": "markdown", "content": markdown}],
    }
    if button_text and button_url:
        card["elements"].append(
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": button_text},
                        "type": "primary",
                        "url": button_url,
                    }
                ],
            }
        )
    return json.dumps(card, ensure_ascii=False)


def build_callback_card_content(
    *,
    title: str,
    markdown: str,
    actions: list[dict[str, str]],
    header_template: str = "blue",
) -> str:
    card: dict[str, Any] = {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": header_template,
            "title": {"tag": "plain_text", "content": title},
        },
        "elements": [{"tag": "markdown", "content": markdown}],
    }
    button_actions: list[dict[str, Any]] = []
    for action in actions:
        button_actions.append(
            {
                "tag": "button",
                "text": {
                    "tag": "plain_text",
                    "content": action["label"],
                },
                "type": action.get("button_type") or "primary",
                "value": {
                    "action_id": action["action_id"],
                    "action_key": action["action_key"],
                },
                "confirm": {
                    "title": {"tag": "plain_text", "content": "确认操作"},
                    "text": {
                        "tag": "plain_text",
                        "content": f"确认{action['label']}？",
                    },
                },
            }
        )
    if button_actions:
        card["elements"].append({"tag": "action", "actions": button_actions})
    return json.dumps(card, ensure_ascii=False)


def build_callback_status_card_content(
    *,
    title: str,
    markdown: str,
    status_text: str,
    header_template: str = "green",
) -> str:
    card: dict[str, Any] = {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": header_template,
            "title": {"tag": "plain_text", "content": title},
        },
        "elements": [
            {"tag": "markdown", "content": markdown},
            {"tag": "hr"},
            {"tag": "markdown", "content": status_text},
        ],
    }
    return json.dumps(card, ensure_ascii=False)


async def send_feishu_message(
    *,
    tenant_access_token: str,
    receive_id: str,
    msg_type: str,
    content: str,
    receive_id_type: str = "open_id",
) -> FeishuMessageSendResult:
    """Send one Feishu IM message with an explicit tenant access token."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{OPEN_API_BASE_URL}/im/v1/messages",
            headers={
                "Authorization": f"Bearer {tenant_access_token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            params={"receive_id_type": receive_id_type},
            json={
                "receive_id": receive_id,
                "msg_type": msg_type,
                "content": content,
            },
        )
        resp.raise_for_status()
        body = resp.json()

    code = body.get("code")
    data = body.get("data") or {}
    if code == 0:
        return FeishuMessageSendResult(
            ok=True,
            message_id=data.get("message_id"),
            code=0,
            raw=body,
        )
    return FeishuMessageSendResult(
        ok=False,
        code=code,
        error_message=body.get("msg") or str(body),
        raw=body,
    )


async def update_feishu_message(
    *,
    tenant_access_token: str,
    message_id: str,
    content: str,
) -> FeishuMessageSendResult:
    """Update an existing Feishu interactive card message with explicit token."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.patch(
            f"{OPEN_API_BASE_URL}/im/v1/messages/{message_id}",
            headers={
                "Authorization": f"Bearer {tenant_access_token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            json={"content": content},
        )
        resp.raise_for_status()
        body = resp.json()

    code = body.get("code")
    data = body.get("data") or {}
    if code == 0:
        return FeishuMessageSendResult(
            ok=True,
            message_id=data.get("message_id") or message_id,
            code=0,
            raw=body,
        )
    return FeishuMessageSendResult(
        ok=False,
        code=code,
        error_message=body.get("msg") or str(body),
        raw=body,
    )


class FeishuIM:
    """Send messages via Feishu IM API."""

    base_url = "https://open.feishu.cn/open-apis"

    def __init__(self, auth: FeishuAuth | None = None) -> None:
        self._auth = auth or FeishuAuth.default()

    async def _batch_get_ids(self, payload: dict) -> dict[str, str]:
        """Internal helper to call batch_get_id and extract open_id mapping."""
        token = await self._auth.get_token()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/contact/v3/users/batch_get_id",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json=payload,
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(
                "Feishu batch_get_id failed: "
                f"code={data.get('code')}, msg={data.get('msg')}"
            )

        result: dict[str, str] = {}
        for item in data.get("data", {}).get("user_list", []):
            open_id = item.get("open_id") or item.get("user_id")
            if not open_id:
                continue
            # Match back by whichever key was in the request
            if "mobiles" in payload:
                key = item.get("mobile")
            elif "emails" in payload:
                key = item.get("email")
            elif "employee_ids" in payload:
                key = item.get("employee_id")
            else:
                key = None
            if key:
                result[key] = open_id
        return result

    async def batch_get_open_ids_by_mobile(self, mobiles: list[str]) -> dict[str, str]:
        """Return mapping mobile -> open_id."""
        return await self._batch_get_ids({"mobiles": mobiles, "include_resigned": True})

    async def batch_get_open_ids_by_email(self, emails: list[str]) -> dict[str, str]:
        """Return mapping email -> open_id."""
        return await self._batch_get_ids({"emails": emails, "include_resigned": True})

    async def batch_get_open_ids_by_employee_id(
        self, employee_ids: list[str]
    ) -> dict[str, str]:
        """Return mapping employee_id -> open_id."""
        return await self._batch_get_ids(
            {"employee_ids": employee_ids, "include_resigned": True}
        )

    async def send_text_message(
        self, receive_id: str, content: str, *, receive_id_type: str = "open_id"
    ) -> None:
        """Send text message to a single user."""
        token = await self._auth.get_token()
        result = await send_feishu_message(
            tenant_access_token=token,
            receive_id=receive_id,
            receive_id_type=receive_id_type,
            msg_type="text",
            content=build_text_message_content(content),
        )
        if not result.ok:
            raise RuntimeError(
                "Feishu send message failed: "
                f"code={result.code}, msg={result.error_message}"
            )
