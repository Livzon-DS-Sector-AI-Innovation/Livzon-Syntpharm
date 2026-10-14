# mypy: ignore-errors
"""管理员分级：超管账号保护 + 防越级提权（guard_manage_target / assert_actor_can_grant_role）。

设计约定（2026-10-14）：
- 目标是超级管理员 → 仅超级管理员可操作（超管平级可互管）；
- 非超管操作者 → 目标权限码必须是操作者权限码的真子集（只能向下管理）；
- 授予超级管理员角色 → 操作者本人必须是超管；其余角色权限码须 ⊆ 操作者权限。
"""

import uuid
from typing import Any

import pytest

from app.core.exceptions import ForbiddenException
from app.platform.identity.models import User
from app.platform.permission.models import Role
from app.platform.permission.repository import GrantRepository, RoleRepository
from app.platform.permission.service import management
from app.platform.permission.service.management import (
    assert_actor_can_grant_role,
    guard_manage_target,
)


def _user() -> User:
    return User(id=uuid.uuid4(), name="测试", username="u1")


def _role(is_superuser: bool = False, code: str = "r1") -> Role:
    return Role(code=code, name=code, category="platform", is_superuser=is_superuser)


@pytest.fixture
def perms(monkeypatch):
    """把 is_superuser 与 effective_permission_codes 替换为内存 dict，隔离数据库。"""
    state: dict[str, Any] = {"superusers": set(), "perms": {}}

    async def _is_superuser(self, db, user):
        return user.id in state["superusers"]

    async def _effective_perms(db, user):
        return state["perms"].get(user.id, set())

    monkeypatch.setattr(GrantRepository, "is_superuser", _is_superuser)
    monkeypatch.setattr(management, "effective_permission_codes", _effective_perms)
    return state


# ── guard_manage_target ────────────────────────────────────────────


async def test_non_superuser_cannot_touch_superadmin(perms):
    actor = _user()
    target = _user()
    perms["superusers"] = {target.id}
    with pytest.raises(ForbiddenException):
        await guard_manage_target(None, actor=actor, target=target)


async def test_superuser_can_manage_peer(perms):
    actor = _user()
    target = _user()
    perms["superusers"] = {actor.id, target.id}
    await guard_manage_target(None, actor=actor, target=target)  # 不应抛


async def test_manager_can_manage_plain_user(perms):
    actor = _user()
    target = _user()
    perms["perms"] = {actor.id: {"platform:user:read", "platform:user:manage"}}
    await guard_manage_target(None, actor=actor, target=target)  # target 无权限 → 空集，是真子集


async def test_manager_cannot_manage_peer(perms):
    actor = _user()
    target = _user()
    perms["perms"] = {
        actor.id: {"platform:user:manage"},
        target.id: {"platform:user:manage"},
    }
    with pytest.raises(ForbiddenException):
        await guard_manage_target(None, actor=actor, target=target)


async def test_manager_cannot_manage_superior(perms):
    actor = _user()
    target = _user()
    perms["perms"] = {
        actor.id: {"platform:user:manage"},
        target.id: {"platform:user:manage", "platform:grant:manage"},
    }
    with pytest.raises(ForbiddenException):
        await guard_manage_target(None, actor=actor, target=target)


# ── assert_actor_can_grant_role ────────────────────────────────────


async def test_non_superuser_cannot_grant_superadmin_role(perms):
    actor = _user()
    role = _role(is_superuser=True, code="super_admin")
    with pytest.raises(ForbiddenException):
        await assert_actor_can_grant_role(None, actor=actor, role=role)


async def test_superuser_can_grant_superadmin_role(perms):
    actor = _user()
    role = _role(is_superuser=True, code="super_admin")
    perms["superusers"] = {actor.id}
    await assert_actor_can_grant_role(None, actor=actor, role=role)  # 不应抛


async def test_cannot_grant_role_beyond_own_permissions(perms, monkeypatch):
    actor = _user()
    role = _role()
    perms["perms"] = {actor.id: {"platform:user:read"}}

    async def _role_perms(self, db, role_id):
        return ["platform:user:read", "platform:user:manage"]

    monkeypatch.setattr(RoleRepository, "list_role_permission_codes", _role_perms)
    with pytest.raises(ForbiddenException):
        await assert_actor_can_grant_role(None, actor=actor, role=role)


async def test_can_grant_role_within_own_permissions(perms, monkeypatch):
    actor = _user()
    role = _role()
    perms["perms"] = {actor.id: {"platform:user:read", "platform:user:manage"}}

    async def _role_perms(self, db, role_id):
        return ["platform:user:read"]

    monkeypatch.setattr(RoleRepository, "list_role_permission_codes", _role_perms)
    await assert_actor_can_grant_role(None, actor=actor, role=role)  # 不应抛
