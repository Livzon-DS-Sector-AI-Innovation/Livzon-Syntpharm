# mypy: ignore-errors
"""批量授权（多用户 × 多角色）：逐对复用单条护栏与幂等语义。

产品口径（2026-11-18）：
- 一次给多个用户授予多个角色，统一套用同一个数据范围；
- 逐对校验：不能给自己授权、不能越级、不能授出自己没有的角色；
- 已存在同用户同角色的有效授权按幂等处理（计入 succeeded、不重复插入、不写审计）；
- 失败项逐条返回原因，不影响其他组合。
"""

import uuid
from typing import Any

import pytest

from app.core.exceptions import ForbiddenException
from app.platform.permission import api as permission_api
from app.platform.permission.api import batch_create_grants
from app.platform.permission.models import Role
from app.platform.permission.public_api import PermissionContext
from app.platform.permission.service.delegation import ModuleScope


class StubResult:
    def __init__(self, *, scalar: Any = None, rows: list[Any] | None = None) -> None:
        self.scalar = scalar
        self.rows = rows or []

    def scalar_one_or_none(self) -> Any:
        return self.scalar

    def all(self) -> list[Any]:
        return self.rows


class StubSession:
    """按调用顺序返回目标用户行；用户查询用尽后返回「已有授权」结果集。"""

    def __init__(self, target_users: list[Any], existing_rows: list[Any] | None = None) -> None:
        self._targets = list(target_users)
        self._existing = existing_rows or []
        self.commits = 0

    async def execute(self, stmt: Any) -> StubResult:
        if self._targets:
            return StubResult(scalar=self._targets.pop(0))
        return StubResult(rows=self._existing)

    async def commit(self) -> None:
        self.commits += 1


class StubGrantRepo:
    def __init__(self) -> None:
        self.created: list[tuple[Any, Any]] = []

    async def create_grant(
        self,
        db: Any,
        *,
        user_id: Any,
        role_id: Any,
        scope_type: str,
        scope_dept_codes: list[str] | None,
        granted_by: Any,
    ) -> Any:
        self.created.append((user_id, role_id))
        grant = type("G", (), {})()
        grant.id = uuid.uuid4()
        grant.user_id = user_id
        grant.role_id = role_id
        return grant


def _user(*, name: str = "张三") -> Any:
    user = type("U", (), {})()
    user.id = uuid.uuid4()
    user.name = name
    user.username = name
    user.is_deleted = False
    return user


def _role(*, name: str, code: str | None = None) -> Role:
    role = Role(code=code or f"code_{uuid.uuid4().hex[:6]}", name=name, status="active")
    role.id = uuid.uuid4()
    role.is_superuser = False
    return role


def _ctx(operator: Any) -> PermissionContext:
    return PermissionContext(user=operator, permission_code="platform:grant:manage", is_superuser=True)


def _patch(
    monkeypatch: pytest.MonkeyPatch,
    *,
    roles: list[Role],
    resolve_map: dict[Any, Any],
    grant_repo: StubGrantRepo | None = None,
    blocked_users: set[Any] | None = None,
    forbidden_roles: set[Any] | None = None,
    scope: ModuleScope | None = None,
):
    """接管角色查询 / 人员映射 / 护栏 / 审计 / 缓存失效。"""
    audits: list[dict[str, Any]] = []
    evicted: list[Any] = []
    repo = grant_repo or StubGrantRepo()
    role_map = {role.id: role for role in roles}
    blocked = blocked_users or set()
    forbidden = forbidden_roles or set()
    the_scope = scope or ModuleScope(
        user_id=uuid.uuid4(),
        is_system_admin=True,
        modules=frozenset(),
        owner_modules=frozenset(),
    )

    async def fake_get_role(db: Any, role_id: Any) -> Role | None:
        return role_map.get(role_id)

    async def fake_resolve(db: Any, person_id: Any) -> Any:
        return resolve_map.get(person_id)

    async def fake_resolve_scope(db: Any, user: Any) -> ModuleScope:
        return the_scope

    async def fake_guard_role(db: Any, *, actor: Any, role: Role) -> None:
        if role.id in forbidden:
            raise ForbiddenException("无权授予该角色")

    async def fake_guard_target(db: Any, *, actor: Any, target: Any, resource_label: str = "") -> None:
        if target.id in blocked:
            raise ForbiddenException("不能操作权限不低于你的授权")

    async def allow_scope(*args: Any, **kwargs: Any) -> None:
        return None

    async def fake_audit(db: Any, **kwargs: Any) -> None:
        audits.append(kwargs)

    async def fake_evict(user_id: Any) -> None:
        evicted.append(user_id)

    monkeypatch.setattr(permission_api, "get_role", fake_get_role)
    monkeypatch.setattr(permission_api, "GrantRepository", lambda: repo)
    monkeypatch.setattr(permission_api, "assert_actor_can_grant_role", fake_guard_role)
    monkeypatch.setattr(permission_api, "assert_actor_can_grant_scope", allow_scope)
    monkeypatch.setattr(permission_api, "guard_manage_target", fake_guard_target)
    monkeypatch.setattr(permission_api, "resolve_module_scope", fake_resolve_scope)
    monkeypatch.setattr(permission_api, "record_audit_log", fake_audit)
    monkeypatch.setattr(permission_api, "_evict_user_cache", fake_evict)
    monkeypatch.setattr("app.platform.identity.public_api.resolve_person_user_id", fake_resolve)

    return {"audits": audits, "evicted": evicted, "repo": repo}


