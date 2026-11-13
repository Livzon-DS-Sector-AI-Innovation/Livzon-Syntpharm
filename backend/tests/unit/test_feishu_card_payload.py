"""Card messages must be shaped the way Feishu actually accepts them.

Two payload bugs made every interactive-card send fail with HTTP 400 while plain
text messages worked, so nothing ever reached the recipient and the only trace was
a bare `raise_for_status()` in the logs:

1. `content` was posted as a JSON **object**. Feishu requires a JSON **string**
   (`9499 invalid content`).
2. Action buttons used `tag: "a"`, which the card v1 action block rejects
   (`11310 unsupported action tag`). Only `tag: "button"` is accepted, and the link
   goes in `url` rather than `href: {url}`.

Both are pinned here so a future "cleanup" of the payload cannot silently re-break
delivery for every module that sends cards through this client.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from app.platform.notification import feishu_client as mod
from app.platform.notification.feishu_client import FeishuClient


def _capture_requests(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Record the JSON body of every outgoing request; always answer success."""
    bodies: list[dict[str, Any]] = []

    async def fake_request(self: Any, method: str, url: str, **kwargs: Any) -> httpx.Response:
        bodies.append(kwargs.get("json") or {})
        return httpx.Response(
            200,
            json={"code": 0, "data": {"message_id": "om_test"}},
            request=httpx.Request(method, url),
        )

    async def fake_token(self: Any) -> str:
        return "t-test"

    monkeypatch.setattr(httpx.AsyncClient, "request", fake_request)
    monkeypatch.setattr(FeishuClient, "get_tenant_access_token", fake_token)
    return bodies


async def test_dict_content_is_serialized_before_sending(monkeypatch: pytest.MonkeyPatch) -> None:
    """A dict card body must go out as a JSON string, not as an object."""
    bodies = _capture_requests(monkeypatch)
    card = {"config": {"wide_screen_mode": True}, "elements": [{"tag": "hr"}]}

    await FeishuClient("app", "secret").send_card_message(
        receive_id_type="open_id", receive_id="ou_x", card_content=card
    )

    sent = bodies[-1]
    assert sent["msg_type"] == "interactive"
    assert isinstance(sent["content"], str), "Feishu rejects object content with 9499"
    assert json.loads(sent["content"]) == card


async def test_card_button_uses_button_tag_with_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Card v1 action blocks only accept `button`; `a` fails with 11310."""
    captured: list[dict[str, Any]] = []

    class _StubClient:
        async def send_card_message(self, receive_id_type: str, receive_id: str, card_content: dict[str, Any]) -> Any:
            captured.append({"receive_id_type": receive_id_type, "receive_id": receive_id, "card": card_content})
            return {"code": 0}

    monkeypatch.setattr(mod, "get_feishu_client", lambda: _StubClient())

    await mod.send_feishu_card(
        receive_id="ou_x",
        title="待你处理",
        content="编号 PC-1",
        actions=[{"text": "去审批", "url": "http://example.test/quality/deviation/x#review"}],
    )

    elements = captured[0]["card"]["elements"]
    action_blocks = [item for item in elements if item.get("tag") == "action"]
    assert len(action_blocks) == 1
    button = action_blocks[0]["actions"][0]
    assert button["tag"] == "button"
    assert button["url"].endswith("#review")
    assert button["text"]["content"] == "去审批"
    assert "href" not in button


async def test_no_unsupported_anchor_tags_anywhere(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guard the whole card tree, not just the first action block."""
    captured: list[dict[str, Any]] = []

    class _StubClient:
        async def send_card_message(self, receive_id_type: str, receive_id: str, card_content: dict[str, Any]) -> Any:
            captured.append({"card": card_content})
            return {"code": 0}

    monkeypatch.setattr(mod, "get_feishu_client", lambda: _StubClient())

    await mod.send_feishu_card(
        receive_id="ou_x",
        title="t",
        content="c",
        actions=[
            {"text": "去审批", "url": "http://example.test/a"},
            {"text": "去处理", "url": "http://example.test/b"},
        ],
    )

    def tags(node: Any) -> list[str]:
        found: list[str] = []
        if isinstance(node, dict):
            tag = node.get("tag")
            if isinstance(tag, str):
                found.append(tag)
            for value in node.values():
                found.extend(tags(value))
        elif isinstance(node, list):
            for item in node:
                found.extend(tags(item))
        return found

    card_tags = tags(captured[0]["card"])
    assert "a" not in card_tags, "card v1 rejects tag 'a' with error 11310"
    assert card_tags.count("button") == 2
