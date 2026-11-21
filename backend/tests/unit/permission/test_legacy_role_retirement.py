"""历史内置角色（head / manager）退役：启动同步 + 迁移 SQL 守卫。

口径（2026-11-19）：
- 只退役 `is_builtin` 的历史角色，保留人工创建的岗位角色；
- 角色与其 active 授权一起置 disabled，并驱逐受影响用户的权限缓存；
- 迁移 0217 复用同一判据，LIKE 后缀必须走绑定参数（否则 sa.text 会把 `%:head`
  里的 `head` 登记成 bindparam）。
"""

import importlib.util
import pathlib
import uuid
from typing import Any, cast

import pytest
from sqlalchemy import Select, Update
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.permission.constants import RETIRED_ROLE_TYPES, ROLE_TYPES
from app.platform.permission.models import GRANT_ACTIVE, GRANT_DISABLED, Role
from app.platform.permission.repository import GrantRepository
from app.platform.permission.service import management

_MIGRATION_PATH = (
    pathlib.Path(__file__).resolve().parents[3] / "alembic" / "versions" / "0217_permission_role_owner_delegate.py"
)


def _load_migration() -> Any:
    spec = importlib.util.spec_from_file_location("migration_0203", _MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _ScalarsResult:
    def __init__(self, roles: list[Role]) -> None:
        self._roles = roles

    def scalars(self) -> "_ScalarsResult":
        return self

    def all(self) -> list[Role]:
        return self._roles


class _UpdateResult:
    rowcount = 1


def _matches_retired_predicate(role: Role) -> bool:
    """与 `_retire_legacy_role_types` / 迁移 0203 的判据保持一致（仅用于假会话）。"""
    if not role.is_builtin or role.is_deleted or role.status != GRANT_ACTIVE:
        return False
    return role.role_type in RETIRED_ROLE_TYPES or role.code.endswith(":head") or role.code.endswith(":manager")


class _FakeSession:
    """按语句类型分发：Select 返回预置角色，Update 记录到 `updates`。"""

    def __init__(self, roles: list[Role]) -> None:
        self._roles = roles
        self.updates: list[Any] = []
        self.events: list[str] = []

    async def execute(self, stmt: Any) -> Any:
        if isinstance(stmt, Select):
            return _ScalarsResult([role for role in self._roles if _matches_retired_predicate(role)])
        assert isinstance(stmt, Update)
        self.updates.append(stmt)
        self.events.append("update")
        return _UpdateResult()


def _builtin_role(
    code: str,
    role_type: str,
    *,
    module_code: str = "quality",
    is_builtin: bool = True,
    status: str = GRANT_ACTIVE,
    is_deleted: bool = False,
) -> Role:
    role = Role(
        code=code,
        name=code,
        category="module",
        role_type=role_type,
        module_code=module_code,
        is_builtin=is_builtin,
        status=status,
        is_deleted=is_deleted,
    )
    role.id = uuid.uuid4()
    return role


def test_retired_role_types_do_not_overlap_selectable_types() -> None:
    assert RETIRED_ROLE_TYPES == {"head", "manager"}
    assert not (RETIRED_ROLE_TYPES & ROLE_TYPES)


async def test_legacy_roles_are_disabled_with_grants_and_cache_evicted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    head = _builtin_role("quality:head", "head")
    manager = _builtin_role("quality:manager", "manager")
    session = _FakeSession([head, manager])
    test_user_id = uuid.UUID(int=1)

    async def fake_user_ids(_db: AsyncSession, role_id: uuid.UUID) -> list[uuid.UUID]:
        session.events.append(f"list:{role_id}")
        return [test_user_id]

    async def fake_evict(user_id: uuid.UUID) -> None:
        session.events.append(f"evict:{user_id}")

    monkeypatch.setattr(GrantRepository, "list_active_user_ids_by_role", staticmethod(fake_user_ids))
    monkeypatch.setattr(management, "evict_user_permission_cache", fake_evict)

    count = await management._retire_legacy_role_types(cast(Any, session))

    assert count == 2
    assert head.status == GRANT_DISABLED
    assert manager.status == GRANT_DISABLED
    assert len(session.updates) == 2
    # 先取 user_ids、再停授权、最后驱逐缓存（顺序写反会导致驱逐空集）
    assert session.events == [
        f"list:{head.id}",
        "update",
        f"evict:{test_user_id}",
        f"list:{manager.id}",
        "update",
        f"evict:{test_user_id}",
    ]


async def test_code_suffix_union_catches_dirty_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    dirty = _builtin_role("quality:head", "job")
    session = _FakeSession([dirty])

    async def fake_user_ids(_db: AsyncSession, _role_id: uuid.UUID) -> list[uuid.UUID]:
        return []

    async def fake_evict(_user_id: uuid.UUID) -> None:
        return None

    monkeypatch.setattr(GrantRepository, "list_active_user_ids_by_role", staticmethod(fake_user_ids))
    monkeypatch.setattr(management, "evict_user_permission_cache", fake_evict)

    count = await management._retire_legacy_role_types(cast(Any, session))

    assert count == 1
    assert dirty.status == GRANT_DISABLED


async def test_human_roles_and_new_builtin_roles_are_untouched(monkeypatch: pytest.MonkeyPatch) -> None:
    human = _builtin_role("quality:head", "job", is_builtin=False)
    owner = _builtin_role("quality:owner", "owner")
    delegate = _builtin_role("quality:delegate", "delegate")
    job = _builtin_role("quality:role-001", "job")
    session = _FakeSession([human, owner, delegate, job])

    async def fake_user_ids(_db: AsyncSession, _role_id: uuid.UUID) -> list[uuid.UUID]:
        return []

    async def fake_evict(_user_id: uuid.UUID) -> None:
        return None

    monkeypatch.setattr(GrantRepository, "list_active_user_ids_by_role", staticmethod(fake_user_ids))
    monkeypatch.setattr(management, "evict_user_permission_cache", fake_evict)

    count = await management._retire_legacy_role_types(cast(Any, session))

    assert count == 0
    assert human.status == GRANT_ACTIVE
    assert owner.status == GRANT_ACTIVE
    assert delegate.status == GRANT_ACTIVE
    assert job.status == GRANT_ACTIVE
    assert session.updates == []


async def test_retire_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    head = _builtin_role("quality:head", "head")
    session = _FakeSession([head])

    async def fake_user_ids(_db: AsyncSession, _role_id: uuid.UUID) -> list[uuid.UUID]:
        return []

    async def fake_evict(_user_id: uuid.UUID) -> None:
        return None

    monkeypatch.setattr(GrantRepository, "list_active_user_ids_by_role", staticmethod(fake_user_ids))
    monkeypatch.setattr(management, "evict_user_permission_cache", fake_evict)

    first = await management._retire_legacy_role_types(cast(Any, session))
    second = await management._retire_legacy_role_types(cast(Any, session))

    assert first == 1
    assert second == 0
    assert len(session.updates) == 1


def test_migration_0203_sql_uses_bound_suffixes() -> None:
    """迁移 SQL 文本不得出现裸 LIKE 字面量，避免被 sa.text 当成 bindparam。"""
    migration = _load_migration()
    expected = {"active", "head_suffix", "manager_suffix"}

    statements = [
        (migration.retired_roles_stmt(), expected),
        (migration.disable_grants_stmt(), expected | {"disabled"}),
        (migration.disable_roles_stmt(), expected | {"disabled"}),
    ]
    for stmt, keys in statements:
        compiled = stmt.compile(dialect=postgresql.dialect())
        assert set(compiled.params) == keys
        assert compiled.params["head_suffix"] == "%:head"
        assert compiled.params["manager_suffix"] == "%:manager"
        text = str(compiled)
        assert "%(head_suffix)s" in text
        assert "%(manager_suffix)s" in text
        assert "%(head)s" not in text
        assert "%(manager)s" not in text
        assert "role_type IN ('head', 'manager')" in text
