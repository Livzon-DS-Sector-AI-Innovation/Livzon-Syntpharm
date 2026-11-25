"""下线模块的内置角色退役机制（当前退役名单为空）。

口径（2026-11-19）：
- 只退役 `RETIRED_MODULE_CODES` 显式登记的模块，不按「注册表里没有」一刀切；
- 角色置 disabled（不物理删除），其 active 授权同步置 disabled；
- 退役后生效权限计算自然断权（查询已过滤 Role.status）。
"""

import uuid
from typing import Any, cast

import pytest

from app.platform.permission.models import GRANT_DISABLED, Role
from app.platform.permission.registry import RETIRED_MODULE_CODES
from app.platform.permission.service import management


class _RoleListResult:
    def __init__(self, roles: list[Role]) -> None:
        self._roles = roles

    def scalars(self) -> "_RoleListResult":
        return self

    def all(self) -> list[Role]:
        return self._roles


class _FakeSession:
    """按调用顺序返回预置结果，并记录后续 update 语句。"""

    def __init__(self, roles: list[Role]) -> None:
        self._roles = roles
        self.updates: list[Any] = []

    async def execute(self, stmt: Any) -> Any:
        if not self.updates and hasattr(stmt, "column_descriptions"):
            return _RoleListResult(self._roles)
        self.updates.append(stmt)
        return None


def _builtin_role(code: str, module_code: str) -> Role:
    role = Role(
        code=code,
        name=code,
        category="module",
        role_type="owner",
        module_code=module_code,
        is_builtin=True,
        status="active",
    )
    role.id = uuid.uuid4()
    return role


def test_retired_modules_do_not_overlap_registered_modules() -> None:
    """退役名单只能登记确认下线的模块。

    2026-11-21：agent 已由 main 的 #224 重新上线（PPT 配音视频），因此从名单移除；
    这里只守「退役名单与在册业务模块不相交」这一条不变量，不锁定具体内容。
    """
    from app.shared.module_registry import BUSINESS_MODULES

    assert not (RETIRED_MODULE_CODES & {m.code for m in BUSINESS_MODULES})


async def test_orphan_roles_are_disabled_with_their_grants(monkeypatch: pytest.MonkeyPatch) -> None:
    # 机制保留备用：当前名单为空，用测试专用模块码覆盖后再验证退役行为
    monkeypatch.setattr(management, "RETIRED_MODULE_CODES", frozenset({"legacy_demo"}))
    agent_head = _builtin_role("legacy_demo:head", "legacy_demo")
    agent_manager = _builtin_role("legacy_demo:manager", "legacy_demo")
    session = _FakeSession([agent_head, agent_manager])

    count = await management._retire_orphan_builtin_roles(cast(Any, session))

    assert count == 2
    assert agent_head.status == GRANT_DISABLED
    assert agent_manager.status == GRANT_DISABLED
    # 每个角色一条 update 授权语句
    assert len(session.updates) == 2


async def test_retire_is_noop_when_no_orphans() -> None:
    session = _FakeSession([])

    count = await management._retire_orphan_builtin_roles(cast(Any, session))

    assert count == 0
    assert session.updates == []
