from typing import Any

from app.modules.hr.org_feishu import FeishuOrgDepartmentFetcher


class _FakeResponse:
    status_code = 200

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeClient:
    is_closed = False

    def __init__(self) -> None:
        self.calls = 0

    async def request(self, *args: object, **kwargs: object) -> _FakeResponse:
        self.calls += 1
        if self.calls == 1:
            return _FakeResponse({"code": 99991663, "msg": "invalid tenant access token"})
        return _FakeResponse({"code": 0, "data": {"ok": True}})


async def test_request_refreshes_cached_token_once_on_99991663() -> None:
    client = _FakeClient()
    fetcher = FeishuOrgDepartmentFetcher(
        app_id="cli_x",
        app_secret="secret",
        root_department_id="od-root",
        client=client,
    )  # type: ignore[arg-type]
    force_flags: list[bool] = []

    async def fake_token(*, force_refresh: bool = False) -> str:
        force_flags.append(force_refresh)
        return "t-1" if not force_refresh else "t-2"

    fetcher._token = fake_token  # type: ignore[method-assign]

    data = await fetcher._request("GET", "/test")

    assert data == {"ok": True}
    assert force_flags == [False, True]
    assert client.calls == 2
