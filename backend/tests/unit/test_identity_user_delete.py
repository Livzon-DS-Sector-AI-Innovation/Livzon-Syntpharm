# mypy: ignore-errors
"""删除账号：仅超级管理员 + 软删除保护规则。

产品口径（2026-10-21）：
- 只有超级管理员能删除账号（`platform:user:manage` 也授予普通账号管理员，不能只靠权限码）；
- 软删除（is_deleted + disabled），用户名继续被唯一约束占用；
- 删除时清空角色授权、吊销在线会话，并写审计。
"""

import uuid
from typing import Any

import pytest

from app.core.exceptions import ForbiddenException
from app.platform.identity import api as identity_api
from app.platform.identity.api import delete_user_management
from app.platform.identity.models import User
from app.platform.identity.repository import UserRepository
from app.platform.permission.public_api import PermissionContext


class StubSession:
    def __init__(self) -> None:
        self.commits = 0
        self.flushes = 0

    async def commit(self) -> None:
        self.commits += 1

    async def flush(self) -> None:
        self.flushes += 1


class StubRepo:
    """最小仓库替身：返回固定目标用户并记录删除调用。"""

    def __init__(self, user: User | None) -> None:
        self.user = user
        self.deleted: list[tuple[Any, Any]] = []

    async def get_by_id(self, session: Any, user_id: uuid.UUID) -> User | None:
        return self.user

    async def soft_delete_user(self, session: Any, user: User, *, operator_id: Any = None) -> User:
        self.deleted.append((user.id, operator_id))
        user.is_deleted = True
        user.status = "disabled"
        return user


def _make_user(*, username: str = "zhangsan", name: str = "张三") -> User:
    """构造未落库的 User：超管身份由授权表决定，不在 User 上，因此这里只造账号本身。"""
    user = User(name=name, username=username, status="active")
    user.id = uuid.uuid4()
    return user


def _ctx(operator: User) -> PermissionContext:
    return PermissionContext(user=operator, permission_code="platform:user:manage", is_superuser=True)


def _patch(monkeypatch: pytest.MonkeyPatch, *, repo: StubRepo, actor_is_superuser: bool, super_ids: list[Any]):
    """接管权限判定、审计、授权清理与会话吊销（删除端点内部为局部 import，patch 模块属性生效）。"""
    audits: list[dict[str, Any]] = []
    calls: dict[str, Any] = {"revoked_grants": 0, "revoked_sessions": 0, "grant_user": None, "session_user": None}

    async def fake_is_superuser(db: Any, user: User) -> bool:
        return actor_is_superuser

    async def fake_list_super_ids(db: Any) -> list[Any]:
        return super_ids

    async def fake_revoke_grants(db: Any, user_id: Any) -> int:
        calls["grant_user"] = user_id
        return 2

    async def fake_revoke_sessions(user_id: Any) -> int:
        calls["session_user"] = user_id
        return 3

    async def fake_audit(db: Any, **kwargs: Any) -> None:
        audits.append(kwargs)

    monkeypatch.setattr(identity_api, "UserRepository", lambda: repo)
    monkeypatch.setattr(identity_api, "record_audit_log", fake_audit)
    monkeypatch.setattr("app.platform.permission.public_api.user_is_superuser", fake_is_superuser)
    monkeypatch.setattr("app.platform.permission.public_api.list_superuser_user_ids", fake_list_super_ids)
    monkeypatch.setattr("app.platform.permission.public_api.revoke_all_user_grants", fake_revoke_grants)
    monkeypatch.setattr("app.platform.identity.session.revoke_all_user_sessions", fake_revoke_sessions)

    calls["audits"] = audits
    return calls


# ── 仓库层 ────────────────────────────────────────────────────────────


async def test_repository_soft_delete_marks_deleted_disables_and_records_operator() -> None:
    session = StubSession()
    operator_id = uuid.uuid4()
    user = _make_user()

    await UserRepository().soft_delete_user(session, user, operator_id=operator_id)

    assert user.is_deleted is True
    assert user.status == "disabled"
    assert user.updated_by == operator_id
    assert session.flushes == 1


# ── 端点：仅超级管理员 ────────────────────────────────────────────────


async def test_delete_rejects_non_superuser_even_with_manage_permission(monkeypatch: pytest.MonkeyPatch) -> None:
    """普通账号管理员持有 platform:user:manage，但不是超管 → 必须拒绝。"""
    operator = _make_user(username="manager")
    target = _make_user()
    repo = StubRepo(target)
    _patch(monkeypatch, repo=repo, actor_is_superuser=False, super_ids=[])

    with pytest.raises(ForbiddenException) as exc:
        await delete_user_management(target.id, ctx=_ctx(operator), db=StubSession())

    assert "只有超级管理员" in str(exc.value)
    assert repo.deleted == []


# ── 端点：正常删除 ────────────────────────────────────────────────────


async def test_delete_soft_deletes_and_clears_grants_and_sessions(monkeypatch: pytest.MonkeyPatch) -> None:
    operator = _make_user(username="root")
    target = _make_user()
    repo = StubRepo(target)
    session = StubSession()
    calls = _patch(monkeypatch, repo=repo, actor_is_superuser=True, super_ids=[operator.id])

    resp = await delete_user_management(target.id, ctx=_ctx(operator), db=session)

    assert repo.deleted == [(target.id, operator.id)]
    assert target.is_deleted is True
    assert target.status == "disabled"
    assert calls["grant_user"] == target.id
    assert calls["session_user"] == target.id
    assert resp.data.revoked_grants == 2
    assert resp.data.revoked_sessions == 3
    assert session.commits == 1
    assert calls["audits"][0]["action"] == "user.delete"
    assert calls["audits"][0]["old_value"]["username"] == "zhangsan"


# ── 端点：保护规则 ────────────────────────────────────────────────────


async def test_delete_rejects_self(monkeypatch: pytest.MonkeyPatch) -> None:
    operator = _make_user(username="root")
    repo = StubRepo(operator)
    _patch(monkeypatch, repo=repo, actor_is_superuser=True, super_ids=[operator.id, uuid.uuid4()])

    with pytest.raises(ForbiddenException) as exc:
        await delete_user_management(operator.id, ctx=_ctx(operator), db=StubSession())

    assert "当前登录账号" in str(exc.value)
    assert repo.deleted == []


async def test_delete_rejects_last_superuser(monkeypatch: pytest.MonkeyPatch) -> None:
    operator = _make_user(username="root")
    target = _make_user(username="root2")
    repo = StubRepo(target)
    _patch(monkeypatch, repo=repo, actor_is_superuser=True, super_ids=[target.id])

    with pytest.raises(ForbiddenException) as exc:
        await delete_user_management(target.id, ctx=_ctx(operator), db=StubSession())

    assert "最后一个超级管理员" in str(exc.value)
    assert repo.deleted == []


async def test_delete_rejects_system_admin_account(monkeypatch: pytest.MonkeyPatch) -> None:
    operator = _make_user(username="root")
    target = _make_user(username="SYSTEM_ADMIN")
    repo = StubRepo(target)
    _patch(monkeypatch, repo=repo, actor_is_superuser=True, super_ids=[operator.id])

    with pytest.raises(ForbiddenException) as exc:
        await delete_user_management(target.id, ctx=_ctx(operator), db=StubSession())

    assert "系统内置账号" in str(exc.value)
    assert repo.deleted == []