# ── 正常批量授权 ──────────────────────────────────────────────────────


async def test_batch_create_cross_product_and_audits(monkeypatch: pytest.MonkeyPatch) -> None:
    operator = _user(name="root")
    u1, u2 = _user(name="张三"), _user(name="李四")
    r1, r2 = _role(name="质量管理员"), _role(name="车间主管")
    holder = _patch(
        monkeypatch,
        roles=[r1, r2],
        resolve_map={u1.id: u1.id, u2.id: u2.id},
    )
    session = StubSession([u1, u2])

    resp = await batch_create_grants(
        permission_api.GrantBatchCreate(user_ids=[u1.id, u2.id], role_ids=[r1.id, r2.id]),
        ctx=_ctx(operator),
        db=session,
    )

    assert len(resp.data["succeeded"]) == 4
    assert resp.data["failed"] == []
    assert holder["repo"].created == [
        (u1.id, r1.id),
        (u1.id, r2.id),
        (u2.id, r1.id),
        (u2.id, r2.id),
    ]
    assert len(holder["audits"]) == 4
    assert all(item["new_value"]["batch"] is True for item in holder["audits"])
    assert all(item["action"] == "grant.create" for item in holder["audits"])
    assert set(holder["evicted"]) == {u1.id, u2.id}
    assert session.commits == 1


# ── 护栏 ──────────────────────────────────────────────────────────────


async def test_batch_create_skips_self_and_creates_for_others(monkeypatch: pytest.MonkeyPatch) -> None:
    operator = _user(name="root")
    other = _user(name="张三")
    role = _role(name="质量管理员")
    holder = _patch(
        monkeypatch,
        roles=[role],
        resolve_map={operator.id: operator.id, other.id: other.id},
    )
    session = StubSession([other])

    resp = await batch_create_grants(
        permission_api.GrantBatchCreate(user_ids=[operator.id, other.id], role_ids=[role.id]),
        ctx=_ctx(operator),
        db=session,
    )

    assert len(resp.data["succeeded"]) == 1
    assert len(resp.data["failed"]) == 1
    assert resp.data["failed"][0]["reason"] == "不能给自己授权"
    assert holder["repo"].created == [(other.id, role.id)]


async def test_batch_create_reports_blocked_target(monkeypatch: pytest.MonkeyPatch) -> None:
    operator = _user(name="root")
    target = _user(name="张三")
    role = _role(name="质量管理员")
    holder = _patch(
        monkeypatch,
        roles=[role],
        resolve_map={target.id: target.id},
        blocked_users={target.id},
    )

    resp = await batch_create_grants(
        permission_api.GrantBatchCreate(user_ids=[target.id], role_ids=[role.id]),
        ctx=_ctx(operator),
        db=StubSession([target]),
    )

    assert resp.data["succeeded"] == []
    assert resp.data["failed"][0]["reason"] == "不能操作权限不低于你的授权"
    assert holder["repo"].created == []


async def test_batch_create_reports_forbidden_role_once(monkeypatch: pytest.MonkeyPatch) -> None:
    operator = _user(name="root")
    u1, u2 = _user(name="张三"), _user(name="李四")
    role = _role(name="质量管理员")
    holder = _patch(
        monkeypatch,
        roles=[role],
        resolve_map={u1.id: u1.id, u2.id: u2.id},
        forbidden_roles={role.id},
    )
    session = StubSession([u1, u2])

    resp = await batch_create_grants(
        permission_api.GrantBatchCreate(user_ids=[u1.id, u2.id], role_ids=[role.id]),
        ctx=_ctx(operator),
        db=session,
    )

    assert resp.data["succeeded"] == []
    assert len(resp.data["failed"]) == 1
    assert resp.data["failed"][0]["label"] == "质量管理员"
    assert resp.data["failed"][0]["reason"] == "无权授予该角色"
    assert holder["repo"].created == []


