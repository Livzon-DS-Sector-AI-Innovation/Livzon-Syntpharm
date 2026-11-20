"""下线模块的内置角色退役（TC-010）。

口径：
- 只退役 `RETIRED_MODULE_CODES` 显式登记的模块，不按「注册表里没有」一刀切；
- 角色置 disabled（不物理删除），其 active 授权同步置 disabled；
- 退役后生效权限计算自然断权（查询已过滤 Role.status）；
- 合入 uat 时登记表为空：`agent` 模块在 uat 仍在线（PPT 配音视频在测），
  所以这里用 monkeypatch 注入一个虚构的下线模块来验证退役逻辑。
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


def test_retired_modules_exclude_live_business_modules() -> None:
    # 已注册业务模块不得出现在退役名单里，否则会被启动同步误停。
    # 合入 uat 后 agent 仍在 BUSINESS_MODULES 中，因此登记表必须为空。
    from app.shared.module_registry import BUSINESS_MODULES

    assert not (RETIRED_MODULE_CODES & {m.code for m in BUSINESS_MODULES})


async def test_orphan_roles_are_disabled_with_their_grants(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(management, "RETIRED_MODULE_CODES", frozenset({"retired-module"}))
    orphan_owner = _builtin_role("retired-module:owner", "retired-module")
    orphan_delegate = _builtin_role("retired-module:delegate", "retired-module")
    session = _FakeSession([orphan_owner, orphan_delegate])

    count = await management._retire_orphan_builtin_roles(cast(Any, session))

    assert count == 2
    assert orphan_owner.status == GRANT_DISABLED
    assert orphan_delegate.status == GRANT_DISABLED
    # 每个角色一条 update 授权语句
    assert len(session.updates) == 2


async def test_retire_is_noop_when_no_orphans() -> None:
    session = _FakeSession([])

    count = await management._retire_orphan_builtin_roles(cast(Any, session))

    assert count == 0
    assert session.updates == []
