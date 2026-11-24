"""飞书网页应用免登（H5）：配置读取、开关关闭时拒绝、成功换取 token。"""

import uuid
from types import SimpleNamespace
from typing import Any, cast

import pytest
from starlette.requests import Request

from app.core.exceptions import NotFoundException
from app.platform.identity import api as identity_api
from app.platform.identity.models import User
from app.platform.identity.schemas import FeishuH5LoginRequest


class StubSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/identity/auth/h5/login",
            "headers": [],
            "client": ("10.0.0.8", 12345),
        }
    )


def _patch_settings(monkeypatch: pytest.MonkeyPatch, *, enabled: bool, app_id: str = "cli_test") -> None:
    platform_cfg = SimpleNamespace(h5_login_enabled=enabled, app_id=app_id)
    monkeypatch.setattr(
        identity_api,
        "get_settings",
        lambda: SimpleNamespace(feishu=SimpleNamespace(platform=platform_cfg)),
    )


async def test_h5_config_disabled_hides_app_id(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_settings(monkeypatch, enabled=False)

    result = await identity_api.feishu_h5_config()

    assert result.data.enabled is False
    assert result.data.app_id == ""


async def test_h5_config_enabled_returns_app_id(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_settings(monkeypatch, enabled=True)

    result = await identity_api.feishu_h5_config()

    assert result.data.enabled is True
    assert result.data.app_id == "cli_test"


async def test_h5_login_rejected_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_settings(monkeypatch, enabled=False)

    with pytest.raises(NotFoundException):
        await identity_api.feishu_h5_login(
            FeishuH5LoginRequest(code="c-1"), _request(), cast(Any, StubSession())
        )


async def test_h5_login_returns_token_and_records_success(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_settings(monkeypatch, enabled=True)

    user = User(name="张三", username="zhangsan")
    user.id = uuid.uuid4()
    user.auth_source = "feishu"
    # 真实仓库 flush 后列默认值才生效；替身显式补上，否则 UserResponse 校验失败
    user.must_change_password = False

    seen: dict[str, Any] = {}
    logs: list[dict[str, Any]] = []

    async def fake_handle(db: Any, code: str, *, preauth_code: bool = False) -> tuple[User, str]:
        seen["code"] = code
        seen["preauth_code"] = preauth_code
        return user, "jwt-token"

    class StubLogRepo:
        async def create(self, db: Any, **kwargs: Any) -> None:
            logs.append(kwargs)

    async def fake_record_session(token: str, record_user: User, ip: str | None, ua: str | None) -> None:
        seen["session_token"] = token

    monkeypatch.setattr("app.platform.identity.service.handle_oauth_callback", fake_handle)
    monkeypatch.setattr("app.platform.identity.repository.LoginLogRepository", StubLogRepo)
    monkeypatch.setattr(identity_api, "_record_login_session", fake_record_session)

    session = StubSession()
    result = await identity_api.feishu_h5_login(
        FeishuH5LoginRequest(code="c-1"), _request(), cast(Any, session)
    )

    assert result.data.access_token == "jwt-token"
    assert seen == {"code": "c-1", "preauth_code": True, "session_token": "jwt-token"}
    assert logs[-1]["login_type"] == "feishu_h5"
    assert logs[-1]["status"] == "success"
    assert session.commits == 1