# mypy: ignore-errors
"""新建本地用户：初始密码自动生成 + 强制首登改密。

产品口径（2026-10-22）：
- 新建表单不再让管理员填密码，后端随机生成 12 位；
- 明文只在创建响应里返回一次（不落库）；
- 新建账号一律 `must_change_password=True`，首次登录必须自行改密；
- 仍然兼容调用方显式传 `password`（按原规则校验强度，响应不含明文）。
"""

import uuid
from typing import Any

import pytest

from app.core.exceptions import BadRequestException
from app.platform.identity import api as identity_api
from app.platform.identity.api import create_user_management
from app.platform.identity.models import User
from app.platform.identity.service import PASSWORD_ALPHABET, verify_password
from app.platform.permission.public_api import PermissionContext


class StubSession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class StubRepo:
    def __init__(self, existing: User | None = None) -> None:
        self.existing = existing
        self.created: dict[str, Any] | None = None

    async def get_by_username(self, db: Any, username: str) -> User | None:
        return self.existing

    async def create(self, db: Any, **kwargs: Any) -> User:
        self.created = kwargs
        user = User(name=kwargs["name"], username=kwargs["username"], status=kwargs.get("status", "active"))
        user.id = uuid.uuid4()
        user.password_hash = kwargs["password_hash"]
        user.must_change_password = kwargs.get("must_change_password", False)
        # 真实仓库 flush 后列默认值会生效；替身要显式补上，否则 schema 校验因 None 报错
        user.auth_source = kwargs.get("auth_source", "feishu")
        return user


def _ctx() -> PermissionContext:
    operator = User(name="管理员", username="root")
    operator.id = uuid.uuid4()
    return PermissionContext(user=operator, permission_code="platform:user:manage", is_superuser=True)


def _patch(monkeypatch: pytest.MonkeyPatch, repo: StubRepo) -> list[dict[str, Any]]:
    audits: list[dict[str, Any]] = []

    async def fake_audit(db: Any, **kwargs: Any) -> None:
        audits.append(kwargs)

    monkeypatch.setattr(identity_api, "UserRepository", lambda: repo)
    monkeypatch.setattr(identity_api, "record_audit_log", fake_audit)
    return audits


def _payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"username": "zhangsan01", "name": "张三"}
    payload.update(overrides)
    return payload


async def test_create_without_password_generates_one_time_password(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = StubRepo()
    _patch(monkeypatch, repo)
    session = StubSession()

    resp = await create_user_management(identity_api.LocalUserCreate(**_payload()), ctx=_ctx(), db=session)

    generated = resp.data["initial_password"]
    assert generated
    assert len(generated) == 12
    assert set(generated) <= set(PASSWORD_ALPHABET)
    assert verify_password(generated, repo.created["password_hash"])
    assert session.commits == 1


async def test_create_forces_password_change_on_first_login(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = StubRepo()
    _patch(monkeypatch, repo)

    await create_user_management(identity_api.LocalUserCreate(**_payload()), ctx=_ctx(), db=StubSession())

    assert repo.created["must_change_password"] is True


async def test_create_audit_never_records_plaintext_password(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = StubRepo()
    audits = _patch(monkeypatch, repo)

    resp = await create_user_management(identity_api.LocalUserCreate(**_payload()), ctx=_ctx(), db=StubSession())

    generated = resp.data["initial_password"]
    dumped = str(audits[0])
    assert generated not in dumped
    assert audits[0]["new_value"]["password_generated"] is True


async def test_create_with_explicit_password_returns_no_plaintext(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = StubRepo()
    audits = _patch(monkeypatch, repo)

    resp = await create_user_management(
        identity_api.LocalUserCreate(**_payload(password="Manual#2026")),
        ctx=_ctx(),
        db=StubSession(),
    )

    assert resp.data["initial_password"] is None
    assert verify_password("Manual#2026", repo.created["password_hash"])
    assert audits[0]["new_value"]["password_generated"] is False


async def test_create_rejects_weak_explicit_password(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = StubRepo()
    _patch(monkeypatch, repo)

    with pytest.raises(BadRequestException):
        await create_user_management(
            identity_api.LocalUserCreate(**_payload(password="abcdefgh")),
            ctx=_ctx(),
            db=StubSession(),
        )

    assert repo.created is None
