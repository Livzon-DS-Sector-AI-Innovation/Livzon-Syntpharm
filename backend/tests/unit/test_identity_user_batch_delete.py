# mypy: ignore-errors
"""批量删除账号：逐条复用单条删除护栏与部分失败汇总。

产品口径（2026-11-18）：
- 仅超级管理员可批量删除（platform:user:manage 也授予普通账号管理员，不能只靠权限码）；
- 单次最多 100 个，自己 / 系统内置账号 / 最后一个超管 → 记入 failed，不影响其他条目；
- 成功条目：软删除 + 清空角色授权 + 审计（batch=true），提交后再吊销在线会话；
- Redis 吊销失败只降级，不回滚已完成的删除。
"""

import uuid
from typing import Any

import pytest

from app.core.exceptions import ForbiddenException
from app.platform.identity import api as identity_api
from app.platform.identity.api import batch_delete_users
from app.platform.identity.models import User
from app.platform.permission.public_api import PermissionContext


class StubSession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class StubRepo:
    """最小仓库替身：返回固定用户集合并记录删除调用。"""

    def __init__(self, users: list[User]) -> None:
        self.users = {u.id: u for u in users}
        self.deleted: list[tuple[Any, Any]] = []

    async def get_by_id(self, db: Any, user_id: uuid.UUID) -> User | None:
        return self.users.get(user_id)

    async def soft_delete_user(self, db: Any, user: User, *, operator_id: Any = None) -> User:
        self.deleted.append((user.id, operator_id))
        user.is_deleted = True
        user.status = "disabled"
        user.updated_by = operator_id
        return user


def _user(*, username: str, name: str | None = None, status: str = "active") -> User:
    user = User(name=name or username, username=username, status=status)
    user.id = uuid.uuid4()
    return user


def _ctx(operator: User) -> PermissionContext:
    return PermissionContext(user=operator, permission_code="platform:user:manage", is_superuser=True)


def _patch(
    monkeypatch: pytest.MonkeyPatch,
    *,
    repo: StubRepo,
    actor_is_superuser: bool = True,
    super_ids: list[Any] | None = None,
    session_error: bool = False,
) -> dict[str, Any]:
    """接管权限判定、审计、授权清理与会话吊销（端点内部为局部 import，patch 模块属性生效）。"""
    audits: list[dict[str, Any]] = []
    calls: dict[str, Any] = {"revoked_grants": [], "revoked_sessions": []}
    super_id_list = super_ids or []

    async def fake_is_superuser(db: Any, user: User) -> bool:
        return actor_is_superuser

    async def fake_list_super_ids(db: Any) -> list[Any]:
        return super_id_list

    async def fake_revoke_grants(db: Any, user_id: Any) -> int:
        calls["revoked_grants"].append(user_id)
        return 2

    async def fake_revoke_sessions(user_id: Any) -> int:
        calls["revoked_sessions"].append(user_id)
        if session_error:
            raise RuntimeError("redis down")
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


# ── 端点：仅超级管理员 ────────────────────────────────────────────────


async def test_batch_delete_rejects_non_superuser(monkeypatch: pytest.MonkeyPatch) -> None:
    operator = _user(username="manager")
    target = _user(username="zhangsan")
    repo = StubRepo([target])
    calls = _patch(monkeypatch, repo=repo, actor_is_superuser=False)

    with pytest.raises(ForbiddenException) as exc:
        await batch_delete_users(
            identity_api.UserBatchDeleteRequest(user_ids=[target.id]),
            ctx=_ctx(operator),
            db=StubSession(),
        )

    assert "只有超级管理员" in str(exc.value)
    assert repo.deleted == []
    assert calls["audits"] == []


# ── 端点：正常批量删除 ────────────────────────────────────────────────


