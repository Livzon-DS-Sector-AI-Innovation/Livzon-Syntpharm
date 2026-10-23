# mypy: ignore-errors
"""批量启用 / 禁用账号：逐条保护规则与部分失败汇总。

产品口径（2026-10-22）：
- 单次最多 100 个，逐条复用单条更新的保护规则；
- 自己、system_admin、非超管操作超管 → 记入 failed，不影响其他条目；
- 状态已一致的条目按幂等处理（计入成功、不写审计）。
"""

import uuid
from typing import Any

import pytest

from app.core.exceptions import ForbiddenException
from app.platform.identity import api as identity_api
from app.platform.identity.api import batch_update_user_status
from app.platform.identity.models import User
from app.platform.permission.public_api import PermissionContext


class StubSession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class StubRepo:
    def __init__(self, users: list[User]) -> None:
        self.users = {u.id: u for u in users}

    async def get_by_id(self, db: Any, user_id: uuid.UUID) -> User | None:
        return self.users.get(user_id)


def _user(*, username: str, status: str = "active") -> User:
    user = User(name=username, username=username, status=status)
    user.id = uuid.uuid4()
    return user


def _ctx(operator: User) -> PermissionContext:
    return PermissionContext(user=operator, permission_code="platform:user:manage", is_superuser=True)


def _patch(monkeypatch: pytest.MonkeyPatch, repo: StubRepo, *, blocked_ids: set[Any] | None = None):
    """接管仓库、审计与越级校验；blocked_ids 模拟 guard_manage_target 拒绝的账号。"""
    audits: list[dict[str, Any]] = []
    blocked = blocked_ids or set()

    async def fake_audit(db: Any, **kwargs: Any) -> None:
        audits.append(kwargs)

    async def fake_guard(db: Any, *, actor: User, target: User, resource_label: str = "") -> None:
        if target.id in blocked:
            raise ForbiddenException("不能操作超级管理员账号")

    monkeypatch.setattr(identity_api, "UserRepository", lambda: repo)
    monkeypatch.setattr(identity_api, "record_audit_log", fake_audit)
    monkeypatch.setattr("app.platform.permission.public_api.guard_manage_target", fake_guard)
    return audits


async def test_batch_enable_updates_all_and_writes_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    operator = _user(username="manager")
    a, b = _user(username="zhangsan", status="disabled"), _user(username="lisi", status="disabled")
    repo = StubRepo([a, b])
    audits = _patch(monkeypatch, repo)
    session = StubSession()

    resp = await batch_update_user_status(
        identity_api.UserBatchStatusRequest(user_ids=[a.id, b.id], status="active"),
        ctx=_ctx(operator),
        db=session,
    )

    assert resp.data["succeeded"] == [a.id, b.id]
    assert resp.data["failed"] == []
    assert a.status == "active" and b.status == "active"
    assert len(audits) == 2
    assert all(item["new_value"]["batch"] is True for item in audits)
    assert session.commits == 1


async def test_batch_skips_self_and_continues(monkeypatch: pytest.MonkeyPatch) -> None:
    operator = _user(username="manager")
    other = _user(username="zhangsan", status="disabled")
    repo = StubRepo([operator, other])
    _patch(monkeypatch, repo)

    resp = await batch_update_user_status(
        identity_api.UserBatchStatusRequest(user_ids=[operator.id, other.id], status="active"),
        ctx=_ctx(operator),
        db=StubSession(),
    )

    assert resp.data["succeeded"] == [other.id]
    assert len(resp.data["failed"]) == 1
    assert resp.data["failed"][0]["reason"] == "不能修改自己的状态"
    assert operator.status == "active"


async def test_batch_reports_guard_rejection_for_superuser_target(monkeypatch: pytest.MonkeyPatch) -> None:
    operator = _user(username="manager")
    superuser = _user(username="root", status="disabled")
    repo = StubRepo([superuser])
    _patch(monkeypatch, repo, blocked_ids={superuser.id})

    resp = await batch_update_user_status(
        identity_api.UserBatchStatusRequest(user_ids=[superuser.id], status="active"),
        ctx=_ctx(operator),
        db=StubSession(),
    )

    assert resp.data["succeeded"] == []
    assert resp.data["failed"][0]["reason"] == "不能操作超级管理员账号"
    assert superuser.status == "disabled"


async def test_batch_rejects_system_admin_account(monkeypatch: pytest.MonkeyPatch) -> None:
    operator = _user(username="manager")
    system_admin = _user(username="system_admin", status="disabled")
    repo = StubRepo([system_admin])
    _patch(monkeypatch, repo)

    resp = await batch_update_user_status(
        identity_api.UserBatchStatusRequest(user_ids=[system_admin.id], status="active"),
        ctx=_ctx(operator),
        db=StubSession(),
    )

    assert resp.data["failed"][0]["reason"] == "系统内置账号不允许批量修改"
    assert system_admin.status == "disabled"


async def test_batch_reports_missing_user(monkeypatch: pytest.MonkeyPatch) -> None:
    operator = _user(username="manager")
    repo = StubRepo([])
    _patch(monkeypatch, repo)
    missing = uuid.uuid4()

    resp = await batch_update_user_status(
        identity_api.UserBatchStatusRequest(user_ids=[missing], status="active"),
        ctx=_ctx(operator),
        db=StubSession(),
    )

    assert resp.data["succeeded"] == []
    assert resp.data["failed"][0]["reason"] == "账号不存在或已删除"


async def test_batch_same_status_is_idempotent_and_not_audited(monkeypatch: pytest.MonkeyPatch) -> None:
    operator = _user(username="manager")
    already_active = _user(username="zhangsan", status="active")
    repo = StubRepo([already_active])
    audits = _patch(monkeypatch, repo)

    resp = await batch_update_user_status(
        identity_api.UserBatchStatusRequest(user_ids=[already_active.id], status="active"),
        ctx=_ctx(operator),
        db=StubSession(),
    )

    assert resp.data["succeeded"] == [already_active.id]
    assert audits == []


async def test_batch_rejects_too_many_ids() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        identity_api.UserBatchStatusRequest(user_ids=[uuid.uuid4() for _ in range(101)], status="active")
