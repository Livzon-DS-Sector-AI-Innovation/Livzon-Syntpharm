"""隐患台账人员引用解析（PersonRef）的单测。

背景：台账历史数据只有姓名快照、没有系统用户 UUID。读取侧按「姓名唯一命中 → 直接关联
并返回 UUID；同名多人 → 用责任部门消歧，唯一才关联；查无此人 / 消歧不唯一 → 仅姓名 +
首字头像 + 待确认」解析，``pending`` 表示「姓名无法唯一解析」，与列表筛选口径一致。
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.safety.models import HazardReport
from app.modules.safety.schemas.person_ref import PersonRef
from app.modules.safety.service.hazard import HazardService
from app.modules.safety.service.hazard_person import (
    PersonLookup,
    _responsible_entries,
    load_person_lookup,
    normalize_person_id,
    resolve_person_name,
    split_person_names,
)


class _FakeResult:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self._rows = rows

    def all(self) -> list[tuple[Any, ...]]:
        return self._rows


class _FakeSession:
    """按调用顺序返回预设结果集，用于验证「按 UUID 一次 + 按姓名一次」的两段查询。"""

    def __init__(self, result_sets: list[list[tuple[Any, ...]]]) -> None:
        self._result_sets = list(result_sets)
        self.call_count = 0

    async def execute(self, _stmt: Any) -> _FakeResult:
        index = min(self.call_count, len(self._result_sets) - 1)
        self.call_count += 1
        return _FakeResult(self._result_sets[index])


def _row(
    user_id: uuid.UUID,
    name: str,
    department: str | None = "生产部",
    avatar_thumb: str | None = None,
    avatar_url: str | None = None,
) -> tuple[Any, ...]:
    return (user_id, name, department, avatar_thumb, avatar_url)


def _cand(
    name: str,
    department: str | None,
    user_id: uuid.UUID | None = None,
    avatar_url: str | None = None,
) -> PersonRef:
    """构造姓名候选（PersonRef 的轻量替身，避免每行都写 cast）。"""
    return cast(
        PersonRef,
        SimpleNamespace(id=user_id or uuid.uuid4(), name=name, department=department, avatar_url=avatar_url),
    )


class TestSplitPersonNames:
    def test_mixed_separators_preserve_order(self) -> None:
        assert split_person_names("张三,李四、王五;赵六/钱七") == ["张三", "李四", "王五", "赵六", "钱七"]

    def test_empty_values(self) -> None:
        assert split_person_names(None) == []
        assert split_person_names(" , ，") == []

    def test_list_input(self) -> None:
        assert split_person_names([" 张三 ", "", "李四"]) == ["张三", "李四"]


class TestNormalizePersonId:
    def test_valid_string(self) -> None:
        value = uuid.uuid4()
        assert normalize_person_id(str(value)) == value

    def test_invalid_values(self) -> None:
        assert normalize_person_id("") is None
        assert normalize_person_id("not-a-uuid") is None
        assert normalize_person_id(None) is None


class TestPersonLookupRef:
    def test_bound_id_uses_avatar_and_is_not_pending(self) -> None:
        user_id = uuid.uuid4()
        lookup = PersonLookup(
            by_id={
                str(user_id): cast(
                    PersonRef, SimpleNamespace(id=user_id, name="张伟", department="生产部", avatar_url="a.png")
                )
            }
        )
        ref = lookup.ref(user_id, "张伟")
        assert ref is not None
        assert ref.id == user_id
        assert ref.avatar_url == "a.png"
        assert ref.department == "生产部"
        assert ref.pending is False

    def test_bound_id_missing_user_keeps_name_only(self) -> None:
        # TODO: 用户已被删除 / 跨库缺失时，不能抛错，仍要显示姓名快照
        user_id = uuid.uuid4()
        ref = PersonLookup().ref(user_id, "旧员工")
        assert ref is not None
        assert ref.id == user_id
        assert ref.name == "旧员工"
        assert ref.avatar_url is None
        assert ref.pending is False

    def test_unique_name_match_binds_directly(self) -> None:
        user_id = uuid.uuid4()
        lookup = PersonLookup(by_name={"张伟": [_cand("张伟", "生产部", user_id, "a.png")]})
        ref = lookup.ref(None, "张伟")
        assert ref is not None
        # 唯一匹配直接关联：返回 UUID、补头像、不再待确认
        assert ref.id == user_id
        assert ref.avatar_url == "a.png"
        assert ref.department == "生产部"
        assert ref.pending is False

    def test_same_name_disambiguated_by_department(self) -> None:
        prod_id, qa_id = uuid.uuid4(), uuid.uuid4()
        lookup = PersonLookup(
            by_name={
                "李雷": [
                    _cand("李雷", "生产部", prod_id),
                    _cand("李雷", "质量部", qa_id),
                ]
            }
        )
        ref = lookup.ref(None, "李雷", department_hint="生产")
        assert ref is not None
        assert ref.id == prod_id
        assert ref.pending is False

    def test_same_name_without_department_stays_pending(self) -> None:
        lookup = PersonLookup(by_name={"李雷": [_cand("李雷", "生产部"), _cand("李雷", "质量部")]})
        ref = lookup.ref(None, "李雷")
        assert ref is not None
        assert ref.id is None
        assert ref.avatar_url is None
        assert ref.pending is True

    def test_same_name_department_not_unique_stays_pending(self) -> None:
        lookup = PersonLookup(by_name={"李雷": [_cand("李雷", "生产一部"), _cand("李雷", "生产二部")]})
        # 两个候选都包含「生产」，无法消歧
        ref = lookup.ref(None, "李雷", department_hint="生产")
        assert ref is not None
        assert ref.id is None
        assert ref.pending is True

    def test_plain_text_mode_never_binds_id(self) -> None:
        user_id = uuid.uuid4()
        lookup = PersonLookup(by_name={"张伟": [_cand("张伟", "生产部", user_id, "a.png")]})
        ref = lookup.ref(None, "张伟", bind_by_name=False)
        assert ref is not None
        assert ref.id is None
        assert ref.avatar_url == "a.png"
        assert ref.pending is True

    def test_ambiguous_name_has_no_avatar(self) -> None:
        ref = PersonLookup().ref(None, "李雷")
        assert ref is not None
        assert ref.avatar_url is None
        assert ref.pending is True

    def test_no_id_and_no_name_returns_none(self) -> None:
        assert PersonLookup().ref(None, None) is None
        assert PersonLookup().ref("", "  ") is None


class TestResolvePersonName:
    """唯一匹配三态：读时解析、列表筛选、迁移回填共用同一规则。"""

    def test_not_found(self) -> None:
        assert resolve_person_name([], "王五") == (None, "not_found")

    def test_single_candidate_matched_ignores_department(self) -> None:
        ref = cast(PersonRef, SimpleNamespace(id=uuid.uuid4(), name="张伟", department="生产部", avatar_url=None))
        assert resolve_person_name([ref], "张伟", "质量部") == (ref, "matched")

    def test_duplicate_candidates_resolved_by_department(self) -> None:
        prod = cast(PersonRef, SimpleNamespace(id=uuid.uuid4(), name="李雷", department="生产部", avatar_url=None))
        qa = cast(PersonRef, SimpleNamespace(id=uuid.uuid4(), name="李雷", department="质量部", avatar_url=None))
        assert resolve_person_name([prod, qa], "李雷", "生产") == (prod, "matched")

    def test_duplicate_candidates_without_department_are_ambiguous(self) -> None:
        prod = cast(PersonRef, SimpleNamespace(id=uuid.uuid4(), name="李雷", department="生产部", avatar_url=None))
        qa = cast(PersonRef, SimpleNamespace(id=uuid.uuid4(), name="李雷", department="质量部", avatar_url=None))
        assert resolve_person_name([prod, qa], "李雷") == (None, "ambiguous")
        assert resolve_person_name([prod, qa], "李雷", "销售部") == (None, "ambiguous")


class TestLoadPersonLookup:
    async def test_two_queries_and_unique_name_only(self) -> None:
        bound_id = uuid.uuid4()
        dup_a, dup_b = uuid.uuid4(), uuid.uuid4()
        session = _FakeSession(
            [
                [_row(bound_id, "张伟", avatar_thumb="thumb.png")],
                [_row(dup_a, "李雷"), _row(dup_b, "李雷"), _row(uuid.uuid4(), "韩梅梅")],
            ]
        )
        lookup = await load_person_lookup(cast(AsyncSession, session), ids=[bound_id], names=["张伟", "李雷", "韩梅梅"])

        assert session.call_count == 2
        # avatar_thumb 优先于 avatar_url
        assert lookup.by_id[str(bound_id)].avatar_url == "thumb.png"
        # 同名候选全部保留，读时再按责任部门消歧
        assert [ref.id for ref in lookup.by_name["李雷"]] == [dup_a, dup_b]
        assert len(lookup.by_name["韩梅梅"]) == 1

    async def test_skips_queries_when_nothing_to_resolve(self) -> None:
        session = _FakeSession([[]])
        lookup = await load_person_lookup(cast(AsyncSession, session), ids=[], names=[])
        assert session.call_count == 0
        assert lookup.by_id == {}
        assert lookup.by_name == {}


class TestResponsibleEntries:
    def test_names_and_ids_align_in_order(self) -> None:
        first, second = uuid.uuid4(), uuid.uuid4()
        item = SimpleNamespace(
            rectification_responsible_person_names="张伟,李雷",
            rectification_responsible_person_ids=[str(first), str(second)],
            rectification_responsible_person=None,
            rectification_responsible_person_name=None,
        )
        entries = _responsible_entries(cast(HazardReport, item))
        assert entries == [(first, "张伟"), (second, "李雷")]

    def test_legacy_single_person_fallback(self) -> None:
        user_id = uuid.uuid4()
        item = SimpleNamespace(
            rectification_responsible_person_names=None,
            rectification_responsible_person_ids=None,
            rectification_responsible_person=user_id,
            rectification_responsible_person_name="张伟",
        )
        assert _responsible_entries(cast(HazardReport, item)) == [(user_id, "张伟")]

    def test_empty_returns_no_entries(self) -> None:
        item = SimpleNamespace(
            rectification_responsible_person_names=None,
            rectification_responsible_person_ids=[],
            rectification_responsible_person=None,
            rectification_responsible_person_name=None,
        )
        assert _responsible_entries(cast(HazardReport, item)) == []


def _fake_resolver(monkeypatch: pytest.MonkeyPatch, mapping: dict[str, uuid.UUID]) -> list[str]:
    """替换 IdentityResolver：按姓名返回固定用户，未命中的姓名视为查无此人/同名多人。"""
    calls: list[str] = []

    class _Resolver:
        def __init__(self, _session: Any) -> None:
            pass

        async def resolve_by_name_strict(self, name: str, department_hint: str | None = None) -> Any:
            calls.append(name)
            matched_id = mapping.get(name)
            person = SimpleNamespace(id=str(matched_id)) if matched_id else None
            return SimpleNamespace(is_matched=matched_id is not None, person=person)

    monkeypatch.setattr("app.modules.safety.feishu.identity_resolver.IdentityResolver", _Resolver)
    return calls


class TestBindPersonIds:
    """写入路径：姓名唯一命中才落库 UUID，未命中保持留空待人工确认。"""

    async def test_discovered_by_filled_on_unique_match(self, monkeypatch: pytest.MonkeyPatch) -> None:
        user_id = uuid.uuid4()
        _fake_resolver(monkeypatch, {"张伟": user_id})
        service = HazardService(cast(AsyncSession, SimpleNamespace()))
        data: dict[str, Any] = {"discovered_by_name": "张伟", "department": "生产部"}
        await service._bind_person_ids(data)
        assert data["discovered_by"] == user_id

    async def test_unknown_name_left_pending(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _fake_resolver(monkeypatch, {})
        service = HazardService(cast(AsyncSession, SimpleNamespace()))
        data: dict[str, Any] = {"discovered_by_name": "查无此人", "department": "生产部"}
        await service._bind_person_ids(data)
        assert "discovered_by" not in data

    async def test_existing_id_not_overwritten(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls = _fake_resolver(monkeypatch, {"张伟": uuid.uuid4()})
        service = HazardService(cast(AsyncSession, SimpleNamespace()))
        user_id = uuid.uuid4()
        data: dict[str, Any] = {"discovered_by": user_id, "discovered_by_name": "张伟"}
        await service._bind_person_ids(data)
        assert data["discovered_by"] == user_id
        assert calls == []

    async def test_multi_responsible_all_matched_writes_ids(self, monkeypatch: pytest.MonkeyPatch) -> None:
        first, second = uuid.uuid4(), uuid.uuid4()
        _fake_resolver(monkeypatch, {"张伟": first, "李雷": second})
        service = HazardService(cast(AsyncSession, SimpleNamespace()))
        data: dict[str, Any] = {
            "rectification_responsible_person_names": "张伟、李雷",
            "department": "生产部",
        }
        await service._bind_person_ids(data)
        assert data["rectification_responsible_person_ids"] == [str(first), str(second)]
        assert data["rectification_responsible_person"] == first
        assert data["rectification_responsible_person_name"] == "张伟"

    async def test_multi_responsible_partial_match_skips_ids(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _fake_resolver(monkeypatch, {"张伟": uuid.uuid4()})
        service = HazardService(cast(AsyncSession, SimpleNamespace()))
        data: dict[str, Any] = {
            "rectification_responsible_person_names": "张伟,查无此人",
            "department": "生产部",
        }
        await service._bind_person_ids(data)
        # 任一未命中则整条不写 ids，避免 ids 与 names 错位
        assert "rectification_responsible_person_ids" not in data
        assert "rectification_responsible_person" not in data