async def test_batch_delete_soft_deletes_all_and_clears_grants_and_sessions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator = _user(username="root")
    a, b = _user(username="zhangsan"), _user(username="lisi")
    repo = StubRepo([a, b])
    session = StubSession()
    calls = _patch(monkeypatch, repo=repo, super_ids=[operator.id])

    resp = await batch_delete_users(
        identity_api.UserBatchDeleteRequest(user_ids=[a.id, b.id]),
        ctx=_ctx(operator),
        db=session,
    )

    assert resp.data["succeeded"] == [a.id, b.id]
    assert resp.data["failed"] == []
    assert repo.deleted == [(a.id, operator.id), (b.id, operator.id)]
    assert a.is_deleted and b.is_deleted
    assert a.status == "disabled" and b.status == "disabled"
    assert calls["revoked_grants"] == [a.id, b.id]
    assert calls["revoked_sessions"] == [a.id, b.id]
    assert session.commits == 1
    assert len(calls["audits"]) == 2
    assert all(item["action"] == "user.delete" for item in calls["audits"])
    assert all(item["new_value"]["batch"] is True for item in calls["audits"])


# ── 端点：保护规则（跳过并继续） ──────────────────────────────────────


async def test_batch_delete_skips_self_and_continues(monkeypatch: pytest.MonkeyPatch) -> None:
    operator = _user(username="root")
    other = _user(username="zhangsan")
    repo = StubRepo([operator, other])
    _patch(monkeypatch, repo=repo, super_ids=[operator.id, uuid.uuid4()])

    resp = await batch_delete_users(
        identity_api.UserBatchDeleteRequest(user_ids=[operator.id, other.id]),
        ctx=_ctx(operator),
        db=StubSession(),
    )

    assert resp.data["succeeded"] == [other.id]
    assert len(resp.data["failed"]) == 1
    assert resp.data["failed"][0]["reason"] == "不能删除当前登录账号"
    assert repo.deleted == [(other.id, operator.id)]


async def test_batch_delete_skips_system_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    operator = _user(username="root")
    system_admin = _user(username="system_admin")
    repo = StubRepo([system_admin])
    _patch(monkeypatch, repo=repo, super_ids=[operator.id])

    resp = await batch_delete_users(
        identity_api.UserBatchDeleteRequest(user_ids=[system_admin.id]),
        ctx=_ctx(operator),
        db=StubSession(),
    )

    assert resp.data["succeeded"] == []
    assert resp.data["failed"][0]["reason"] == "系统内置账号不允许删除"
    assert repo.deleted == []


async def test_batch_delete_skips_last_superuser(monkeypatch: pytest.MonkeyPatch) -> None:
    operator = _user(username="root")
    target = _user(username="root2")
    repo = StubRepo([target])
    _patch(monkeypatch, repo=repo, super_ids=[target.id])

    resp = await batch_delete_users(
        identity_api.UserBatchDeleteRequest(user_ids=[target.id]),
        ctx=_ctx(operator),
        db=StubSession(),
    )

    assert resp.data["succeeded"] == []
    assert "至少保留 2 名" in resp.data["failed"][0]["reason"]
    assert repo.deleted == []


async def test_batch_delete_reports_missing_user(monkeypatch: pytest.MonkeyPatch) -> None:
    operator = _user(username="root")
    repo = StubRepo([])
    _patch(monkeypatch, repo=repo, super_ids=[operator.id])
    missing = uuid.uuid4()

    resp = await batch_delete_users(
        identity_api.UserBatchDeleteRequest(user_ids=[missing]),
        ctx=_ctx(operator),
        db=StubSession(),
    )

    assert resp.data["succeeded"] == []
    assert resp.data["failed"][0]["reason"] == "账号不存在或已删除"


# ── 端点：吊销失败降级 ────────────────────────────────────────────────


async def test_batch_delete_tolerates_session_revoke_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    operator = _user(username="root")
    target = _user(username="zhangsan")
    repo = StubRepo([target])
    _patch(monkeypatch, repo=repo, super_ids=[operator.id], session_error=True)
    session = StubSession()

    resp = await batch_delete_users(
        identity_api.UserBatchDeleteRequest(user_ids=[target.id]),
        ctx=_ctx(operator),
        db=session,
    )

    assert resp.data["succeeded"] == [target.id]
    assert target.is_deleted is True
    assert session.commits == 1


# ── 请求模型 ──────────────────────────────────────────────────────────


async def test_batch_delete_rejects_too_many_ids() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        identity_api.UserBatchDeleteRequest(user_ids=[uuid.uuid4() for _ in range(101)])
