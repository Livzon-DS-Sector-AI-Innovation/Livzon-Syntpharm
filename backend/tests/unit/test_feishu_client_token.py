"""tenant_access_token 缓存 / 过期重取 / 失效自愈的回归测试。

背景：生产出现「偏差流转飞书卡片连续 400」。旧实现取到一次 token 就永久复用
（``invalidate_token()`` 全仓零调用点），而飞书 tenant_access_token 约 2 小时过期；
过期后飞书返回 HTTP 400 + body ``code=99991663``，旧实现既看不到 body 错误码，
也不会重取 token。两个飞书客户端同构，因此参数化运行，覆盖：

- token 未过期 → 复用缓存，不重复请求 token 接口；
- token 过期 → 重新请求 token 接口；
- 发送返回失效码（HTTP 200 或 400）→ 丢弃缓存、重取、只重发一次并成功；
- 重发仍失效 → 抛 ``ValueError``，且只重发一次；
- 一次 ``send_message`` 受总时长预算约束 → 自愈重发与首次发送共享同一份预算，
  预算耗尽时不再发起新请求；正常路径与 5xx 三次重试不受影响。

飞书 HTTP 一律 mock，不发起真实请求；预算相关用例用假时钟推进，不做真实等待。
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.platform.notification import feishu_client, feishu_client_config

_TOKEN_URL_SUFFIX = "/auth/v3/tenant_access_token/internal"
_INVALID_TOKEN = {"code": 99991663, "msg": "invalid access token"}
_OK = {"code": 0, "data": {}}


class _FakeClock:
    """只实现被测模块用到的 ``time.monotonic()``；不动全局 time，避免干扰事件循环。"""

    def __init__(self, now: float = 1000.0) -> None:
        self.now = now

    def monotonic(self) -> float:
        return self.now


class _FakeGateway:
    """按 URL 分发：token 接口每次发新 token，消息接口按脚本顺序返回。

    ``cost`` 表示一次 HTTP 往返消耗的秒数，用于模拟「预算被耗掉」。
    """

    def __init__(
        self,
        send_script: list[tuple[int, dict[str, Any]]],
        *,
        clock: _FakeClock | None = None,
        cost: float = 0.0,
    ) -> None:
        self._send_script = send_script
        self._clock = clock
        self._cost = cost
        self.token_calls = 0
        self.send_calls = 0

    async def request(self, method: str, url: str) -> httpx.Response:
        request = httpx.Request(method, url)
        if url.endswith(_TOKEN_URL_SUFFIX):
            self.token_calls += 1
            response = httpx.Response(
                200,
                json={"code": 0, "tenant_access_token": f"t-{self.token_calls}", "expire": 7200},
                request=request,
            )
            self._advance()
            return response
        index = min(self.send_calls, len(self._send_script) - 1)
        self.send_calls += 1
        status, payload = self._send_script[index]
        response = httpx.Response(status, json=payload, request=request)
        self._advance()
        return response

    def _advance(self) -> None:
        if self._clock is not None:
            self._clock.now += self._cost


@pytest.fixture(autouse=True)
def _no_real_sleeping(monkeypatch: pytest.MonkeyPatch) -> None:
    """保留退避策略但去掉真实等待——延迟不是本测试的关注点。"""
    for module in (feishu_client, feishu_client_config):
        monkeypatch.setattr(module, "_RETRY_BACKOFF", (0, 0, 0))


@pytest.fixture(params=["platform", "config"], ids=["platform", "config"])
def module(request: pytest.FixtureRequest) -> Any:
    """被测模块本身（常量与 ``time`` 注入都作用在它上面）。"""
    return feishu_client if request.param == "platform" else feishu_client_config


@pytest.fixture
def client(module: Any) -> Any:
    return module.FeishuClient("app", "secret")


def _patch_http(
    monkeypatch: pytest.MonkeyPatch,
    gateway: _FakeGateway,
    *,
    timeouts: list[float] | None = None,
) -> None:
    async def fake_request(_self: httpx.AsyncClient, method: str, url: str, **_kwargs: Any) -> httpx.Response:
        if timeouts is not None:
            connect = _self.timeout.connect
            assert connect is not None  # 被测代码始终显式传 float
            timeouts.append(connect)
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


def test_call_budget_equals_single_request_upper_bound(module: Any) -> None:
    """预算必须等于单次 _request 的原有上界（3×30s + 1+2+4s），防止被改小或漂移。

    退避值写成字面量：``_no_real_sleeping`` 会把模块里的 ``_RETRY_BACKOFF`` 置 0，
    而 ``_CALL_BUDGET_SECONDS`` 在 import 期就已按源码里的 (1, 2, 4) 算出。
    """
    assert module._CALL_BUDGET_SECONDS == 97.0
    assert module._CALL_BUDGET_SECONDS == module._MAX_RETRIES * module._HTTP_TIMEOUT + (1 + 2 + 4)


async def test_happy_path_is_one_http_call(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """预算不得改变正常路径：取 token + 发送各一次，超时仍是 30s。"""
    gateway = _FakeGateway([(200, _OK)])
    timeouts: list[float] = []
    _patch_http(monkeypatch, gateway, timeouts=timeouts)

    result = await client.send_message("open_id", "ou_test", "text", '{"text":"hi"}')

    assert result["code"] == 0
    assert (gateway.token_calls, gateway.send_calls) == (1, 1)
    assert timeouts == [30.0, 30.0]


async def test_5xx_is_retried_three_times_then_raises(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """预算不得削弱 5xx 重试：预算充裕时仍是 3 次尝试。"""
    gateway = _FakeGateway([(500, {}), (500, {}), (500, {})])
    _patch_http(monkeypatch, gateway)

    with pytest.raises(httpx.HTTPStatusError):
        await client.send_message("open_id", "ou_test", "text", '{"text":"hi"}')

    assert gateway.token_calls == 1
    assert gateway.send_calls == 3


async def test_5xx_then_success(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """5xx 后重试成功：第二次即返回。"""
    gateway = _FakeGateway([(500, {}), (200, _OK)])
    _patch_http(monkeypatch, gateway)

    result = await client.send_message("open_id", "ou_test", "text", '{"text":"hi"}')

    assert result["code"] == 0
    assert gateway.send_calls == 2


async def test_self_heal_does_not_exceed_budget(client: Any, module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """核心回归：首次发送已耗掉预算时，自愈重发的取 token 不再发起外呼。"""
    clock = _FakeClock()
    monkeypatch.setattr(module, "time", clock)
    gateway = _FakeGateway([(200, _INVALID_TOKEN), (200, _OK)], clock=clock, cost=60.0)
    _patch_http(monkeypatch, gateway)

    with pytest.raises(httpx.TimeoutException):
        await client.send_message("open_id", "ou_test", "text", '{"text":"hi"}')

    # 取 token 60s + 首次发送 60s 已耗尽 97s 预算，重发的取 token 被预算拦住
    assert (gateway.token_calls, gateway.send_calls) == (1, 1)


async def test_retry_stops_when_budget_exhausted(client: Any, module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """预算耗尽时不再重试，且保留原始异常类型（不被替换成超时）。"""
    clock = _FakeClock()
    monkeypatch.setattr(module, "time", clock)
    client._tenant_access_token = "t-cached"
    client._token_expires_at = clock.now + 7200
    gateway = _FakeGateway([(500, {})], clock=clock, cost=100.0)
    _patch_http(monkeypatch, gateway)

    with pytest.raises(httpx.HTTPStatusError):
        await client.send_message("open_id", "ou_test", "text", '{"text":"hi"}')

    assert gateway.token_calls == 0
    assert gateway.send_calls == 1
