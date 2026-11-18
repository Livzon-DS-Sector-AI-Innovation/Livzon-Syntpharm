"""角色编码自动生成（界面不暴露编码）。

规则：
- 模块角色：`{module}:role-001`，模块内递增；
- 平台 / 全局角色：`platform:role-001`；
- 三位补零，超过 999 继续递增不截断。
"""

from typing import Any, cast

from app.platform.permission.service.role_code import next_role_code, role_code_prefix


class _Scalars:
    def __init__(self, values: list[str]) -> None:
        self._values = values

    def all(self) -> list[str]:
        return self._values


class _Result:
    def __init__(self, values: list[str]) -> None:
        self._values = values

    def scalars(self) -> _Scalars:
        return _Scalars(self._values)


class _FakeSession:
    def __init__(self, values: list[str]) -> None:
        self._values = values

    async def execute(self, *_args: Any, **_kwargs: Any) -> _Result:
        return _Result(self._values)


def test_prefix_uses_module_code_or_platform() -> None:
    assert role_code_prefix("quality") == "quality:role-"
    assert role_code_prefix(None) == "platform:role-"


async def test_first_code_is_001() -> None:
    assert await next_role_code(cast(Any, _FakeSession([])), "quality") == "quality:role-001"


async def test_increments_from_max_existing() -> None:
    db = _FakeSession(["quality:role-001", "quality:role-007", "quality:role-abc"])
    assert await next_role_code(cast(Any, db), "quality") == "quality:role-008"


async def test_platform_scope_is_independent() -> None:
    db = _FakeSession(["platform:role-003"])
    assert await next_role_code(cast(Any, db), None) == "platform:role-004"


async def test_padding_keeps_three_digits() -> None:
    db = _FakeSession(["quality:role-099"])
    assert await next_role_code(cast(Any, db), "quality") == "quality:role-100"
