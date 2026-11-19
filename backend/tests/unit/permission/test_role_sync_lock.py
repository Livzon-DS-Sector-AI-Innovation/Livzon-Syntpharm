"""内置角色「手工接管」与「恢复默认」。

口径（2026-11-18 用户确认）：
- 系统管理员可编辑内置角色（模块负责人 / 模块管理员）的权限；
- 一旦手工编辑，`sync_locked=True`，启动同步不再改动该角色；
- 「恢复默认」把权限重建为注册表装配值并清掉接管标记；
- 系统管理员角色（super_admin）任何情况下都不可改。
"""

import uuid
from typing import Any, cast

import pytest

from app.core.exceptions import ForbiddenException
from app.platform.permission.models import Role
from app.platform.permission.registry import BUILTIN_ROLE_PERMISSIONS
from app.platform.permission.service import management
from app.platform.permission.service.delegation import ModuleScope, assert_can_edit_role


def _role(role_type: str, module_code: str | None = "quality", *, builtin: bool = True) -> Role:
    return Role(
        code=f"{module_code}:{role_type}" if module_code and role_type != "system" else "super_admin",
        name="测试角色",
        category="module" if module_code else "platform",
        role_type=role_type,
        module_code=module_code,
        is_builtin=builtin,
        is_superuser=role_type == "system",
    )


def _sysadmin() -> ModuleScope:
    return ModuleScope(user_id=uuid.uuid4(), is_system_admin=True, modules=frozenset(), owner_modules=frozenset())


def _head_scope() -> ModuleScope:
    return ModuleScope(
        user_id=uuid.uuid4(),
        is_system_admin=False,
        modules=frozenset({"quality"}),
        owner_modules=frozenset({"quality"}),
    )


def test_sysadmin_can_edit_builtin_role_content() -> None:
    """系统管理员编辑内置角色权限时显式声明 allow_builtin=True → 放行。"""
    assert_can_edit_role(_sysadmin(), _role("owner"), allow_builtin=True)
    assert_can_edit_role(_sysadmin(), _role("delegate"), allow_builtin=True)


def test_sysadmin_cannot_delete_builtin_role() -> None:
    """删除路径不传 allow_builtin → 内置角色仍不可删。"""
    with pytest.raises(ForbiddenException):
        assert_can_edit_role(_sysadmin(), _role("owner"))


def test_module_head_cannot_edit_builtin_even_with_flag() -> None:
    with pytest.raises(ForbiddenException):
        assert_can_edit_role(_head_scope(), _role("owner"), allow_builtin=True)


def test_super_admin_role_never_editable() -> None:
    with pytest.raises(ForbiddenException):
        assert_can_edit_role(_sysadmin(), _role("system", module_code=None), allow_builtin=True)


def test_job_role_still_scoped_by_module() -> None:
    job = _role("job", builtin=False)
    assert_can_edit_role(_head_scope(), job)
    other = ModuleScope(
        user_id=uuid.uuid4(), is_system_admin=False, modules=frozenset({"safety"}), owner_modules=frozenset()
    )
    with pytest.raises(ForbiddenException):
        assert_can_edit_role(other, job)


class _FakeSession:
    """只记录 add 的对象，用于验证恢复默认时的权限重建。"""

    def __init__(self) -> None:
        self.added: list[Any] = []
        self.executed: list[Any] = []

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def execute(self, stmt: Any) -> Any:
        self.executed.append(stmt)
        return _EmptyResult()


class _EmptyScalars:
    def all(self) -> list[Any]:
        return []


class _EmptyResult:
    def scalars(self) -> _EmptyScalars:
        return _EmptyScalars()


async def test_reset_role_to_default_restores_registry_codes() -> None:
    role = _role("owner")
    role.sync_locked = True
    db = _FakeSession()

    count = await management.reset_role_to_default(cast(Any, db), role)

    expected = BUILTIN_ROLE_PERMISSIONS["quality:owner"]
    added_codes = [obj.permission_code for obj in db.added]
    assert sorted(added_codes) == sorted(expected)
    assert count == len(expected)
    assert role.sync_locked is False


async def test_reset_role_to_default_rejects_non_builtin() -> None:
    job = _role("job", builtin=False)
    with pytest.raises(ForbiddenException):
        await management.reset_role_to_default(cast(Any, _FakeSession()), job)
