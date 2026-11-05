"""隐患台账人员「姓名 → 系统用户」严格匹配的回归测试。

背景：隐患台账的检查人员 / 整改责任人以 identity.users 的 UUID 为准、姓名为展示快照。
飞书导入只提供姓名，历史实现同名多人时"取第一个"，会静默错绑到别人身上。
严格模式要求：同名多人且无法唯一消歧时不绑定（uuid 留空），交给人工指定。
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

from app.modules.safety.feishu import identity_resolver as resolver_module
from app.modules.safety.feishu.bitable_handler import _resolve_person
from app.modules.safety.feishu.identity_resolver import IdentityResolver, NameMatch

# monkeypatch 会替换模块属性，这里先留住真实类用于构造 ResolvedPerson
_REAL_RESOLVER = IdentityResolver


def _user(name: str, department: str | None = None) -> Any:
    return SimpleNamespace(
        id=uuid.uuid4(),
        name=name,
        department=department,
        feishu_open_id=f"ou_{name}",
        feishu_user_id=f"uid_{name}",
    )


class _StubResolver(IdentityResolver):
    """只替换姓名查询，验证三态判定逻辑本身。"""

    def __init__(self, users: list[Any]) -> None:
        super().__init__(session=None)  # type: ignore[arg-type]
        self._users = users

    async def _find_users_by_name(self, name: str) -> list[Any]:
        return [u for u in self._users if u.name == name]


class TestResolveByNameStrict:
    async def test_empty_name_is_not_found(self) -> None:
        match = await _StubResolver([]).resolve_by_name_strict("   ")
        assert match.status == "not_found"
        assert match.person is None

    async def test_unique_hit_matches(self) -> None:
        user = _user("张伟", "生产部")
        match = await _StubResolver([user]).resolve_by_name_strict("张伟")
        assert match.is_matched
        assert match.person is not None
        assert match.person.id == str(user.id)

    async def test_unknown_name_is_not_found(self) -> None:
        match = await _StubResolver([_user("张伟", "生产部")]).resolve_by_name_strict("李雷")
        assert match.status == "not_found"
        assert match.person is None

    async def test_same_name_disambiguated_by_department(self) -> None:
        users = [_user("张伟", "生产部"), _user("张伟", "EHS部")]
        match = await _StubResolver(users).resolve_by_name_strict("张伟", department_hint="EHS部")
        assert match.is_matched
        assert match.person is not None
        assert match.person.department == "EHS部"

    async def test_same_name_without_hint_is_ambiguous(self) -> None:
        users = [_user("张伟", "生产部"), _user("张伟", "EHS部")]
        match = await _StubResolver(users).resolve_by_name_strict("张伟")
        assert match.status == "ambiguous"
        # 关键：不能返回任何一个候选，交给人工指定
        assert match.person is None
        assert len(match.candidates) == 2

    async def test_same_name_same_department_stays_ambiguous(self) -> None:
        users = [_user("张伟", "生产部"), _user("张伟", "生产部")]
        match = await _StubResolver(users).resolve_by_name_strict("张伟", department_hint="生产部")
        assert match.status == "ambiguous"
        assert match.person is None
        assert len(match.candidates) == 2


class _AmbiguousResolver:
    def __init__(self, session: Any) -> None:
        self._session = session

    async def resolve_by_name_strict(self, name: str, department_hint: str | None = None) -> NameMatch:
        return NameMatch(
            status="ambiguous",
            name=name,
            candidates=[
                _REAL_RESOLVER._user_to_person(_user("张伟", "生产部")),
                _REAL_RESOLVER._user_to_person(_user("张伟", "EHS部")),
            ],
        )


class _MatchedResolver:
    def __init__(self, session: Any) -> None:
        self._session = session

    async def resolve_by_name_strict(self, name: str, department_hint: str | None = None) -> NameMatch:
        person = _REAL_RESOLVER._user_to_person(_user("张伟", "生产部"))
        return NameMatch(status="matched", name=name, person=person)


class TestResolvePersonStrictMode:
    """_resolve_person 在严格模式下：宁可 uuid 留空，也不能把姓名错绑到别人。"""

    _BT_VALUE = [{"id": "", "name": "张伟", "email": ""}]

    async def test_ambiguous_name_keeps_name_without_uuid(self, monkeypatch: Any) -> None:
        monkeypatch.setattr(resolver_module, "IdentityResolver", _AmbiguousResolver)
        db_uuid, _open_id, display_name = await _resolve_person(
            None,
            self._BT_VALUE,
            bt_field_label="检查人员",
            strict_name=True,
        )
        assert db_uuid is None
        assert display_name == "张伟"

    async def test_matched_name_returns_uuid(self, monkeypatch: Any) -> None:
        monkeypatch.setattr(resolver_module, "IdentityResolver", _MatchedResolver)
        db_uuid, _open_id, display_name = await _resolve_person(
            None,
            self._BT_VALUE,
            bt_field_label="检查人员",
            strict_name=True,
        )
        assert db_uuid is not None
        assert display_name == "张伟"
