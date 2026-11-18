"""委派式权限管理守卫（R2–R9）的纯判定单元测试。

覆盖口径（与 Issue #221 的验收一致，测外部行为）：
- 岗位角色编码必须是两段、带本模块前缀、非保留字；
- 岗位角色只能含本模块业务码，不能含模块管理入口码；
- 负责人 / 管理人这两个内置角色只有系统管理员能动；
- 跨模块操作一律拒绝（403 语义），不是返回空；
- 不能给自己授权；
- 同一人同一角色不允许重复活跃授权。
"""

import uuid
from typing import Any, cast

import pytest

from app.core.exceptions import ForbiddenException
from app.platform.permission.models import Role
from app.platform.permission.service.delegation import (
    ModuleScope,
    assert_can_create_role,
    assert_can_edit_role,
    assert_job_role_permissions,
    assert_module_manageable,
    assert_no_duplicate_grant,
    assert_not_self,
    assert_role_code_valid,
    assert_target_role_operable,
)


def _role(code: str, role_type: str, module_code: str | None = None, *, builtin: bool = True) -> Role:
    return Role(
        code=code,
        name=code,
        category="module" if module_code else "platform",
        role_type=role_type,
        module_code=module_code,
        is_builtin=builtin,
    )


def _scope(*modules: str, is_system_admin: bool = False, heads: tuple[str, ...] = ()) -> ModuleScope:
    return ModuleScope(
        user_id=uuid.uuid4(),
        is_system_admin=is_system_admin,
        modules=frozenset(modules),
        head_modules=frozenset(heads),
    )


# ── 角色编码 ──────────────────────────────────────────────────────


def test_role_code_accepts_two_segments_with_module_prefix() -> None:
    assert_role_code_valid("quality", "quality:deviation-reviewer")


@pytest.mark.parametrize(
    "code",
    [
        "quality",  # 只有一段
        "quality:deviation:reviewer",  # 三段，与权限码形态混淆
        "safety:hazard-reader",  # 跨模块
        "quality:head",  # 保留字
        "quality:manager",  # 保留字
    ],
)
def test_role_code_rejects_invalid_forms(code: str) -> None:
    with pytest.raises(ForbiddenException):
        assert_role_code_valid("quality", code)


# ── 岗位角色权限载荷 ──────────────────────────────────────────────


def test_job_role_permissions_accept_module_codes() -> None:
    assert_job_role_permissions("quality", ["quality:deviation:read", "quality:deviation:create"])


def test_job_role_permissions_reject_admin_entry_code() -> None:
    with pytest.raises(ForbiddenException):
        assert_job_role_permissions("quality", ["quality:admin:read"])


def test_job_role_permissions_reject_cross_module_code() -> None:
    with pytest.raises(ForbiddenException):
        assert_job_role_permissions("quality", ["safety:hazard:read"])


# ── 模块作用域 ────────────────────────────────────────────────────


def test_module_scope_allows_only_own_modules() -> None:
    scope = _scope("quality")
    assert_module_manageable(scope, "quality")
    with pytest.raises(ForbiddenException):
        assert_module_manageable(scope, "safety")
    with pytest.raises(ForbiddenException):
        assert_module_manageable(scope, None)


def test_system_admin_manages_every_module() -> None:
    scope = _scope(is_system_admin=True)
    for code in ("quality", "safety", None):
        assert_module_manageable(scope, code)


# ── 内置管理角色仅系统管理员可动（R2）──────────────────────────────


@pytest.mark.parametrize(
    ("code", "role_type"),
    [("quality:head", "head"), ("quality:manager", "manager"), ("super_admin", "system")],
)
def test_manager_cannot_touch_builtin_admin_roles(code: str, role_type: str) -> None:
    """模块管理人（非负责人）不能任命管理人，也不能动负责人/系统管理员角色。"""
    scope = _scope("quality")
    with pytest.raises(ForbiddenException):
        assert_target_role_operable(scope, _role(code, role_type, "quality" if role_type != "system" else None))


def test_head_can_assign_module_manager() -> None:
    """模块内只有负责人能指定模块管理人。"""
    assert_target_role_operable(_scope("quality", heads=("quality",)), _role("quality:manager", "manager", "quality"))


def test_head_cannot_touch_fellow_head() -> None:
    with pytest.raises(ForbiddenException):
        assert_target_role_operable(_scope("quality", heads=("quality",)), _role("quality:head", "head", "quality"))


def test_head_of_other_module_cannot_assign_manager() -> None:
    scope = _scope("quality", heads=("safety",))
    with pytest.raises(ForbiddenException):
        assert_target_role_operable(scope, _role("quality:manager", "manager", "quality"))


def test_system_admin_can_touch_builtin_admin_roles() -> None:
    scope = _scope(is_system_admin=True)
    assert_target_role_operable(scope, _role("quality:head", "head", "quality"))
    assert_target_role_operable(scope, _role("quality:manager", "manager", "quality"))


def test_non_admin_can_touch_job_roles() -> None:
    assert_target_role_operable(_scope("quality"), _role("quality:viewer", "job", "quality"))


# ── 角色编辑/删除准入 ─────────────────────────────────────────────


def test_builtin_role_cannot_be_edited_even_by_system_admin() -> None:
    with pytest.raises(ForbiddenException):
        assert_can_edit_role(_scope(is_system_admin=True), _role("quality:head", "head", "quality"))


def test_job_role_edit_requires_module_scope() -> None:
    job = _role("quality:viewer", "job", "quality", builtin=False)
    assert_can_edit_role(_scope("quality"), job)
    with pytest.raises(ForbiddenException):
        assert_can_edit_role(_scope("safety"), job)


# ── 新建角色准入 ──────────────────────────────────────────────────


def test_create_role_requires_scope_and_valid_payload() -> None:
    scope = _scope("quality")
    assert_can_create_role(scope, "quality", "quality:viewer", ["quality:deviation:read"])

    with pytest.raises(ForbiddenException):
        assert_can_create_role(scope, "safety", "safety:viewer", ["safety:hazard:read"])


def test_create_role_rejects_admin_entry_permission() -> None:
    with pytest.raises(ForbiddenException):
        assert_can_create_role(_scope("quality"), "quality", "quality:viewer", ["quality:admin:read"])


def test_system_admin_can_create_global_role_without_module() -> None:
    assert_can_create_role(_scope(is_system_admin=True), None, "global-role", [])


# ── 自授权 ────────────────────────────────────────────────────────


def test_cannot_grant_to_self() -> None:
    actor_id = uuid.uuid4()
    with pytest.raises(ForbiddenException):
        assert_not_self(actor_id, actor_id)
    assert_not_self(actor_id, uuid.uuid4())


# ── 重复授权（R9）─────────────────────────────────────────────────


class _EmptyResult:
    def scalar_one_or_none(self):
        return None


class _HitResult:
    def scalar_one_or_none(self):
        return uuid.uuid4()


class _FakeSession:
    def __init__(self, result):
        self._result = result

    async def execute(self, *_args, **_kwargs):
        return self._result


async def test_duplicate_grant_allowed_when_absent() -> None:
    await assert_no_duplicate_grant(cast(Any, _FakeSession(_EmptyResult())), uuid.uuid4(), uuid.uuid4())


async def test_duplicate_grant_rejected_when_present() -> None:
    with pytest.raises(ForbiddenException):
        await assert_no_duplicate_grant(cast(Any, _FakeSession(_HitResult())), uuid.uuid4(), uuid.uuid4())
