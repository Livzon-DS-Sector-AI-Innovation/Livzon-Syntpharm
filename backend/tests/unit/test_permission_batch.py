# mypy: ignore-errors
"""角色 / 授权的批量启停与批量删除。

产品口径（2026-10-22）：
- 逐条复用单条护栏，失败项不影响其他条目并返回原因；
- 内置角色不可改状态、不可删除；超管角色不可删除；
- 授权：不能改自己的、不能越级、不能移除最后一个超管授权；
- 状态已一致的按幂等处理（计入成功、不写审计）。
"""

import uuid
from typing import Any

import pytest

from app.platform.permission import api as permission_api
from app.platform.permission.api import batch_delete_grants, batch_delete_roles, batch_grant_status, batch_role_status
from app.platform.permission.models import Role, UserRoleGrant
from app.platform.permission.public_api import PermissionContext


class StubResult:
    def __init__(self, value: Any) -> None:
        self.value = value

    def scalar_one_or_none(self) -> Any:
        return self.value


class StubSession:
    def __init__(self, target_user: Any = None) -> None:
        self.target_user = target_user
        self.commits = 0
        self.flushes = 0

    async def execute(self, stmt: Any) -> StubResult:
        return StubResult(self.target_user)

    async def commit(self) -> None:
        self.commits += 1

    async def flush(self) -> None:
        self.flushes += 1


class StubRoleRepo:
    def __init__(self, roles: list[Role]) -> None:
        self.roles = {role.id: role for role in roles}
        self.deleted: list[uuid.UUID] = []

    async def get_role(self, db: Any, role_id: uuid.UUID) -> Role | None:
        return self.roles.get(role_id)

    async def soft_delete_role(self, db: Any, role: Role) -> None:
        self.deleted.append(role.id)
        role.is_deleted = True


class StubGrantRepo:
    def __init__(self, grants: list[UserRoleGrant]) -> None:
        self.grants = {grant.id: grant for grant in grants}

    async def get_grant(self, db: Any, grant_id: uuid.UUID) -> UserRoleGrant | None:
        return self.grants.get(grant_id)


def _role(*, name: str, status: str = "active", is_builtin: bool = False, is_superuser: bool = False) -> Role:
    role = Role(code=f"code_{uuid.uuid4().hex[:6]}", name=name, status=status)
    role.id = uuid.uuid4()
    role.is_builtin = is_builtin
    role.is_superuser = is_superuser
    return role


def _grant(*, user_id: uuid.UUID, status: str = "active") -> UserRoleGrant:
    grant = UserRoleGrant(user_id=user_id, role_id=uuid.uuid4(), scope_type="all", status=status)
    grant.id = uuid.uuid4()
    grant.version = 1
    grant.is_deleted = False
    return grant


def _ctx() -> PermissionContext:
    operator = type("U", (), {})()
    operator.id = uuid.uuid4()
    operator.name = "管理员"
    return PermissionContext(user=operator, permission_code="platform:role:manage", is_superuser=True)


def _patch(monkeypatch: pytest.MonkeyPatch, *, role_repo: Any = None, grant_repo: Any = None):
    audits: list[dict[str, Any]] = []
    evicted: list[Any] = []

    async def fake_audit(db: Any, **kwargs: Any) -> None:
        audits.append(kwargs)

    async def fake_evict_role(db: Any, role_id: Any) -> None:
        evicted.append(role_id)

    async def fake_evict_user(user_id: Any) -> None:
        evicted.append(user_id)

    monkeypatch.setattr(permission_api, "record_audit_log", fake_audit)
    monkeypatch.setattr(permission_api, "_evict_cache_for_role", fake_evict_role)
    monkeypatch.setattr(permission_api, "_evict_user_cache", fake_evict_user)

    async def fake_get_role(db: Any, role_id: Any) -> None:
        return None

    monkeypatch.setattr(permission_api, "guard_self_escalation", lambda actor_id, grant: None)
    monkeypatch.setattr(permission_api, "get_role", fake_get_role)

    if role_repo is not None:
        monkeypatch.setattr(permission_api, "RoleRepository", lambda: role_repo)
    if grant_repo is not None:
        monkeypatch.setattr(permission_api, "GrantRepository", lambda: grant_repo)

    audits_holder = {"audits": audits, "evicted": evicted}
    return audits_holder


# ── 角色 ──────────────────────────────────────────────────────────────


async def test_role_batch_status_updates_and_audits(monkeypatch: pytest.MonkeyPatch) -> None:
    role = _role(name="研发主管")
    repo = StubRoleRepo([role])
    holder = _patch(monkeypatch, role_repo=repo)
    session = StubSession()

    resp = await batch_role_status(
        permission_api.StatusBatchRequest(ids=[role.id], status="disabled"),
        ctx=_ctx(),
        db=session,
    )

    assert resp.data["succeeded"] == [str(role.id)]
    assert role.status == "disabled"
    assert len(holder["audits"]) == 1
    assert holder["audits"][0]["new_value"]["batch"] is True
    assert holder["evicted"] == [role.id]
    assert session.commits == 1


