"""tenant_access_token 缓存 / 过期重取 / 失效自愈的回归测试。

背景：生产出现「偏差流转飞书卡片连续 400」。旧实现取到一次 token 就永久复用
（``invalidate_token()`` 全仓零调用点），而飞书 tenant_access_token 约 2 小时过期；
过期后飞书返回 HTTP 400 + body ``code=99991663``，旧实现既看不到 body 错误码，
也不会重取 token。这里覆盖四个行为，两个飞书客户端同构，因此参数化运行：

- token 未过期 → 复用缓存，不重复请求 token 接口；
- token 过期 → 重新请求 token 接口；
- 发送返回失效码（HTTP 200 或 400）→ 丢弃缓存、重取、只重发一次并成功；
- 重发仍失效 → 抛 ``ValueError``，且只重发一次。

飞书 HTTP 一律 mock，不发起真实请求。
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.platform.notification import feishu_client, feishu_client_config

_TOKEN_URL_SUFFIX = "/auth/v3/tenant_access_token/internal"
_INVALID_TOKEN = {"code": 99991663, "msg": "invalid access token"}
_OK = {"code": 0, "data": {}}


class _FakeGateway:
    """按 URL 分发：token 接口每次发新 token，消息接口按脚本顺序返回。"""

    def __init__(self, send_script: list[tuple[int, dict[str, Any]]]) -> None:
        self._send_script = send_script
        self.token_calls = 0
        self.send_calls = 0

    async def request(self, method: str, url: str) -> httpx.Response:
        request = httpx.Request(method, url)
        if url.endswith(_TOKEN_URL_SUFFIX):
            self.token_calls += 1
            return httpx.Response(
                200,
                json={"code": 0, "tenant_access_token": f"t-{self.token_calls}", "expire": 7200},
                request=request,
            )
        index = min(self.send_calls, len(self._send_script) - 1)
        self.send_calls += 1
        status, payload = self._send_script[index]
        return httpx.Response(status, json=payload, request=request)


@pytest.fixture(autouse=True)
def _no_real_sleeping(monkeypatch: pytest.MonkeyPatch) -> None:
    """保留退避策略但去掉真实等待——延迟不是本测试的关注点。"""
    for module in (feishu_client, feishu_client_config):
        monkeypatch.setattr(module, "_RETRY_BACKOFF", (0, 0, 0))


@pytest.fixture(params=[feishu_client.FeishuClient, feishu_client_config.FeishuClient], ids=["platform", "config"])
def client(request: pytest.FixtureRequest) -> Any:
    return request.param("app", "secret")


def _patch_http(monkeypatch: pytest.MonkeyPatch, gateway: _FakeGateway) -> None:
    async def fake_request(_self: httpx.AsyncClient, method: str, url: str, **_kwargs: Any) -> httpx.Response:
        return await gateway.request(method, url)

    monkeypatch.setattr(httpx.AsyncClient, "request", fake_request)


async def test_valid_token_is_reused(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """用例 A：token 未过期，第二次取 token 不再请求飞书。"""
    gateway = _FakeGateway([(200, _OK)])
    _patch_http(monkeypatch, gateway)

    first = await client.get_tenant_access_token()
    second = await client.get_tenant_access_token()

    assert first == second
    assert gateway.token_calls == 1


async def test_expired_token_is_refetched(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """用例 B：过期时刻已到，必须重新请求 token 接口。"""
    gateway = _FakeGateway([(200, _OK)])
    _patch_http(monkeypatch, gateway)

    first = await client.get_tenant_access_token()
    client._token_expires_at = 0.0
    second = await client.get_tenant_access_token()

    assert first != second
    assert gateway.token_calls == 2


async def test_invalid_token_code_retries_once_and_succeeds(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """用例 C：HTTP 200 但 code=99991663 → 丢弃缓存、重取、重发一次后成功。"""
    gateway = _FakeGateway([(200, _INVALID_TOKEN), (200, _OK)])
    _patch_http(monkeypatch, gateway)

    result = await client.send_message("open_id", "ou_test", "text", '{"text":"hi"}')

    assert result["code"] == 0
    assert gateway.token_calls == 2
    assert gateway.send_calls == 2


async def test_invalid_token_on_http_400_is_also_healed(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """生产实际形态：飞书返回 HTTP 400 + body code=99991663，也要自愈且只重发一次。"""
    gateway = _FakeGateway([(400, _INVALID_TOKEN), (200, _OK)])
    _patch_http(monkeypatch, gateway)

    result = await client.send_message("open_id", "ou_test", "text", '{"text":"hi"}')

    assert result["code"] == 0
    assert gateway.token_calls == 2
    # 4xx 本身不重试；两次发送来自「失效自愈」的一次重发
    assert gateway.send_calls == 2


async def test_retry_still_invalid_raises_after_one_retry(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """用例 D：重发仍失效 → 抛 ValueError，且只重发一次。"""
    gateway = _FakeGateway([(200, _INVALID_TOKEN)])
    _patch_http(monkeypatch, gateway)

    with pytest.raises(ValueError):
        await client.send_message("open_id", "ou_test", "text", '{"text":"hi"}')

    assert gateway.token_calls == 2
    assert gateway.send_calls == 2


async def test_other_4xx_is_not_retried(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """非 token 失效的 4xx 保持原行为：不重试、不重取 token、抛 HTTPStatusError。"""
    gateway = _FakeGateway([(400, {"code": 10002, "msg": "bad request"})])
    _patch_http(monkeypatch, gateway)

    with pytest.raises(httpx.HTTPStatusError):
        await client.send_message("open_id", "ou_test", "text", '{"text":"hi"}')

    assert gateway.token_calls == 1
    assert gateway.send_calls == 1