async def test_batch_create_reports_unresolvable_person(monkeypatch: pytest.MonkeyPatch) -> None:
    operator = _user(name="root")
    missing = uuid.uuid4()
    role = _role(name="质量管理员")
    holder = _patch(monkeypatch, roles=[role], resolve_map={})

    resp = await batch_create_grants(
        permission_api.GrantBatchCreate(user_ids=[missing], role_ids=[role.id]),
        ctx=_ctx(operator),
        db=StubSession([]),
    )

    assert resp.data["succeeded"] == []
    assert resp.data["failed"][0]["reason"] == "用户不存在"
    assert holder["repo"].created == []


# ── 幂等：已拥有组合不重复插入 ────────────────────────────────────────


async def test_batch_create_skips_existing_grant_without_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    operator = _user(name="root")
    target = _user(name="张三")
    role = _role(name="质量管理员")
    existing_id = uuid.uuid4()
    holder = _patch(monkeypatch, roles=[role], resolve_map={target.id: target.id})
    session = StubSession([target], existing_rows=[(existing_id, target.id, role.id)])

    resp = await batch_create_grants(
        permission_api.GrantBatchCreate(user_ids=[target.id], role_ids=[role.id]),
        ctx=_ctx(operator),
        db=session,
    )

    assert resp.data["succeeded"] == [str(existing_id)]
    assert resp.data["failed"] == []
    assert holder["repo"].created == []
    assert holder["audits"] == []
    assert holder["evicted"] == []


# ── 请求模型 ──────────────────────────────────────────────────────────


async def test_batch_create_rejects_too_many_users() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        permission_api.GrantBatchCreate(user_ids=[uuid.uuid4() for _ in range(101)], role_ids=[uuid.uuid4()])


async def test_batch_create_rejects_too_many_roles() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        permission_api.GrantBatchCreate(user_ids=[uuid.uuid4()], role_ids=[uuid.uuid4() for _ in range(21)])


# ── 模块代表：只有本模块负责人可指派（TC-014）────────────────────────


def _delegate_role(module_code: str = "quality") -> Role:
    role = Role(
        code=f"{module_code}:delegate",
        name=f"{module_code}代表",
        status="active",
        role_type="delegate",
        module_code=module_code,
        is_builtin=True,
    )
    role.id = uuid.uuid4()
    role.is_superuser = False
    return role


async def test_batch_create_rejects_delegate_for_superadmin(monkeypatch: pytest.MonkeyPatch) -> None:
    operator = _user(name="root")
    target = _user(name="张三")
    role = _delegate_role("quality")
    holder = _patch(monkeypatch, roles=[role], resolve_map={target.id: target.id})

    resp = await batch_create_grants(
        permission_api.GrantBatchCreate(user_ids=[target.id], role_ids=[role.id]),
        ctx=_ctx(operator),
        db=StubSession([target]),
    )

    assert resp.data["succeeded"] == []
    assert len(resp.data["failed"]) == 1
    assert "只有本模块负责人可以指派或移除模块代表" in resp.data["failed"][0]["reason"]
    assert holder["repo"].created == []


async def test_batch_create_allows_delegate_for_own_module_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    operator = _user(name="quality-owner")
    target = _user(name="张三")
    role = _delegate_role("quality")
    scope = ModuleScope(
        user_id=operator.id,
        is_system_admin=False,
        modules=frozenset({"quality"}),
        owner_modules=frozenset({"quality"}),
    )
    holder = _patch(monkeypatch, roles=[role], resolve_map={target.id: target.id}, scope=scope)

    resp = await batch_create_grants(
        permission_api.GrantBatchCreate(user_ids=[target.id], role_ids=[role.id]),
        ctx=_ctx(operator),
        db=StubSession([target]),
    )

    assert resp.data["failed"] == []
    assert holder["repo"].created == [(target.id, role.id)]


async def test_batch_create_rejects_delegate_for_other_module_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    operator = _user(name="safety-owner")
    target = _user(name="张三")
    role = _delegate_role("quality")
    scope = ModuleScope(
        user_id=operator.id,
        is_system_admin=False,
        modules=frozenset({"safety"}),
        owner_modules=frozenset({"safety"}),
    )
    holder = _patch(monkeypatch, roles=[role], resolve_map={target.id: target.id}, scope=scope)

    resp = await batch_create_grants(
        permission_api.GrantBatchCreate(user_ids=[target.id], role_ids=[role.id]),
        ctx=_ctx(operator),
        db=StubSession([target]),
    )

    assert resp.data["succeeded"] == []
    assert "只有本模块负责人可以指派或移除模块代表" in resp.data["failed"][0]["reason"]
    assert holder["repo"].created == []
