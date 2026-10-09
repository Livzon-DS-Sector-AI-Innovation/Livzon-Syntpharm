"""The configured Feishu client retries per `AGENTS.md:314`.

> 外部调用（LLM、飞书、能耗平台等）最多 3 次重试，指数退避（1s, 2s, 4s）

`feishu_client_config.py` had **no** retry: each method opened its own
`httpx.AsyncClient` and called `raise_for_status()` straight through. A sibling client
(`app/platform/integrations/feishu/client.py`) already implemented the policy, but
takes a single global `FeishuAuth` — this client is the one that accepts per-call
credentials from the reminder config, so it is the one that needed the fix.

These tests exist because "the retry loop is present" is not evidence that it retries.
They assert the behaviour, including the case the rule implies and a naive `except`
would get wrong: **a 4xx must not be retried.**
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.platform.notification import feishu_client_config as mod
from app.platform.notification.feishu_client_config import FeishuClient


@pytest.fixture(autouse=True)
def _no_real_sleeping(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the backoff but make it instant — the delays are not what is under test."""
    monkeypatch.setattr(mod, "_RETRY_BACKOFF", (0, 0, 0))


def _ok() -> httpx.Response:
    return httpx.Response(
        200,
        json={"code": 0, "tenant_access_token": "t-123"},
        request=httpx.Request("POST", "https://example.invalid"),
    )


def _status(code: int) -> httpx.Response:
    return httpx.Response(code, request=httpx.Request("POST", "https://example.invalid"))


def _patch_request(monkeypatch: pytest.MonkeyPatch, responses: list[Any]) -> list[int]:
    """Return each response in turn; record how many attempts were made."""
    calls: list[int] = []

    async def fake_request(self: Any, method: str, url: str, **kwargs: Any) -> httpx.Response:
        calls.append(1)
        result: Any = responses[min(len(calls) - 1, len(responses) - 1)]
        if isinstance(result, Exception):
            raise result
        assert isinstance(result, httpx.Response)
        return result

    monkeypatch.setattr(httpx.AsyncClient, "request", fake_request)
    return calls


async def test_timeout_is_retried_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two timeouts, then success — the third attempt returns the token."""
    calls = _patch_request(
        monkeypatch,
        [
            httpx.TimeoutException("timed out"),
            httpx.TimeoutException("timed out"),
            _ok(),
        ],
    )

    token: Any = await FeishuClient("app", "secret").get_tenant_access_token()

    assert token == "t-123"
    assert len(calls) == 3, f"expected 3 attempts, made {len(calls)}"


async def test_connection_error_is_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _patch_request(monkeypatch, [httpx.ConnectError("no route"), _ok()])

    token: Any = await FeishuClient("app", "secret").get_tenant_access_token()

    assert token == "t-123"
    assert len(calls) == 2


async def test_five_hundred_is_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    """A 5xx means the far side is unwell — worth repeating."""
    calls = _patch_request(monkeypatch, [_status(503), _status(500), _ok()])

    token: Any = await FeishuClient("app", "secret").get_tenant_access_token()

    assert token == "t-123"
    assert len(calls) == 3


async def test_four_hundred_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    """A 4xx is a malformed request. Repeating it cannot help, so it must fail fast.

    This is the case a bare `except Exception` would get wrong by retrying.
    """
    calls = _patch_request(monkeypatch, [_status(400)])

    with pytest.raises(httpx.HTTPStatusError):
        await FeishuClient("app", "secret").get_tenant_access_token()

    assert len(calls) == 1, f"a 400 was retried {len(calls)} times; it must not be retried at all"


async def test_gives_up_after_three_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    """The rule says 最多 3 次 — it must stop, not loop."""
    calls = _patch_request(monkeypatch, [httpx.TimeoutException("timed out")])

    with pytest.raises(httpx.TimeoutException):
        await FeishuClient("app", "secret").get_tenant_access_token()

    assert len(calls) == 3, f"expected exactly 3 attempts, made {len(calls)}"
