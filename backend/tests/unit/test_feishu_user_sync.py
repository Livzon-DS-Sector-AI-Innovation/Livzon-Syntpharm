# mypy: ignore-errors
"""飞书成员同步：部门跟随飞书 + 账号回填策略。

口径（2026-11-09）：
- 部门以飞书为准（人员换部门要跟着变），飞书没给部门时保留本地旧值；
- 账号不自动生成（飞书 user_id / 工号权限未开通），只做「有值才回填」；
- 工号 / user_id 有值且未被占用时才回填 username，冲突则跳过不打断整批同步。
"""

from typing import Any

import pytest

from app.platform.identity.models import User
from app.platform.integrations.feishu import sync as sync_module


class _StubResult:
    def __init__(self, value: Any) -> None:
        self._value = value

    def scalar_one_or_none(self) -> Any:
        return self._value


class _StubSession:
    """按调用顺序吐出预设查询结果，记录 add/flush/commit。"""

    def __init__(self, results: list[Any]) -> None:
        self._results = list(results)
        self.added: list[Any] = []
        self.commits = 0
        self.flushes = 0

    async def execute(self, _stmt: Any) -> _StubResult:
        return _StubResult(self._results.pop(0))

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        self.flushes += 1

    async def commit(self) -> None:
        self.commits += 1


class _StubFactory:
    def __init__(self, session: _StubSession) -> None:
        self.session = session

    def __call__(self) -> "_StubFactory":
        return self

    async def __aenter__(self) -> _StubSession:
        return self.session

    async def __aexit__(self, *exc: Any) -> bool:
        return False


def _parsed(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "open_id": "ou_test",
        "user_id": None,
        "union_id": None,
        "name": "张三",
        "en_name": "Zhang San",
        "employee_no": None,
        "email": None,
        "mobile": None,
        "department": "新部门",
        "position": "工程师",
        "avatar_url": "https://cdn.example.com/a.png",
        "avatar_thumb": "https://cdn.example.com/a_t.png",
        "avatar_middle": None,
        "avatar_big": None,
        "feishu_department_ids": '["d1"]',
        "is_resigned": False,
        "is_frozen": False,
    }
    base.update(overrides)
    return base


@pytest.fixture()
def patch_factory(monkeypatch: pytest.MonkeyPatch):
    def _patch(results: list[Any]) -> _StubSession:
        session = _StubSession(results)
        monkeypatch.setattr(sync_module, "async_session_factory", _StubFactory(session))
        return session

    return _patch


async def test_upsert_user_overwrites_department_with_feishu_value(patch_factory) -> None:
    user = User(name="张三", department="旧部门")
    patch_factory([user])

    await sync_module._upsert_user(_parsed(department="新部门"))

    assert user.department == "新部门"


async def test_upsert_user_keeps_department_when_feishu_has_none(patch_factory) -> None:
    user = User(name="张三", department="旧部门")
    patch_factory([user])

    await sync_module._upsert_user(_parsed(department=""))

    assert user.department == "旧部门"


async def test_upsert_user_backfills_username_from_employee_no(patch_factory) -> None:
    user = User(name="张三", department="研发部")
    patch_factory([user, None])

    await sync_module._upsert_user(_parsed(employee_no="YTH00123"))

    assert user.username == "YTH00123"


async def test_upsert_user_skips_backfill_when_username_taken(patch_factory) -> None:
    user = User(name="张三", department="研发部")
    patch_factory([user, "other-user-id"])

    await sync_module._upsert_user(_parsed(employee_no="YTH00123"))

    assert user.username is None


async def test_upsert_user_never_touches_existing_username(patch_factory) -> None:
    user = User(name="张三", username="liujg", department="研发部")
    patch_factory([user])

    await sync_module._upsert_user(_parsed(employee_no="YTH00123", user_id="u_123"))

    assert user.username == "liujg"


async def test_upsert_user_skips_backfill_without_candidate(patch_factory) -> None:
    # 只给一个查询结果：若回填逻辑仍去查重，会因结果耗尽而报错，从而证明被跳过
    user = User(name="张三", department="研发部")
    patch_factory([user])

    await sync_module._upsert_user(_parsed())

    assert user.username is None


async def test_upsert_new_user_backfills_username(patch_factory) -> None:
    session = patch_factory([None, None])

    await sync_module._upsert_user(_parsed(open_id="ou_new", employee_no="YTH00888"))

    assert len(session.added) == 1
    assert session.added[0].username == "YTH00888"
    assert session.commits == 1
