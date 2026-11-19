"""下线模块的内置角色退役（TC-010：agent 残留角色）。

口径（2026-11-19）：
- 只退役 `RETIRED_MODULE_CODES` 显式登记的模块，不按「注册表里没有」一刀切；
- 角色置 disabled（不物理删除），其 active 授权同步置 disabled；
- 退役后生效权限计算自然断权（查询已过滤 Role.status）。
"""

import uuid
from typing import Any, cast

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


def test_retired_modules_cover_agent_only_for_now() -> None:
    assert "agent" in RETIRED_MODULE_CODES
    # 已注册业务模块不得出现在退役名单里，否则会被启动同步误停
    from app.shared.module_registry import BUSINESS_MODULES

    assert not (RETIRED_MODULE_CODES & {m.code for m in BUSINESS_MODULES})


async def test_orphan_roles_are_disabled_with_their_grants() -> None:
    agent_head = _builtin_role("agent:head", "agent")
    agent_manager = _builtin_role("agent:manager", "agent")
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