async def test_role_batch_status_skips_builtin(monkeypatch: pytest.MonkeyPatch) -> None:
    role = _role(name="超级管理员", is_builtin=True, is_superuser=True)
    repo = StubRoleRepo([role])
    holder = _patch(monkeypatch, role_repo=repo)

    resp = await batch_role_status(
        permission_api.StatusBatchRequest(ids=[role.id], status="disabled"),
        ctx=_ctx(),
        db=StubSession(),
    )

    assert resp.data["succeeded"] == []
    assert resp.data["failed"][0]["reason"] == "内置角色不可修改状态"
    assert role.status == "active"
    assert holder["audits"] == []


async def test_role_batch_status_same_status_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    role = _role(name="只读角色", status="active")
    repo = StubRoleRepo([role])
    holder = _patch(monkeypatch, role_repo=repo)

    resp = await batch_role_status(
        permission_api.StatusBatchRequest(ids=[role.id], status="active"),
        ctx=_ctx(),
        db=StubSession(),
    )

    assert resp.data["succeeded"] == [str(role.id)]
    assert holder["audits"] == []


async def test_role_batch_delete_protects_builtin_and_superuser(monkeypatch: pytest.MonkeyPatch) -> None:
    builtin = _role(name="内置角色", is_builtin=True)
    superuser = _role(name="超管角色", is_superuser=True)
    normal = _role(name="普通角色")
    repo = StubRoleRepo([builtin, superuser, normal])
    holder = _patch(monkeypatch, role_repo=repo)

    resp = await batch_delete_roles(
        permission_api.IdsBatchRequest(ids=[builtin.id, superuser.id, normal.id]),
        ctx=_ctx(),
        db=StubSession(),
    )

    assert resp.data["succeeded"] == [str(normal.id)]
    assert len(resp.data["failed"]) == 2
    assert repo.deleted == [normal.id]
    assert holder["audits"][0]["action"] == "role.delete"


# ── 授权 ──────────────────────────────────────────────────────────────


async def test_grant_batch_status_disables_and_evicts(monkeypatch: pytest.MonkeyPatch) -> None:
    target = type("U", (), {})()
    target.id = uuid.uuid4()
    grant = _grant(user_id=target.id)
    repo = StubGrantRepo([grant])
    holder = _patch(monkeypatch, grant_repo=repo)

    async def allow(*args: Any, **kwargs: Any) -> None:
        return None

    monkeypatch.setattr(permission_api, "guard_manage_target", allow)
    monkeypatch.setattr(permission_api, "guard_last_superadmin", allow)

    resp = await batch_grant_status(
        permission_api.StatusBatchRequest(ids=[grant.id], status="disabled"),
        ctx=_ctx(),
        db=StubSession(target_user=target),
    )

    assert resp.data["succeeded"] == [str(grant.id)]
    assert grant.status == "disabled"
    assert grant.version == 2
    assert holder["evicted"] == [target.id]


async def test_grant_batch_status_reports_last_superadmin(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.exceptions import ForbiddenException

    target = type("U", (), {})()
    target.id = uuid.uuid4()
    grant = _grant(user_id=target.id)
    repo = StubGrantRepo([grant])
    holder = _patch(monkeypatch, grant_repo=repo)

    async def allow(*args: Any, **kwargs: Any) -> None:
        return None

    async def deny_last(*args: Any, **kwargs: Any) -> None:
        raise ForbiddenException("不能移除最后一个超级管理员")

    monkeypatch.setattr(permission_api, "guard_manage_target", allow)
    monkeypatch.setattr(permission_api, "guard_last_superadmin", deny_last)

    resp = await batch_grant_status(
        permission_api.StatusBatchRequest(ids=[grant.id], status="disabled"),
        ctx=_ctx(),
        db=StubSession(target_user=target),
    )

    assert resp.data["succeeded"] == []
    assert resp.data["failed"][0]["reason"] == "不能移除最后一个超级管理员"
    assert grant.status == "active"
    assert holder["audits"] == []


async def test_grant_batch_delete_marks_deleted(monkeypatch: pytest.MonkeyPatch) -> None:
    target = type("U", (), {})()
    target.id = uuid.uuid4()
    grant = _grant(user_id=target.id)
    repo = StubGrantRepo([grant])
    holder = _patch(monkeypatch, grant_repo=repo)
    session = StubSession(target_user=target)

    async def allow(*args: Any, **kwargs: Any) -> None:
        return None

    monkeypatch.setattr(permission_api, "guard_manage_target", allow)
    monkeypatch.setattr(permission_api, "guard_last_superadmin", allow)

    resp = await batch_delete_grants(
        permission_api.IdsBatchRequest(ids=[grant.id]),
        ctx=_ctx(),
        db=session,
    )

    assert resp.data["succeeded"] == [str(grant.id)]
    assert grant.is_deleted is True
    assert holder["audits"][0]["action"] == "grant.delete"
    assert session.flushes == 1
