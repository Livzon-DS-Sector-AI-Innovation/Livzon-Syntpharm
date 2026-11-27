"""`get_user_info` 重试：`GET /authen/v1/user_info` 是幂等读，必须按 3 次 / 1,2,4s 退避。

规则见 AGENTS.md「错误处理与容错/重试策略」：外部调用（LLM、飞书、能耗平台等）
最多 3 次重试，指数退避（1s, 2s, 4s）。同文件 `exchange_preauth_code` 与
`feishu/auth.py::_request_token` 已实现同一策略，这里补的是遗漏的 user_info。
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.platform.integrations.feishu import oauth as mod
from app.platform.integrations.feishu.oauth import FeishuOAuthClient, OAuthError


@pytest.fixture(autouse=True)
def _no_real_sleeping(monkeypatch: pytest.MonkeyPatch) -> None:
    """保留重试次数，把退避改成 0 秒（延迟本身不是被测对象）。"""
    monkeypatch.setattr(mod, "_RETRY_BACKOFF_SECONDS", (0, 0, 0))


def _response(body: dict[str, Any]) -> httpx.Response:
    return httpx.Response(200, json=body, request=httpx.Request("GET", mod._USER_INFO_URL))


def _patch_get(monkeypatch: pytest.MonkeyPatch, responses: list[Any]) -> list[int]:
    """按顺序返回响应（或抛异常），并记录尝试次数。"""
    calls: list[int] = []

    async def fake_get(self: Any, url: str, **kwargs: Any) -> httpx.Response:
        calls.append(1)
        result: Any = responses[min(len(calls) - 1, len(responses) - 1)]
        if isinstance(result, Exception):
            raise result
        assert isinstance(result, httpx.Response)
        return result

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    return calls


def _client() -> FeishuOAuthClient:
    return FeishuOAuthClient("app-id", "app-secret", "https://example.invalid/cb", "contact:user.base:readonly")


async def test_timeout_is_retried_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _patch_get(
        monkeypatch,
        [
            httpx.TimeoutException("timed out"),
            httpx.TimeoutException("timed out"),
            _response({"code": 0, "data": {"open_id": "ou_1", "name": "张三"}}),
        ],
    )

    info = await _client().get_user_info("u-token")

    assert info["open_id"] == "ou_1"
    assert len(calls) == 3, f"expected 3 attempts, made {len(calls)}"


async def test_gives_up_after_three_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _patch_get(monkeypatch, [httpx.ConnectError("no route")])

    with pytest.raises(httpx.ConnectError):
        await _client().get_user_info("u-token")

    assert len(calls) == 3, f"expected exactly 3 attempts, made {len(calls)}"


async def test_business_error_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    """飞书业务码错误（HTTP 200 + code != 0）说明凭据/授权问题，重试不会变好。"""
    calls = _patch_get(monkeypatch, [_response({"code": 99991663, "msg": "token invalid"})])

    with pytest.raises(OAuthError):
        await _client().get_user_info("u-token")

    assert len(calls) == 1, f"a business error was retried {len(calls)} times"
