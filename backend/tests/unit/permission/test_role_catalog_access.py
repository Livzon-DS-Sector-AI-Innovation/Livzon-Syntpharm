"""角色管理只读目录接口的准入与权限树裁剪。

背景（2026-11-18）：模块负责人 / 模块管理员只持有本模块业务码 + `{module}:admin:read`，
不含 `platform:role:read`。`/permission/tree` 若沿用单码判定，他们在模块配置页
「新建角色」时权限树会 403、界面表现为空树。
"""

import uuid
from typing import Any, cast

import pytest

from app.core.exceptions import ForbiddenException
from app.platform.identity.models import User
from app.platform.permission import api as permission_api
from app.platform.permission import deps as permission_deps
from app.platform.permission.registry import BUILTIN_ROLE_PERMISSIONS, PERMISSIONS_BY_CODE
from app.platform.permission.service.authorization import PermissionContext
from app.platform.permission.service.catalog import count_permission_leaves
from app.platform.permission.service.delegation import ModuleScope


def _user() -> User:
    return User(id=uuid.uuid4(), name="测试", username="u1")


@pytest.fixture
def access(monkeypatch):
    """把超管判定与权限码查询替换为内存 dict，隔离数据库 / Redis。"""
    state: dict[str, Any] = {"superusers": set(), "perms": {}}

    async def _is_superuser(db: Any, user: User) -> bool:
        return user.id in state["superusers"]

    async def _effective_perms(db: Any, user: User) -> set[str]:
        return cast(set[str], state["perms"].get(user.id, set()))

    monkeypatch.setattr(permission_deps, "is_superuser_with_cache", _is_superuser)
    monkeypatch.setattr(permission_deps, "effective_permission_codes", _effective_perms)
    return state


async def _resolve(user: User) -> PermissionContext:
    dependency = permission_deps.require_role_catalog_read()
    return await dependency(user=user, db=cast(Any, None))


# ── 准入集合 ──────────────────────────────────────────────────────


async def test_module_head_permissions_lack_platform_role_read() -> None:
    """根因回归：负责人 / 管理人不持有 platform:role:read，不能靠单码判定。"""
    assert "platform:role:read" not in BUILTIN_ROLE_PERMISSIONS["quality:head"]
    assert "platform:role:read" not in BUILTIN_ROLE_PERMISSIONS["quality:manager"]


async def test_module_entry_can_read_catalog(access) -> None:
    user = _user()
    access["perms"] = {user.id: {"quality:admin:read", "quality:deviation:read"}}
    ctx = await _resolve(user)
    assert ctx.permission_code == "quality:admin:read"


async def test_platform_read_permission_can_read_catalog(access) -> None:
    user = _user()
    access["perms"] = {user.id: {"platform:role:read"}}
    ctx = await _resolve(user)
    assert ctx.permission_code == "platform:role:read"


async def test_superuser_can_read_catalog(access) -> None:
    user = _user()
    access["superusers"] = {user.id}
    ctx = await _resolve(user)
    assert ctx.is_superuser is True


async def test_plain_user_is_rejected(access) -> None:
    user = _user()
    access["perms"] = {user.id: {"quality:deviation:read"}}
    with pytest.raises(ForbiddenException):
        await _resolve(user)


# ── 权限树按模块裁剪 ───────────────────────────────────────────────


async def test_tree_scoped_to_managed_module(monkeypatch) -> None:
    user = _user()

    async def _scope(db: Any, actor: User) -> ModuleScope:
        return ModuleScope(user_id=actor.id, is_system_admin=False, modules=frozenset({"quality"}))

    monkeypatch.setattr(permission_api, "resolve_module_scope", _scope)
    response = await permission_api.get_permission_tree(
        ctx=PermissionContext(user=user, permission_code="quality:admin:read"),
        db=cast(Any, None),
    )
    tree = response.data["tree"]
    assert [node["code"] for node in tree] == ["quality"]
    assert response.data["total_modules"] == 1
    assert response.data["total_permissions"] == count_permission_leaves(tree)


async def test_tree_full_for_platform_admin(monkeypatch) -> None:
    async def _scope(db: Any, actor: User) -> ModuleScope:  # pragma: no cover - 不应被调用
        raise AssertionError("平台级角色管理员不应做模块裁剪")

    monkeypatch.setattr(permission_api, "resolve_module_scope", _scope)
    response = await permission_api.get_permission_tree(
        ctx=PermissionContext(user=_user(), permission_code="platform:role:read"),
        db=cast(Any, None),
    )
    assert len(response.data["tree"]) > 1


# ── 接口清单同样受模块限制 ─────────────────────────────────────────


async def test_api_bindings_rejects_other_module_codes() -> None:
    own_code = next(code for code in PERMISSIONS_BY_CODE if code.startswith("quality:"))
    other_code = next(code for code in PERMISSIONS_BY_CODE if code.startswith("safety:"))
    ctx = PermissionContext(user=_user(), permission_code="quality:admin:read")

    response = await permission_api.list_permission_api_bindings(code=own_code, ctx=ctx)
    assert isinstance(response.data, list)

    with pytest.raises(ForbiddenException):
        await permission_api.list_permission_api_bindings(code=other_code, ctx=ctx)
