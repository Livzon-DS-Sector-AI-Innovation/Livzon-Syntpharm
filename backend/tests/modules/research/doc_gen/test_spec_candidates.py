"""候选锚点位置枚举：人工新增填写项时，系统列出母本里尚未被占用的可锚定位置。"""

from __future__ import annotations

import pytest

from app.modules.research.doc_gen.anchors import resolve_slot
from app.modules.research.doc_gen.renderer import open_document
from app.modules.research.doc_gen.spec_candidates import (
    add_slot_to_spec,
    anchor_signature,
    generate_slot_key,
    list_anchor_candidates,
)
from app.modules.research.doc_gen.spec_draft import draft_spec_from_bytes
from app.modules.research.doc_gen.template_spec import TEMPLATE_DIR, Anchor, Slot, TemplateSpec

ASSET = TEMPLATE_DIR / "tech_research_report.dotx"


def _data() -> bytes:
    return ASSET.read_bytes()


def _spec(slots: list[Slot] | None = None) -> TemplateSpec:
    """构造一个最小可用规格（master_asset 仅占位，TemplateSpec 不校验文件存在）。"""
    return TemplateSpec(
        code="test_manual",
        name="人工新增测试模板",
        version="v1",
        master_asset="tech_research_report.dotx",
        slots=slots or [],
    )


def _anchor(label: str = "项目名称") -> Anchor:
    return Anchor(type="paragraph_after_label", paragraph_label=label)


def test_candidates_cover_all_positions_when_no_existing() -> None:
    """空模板（existing=None）：规则检测到的位置都成为候选，且锚点签名不重复。"""
    data = _data()
    candidates = list_anchor_candidates(data, None)
    assert candidates, "真实母本应能枚举出候选位置"
    assert all(candidate.label for candidate in candidates)
    assert all(candidate.anchor is not None for candidate in candidates)
    signatures = [candidate.anchor.model_dump_json(exclude_none=True) for candidate in candidates]
    assert len(signatures) == len(set(signatures)), "候选锚点不应重复"


def test_all_positions_occupied_yields_no_duplicate_candidate() -> None:
    """把 draft 自身当作 existing：草拟已识别的位置不再重复列候选。

    补扫允许出现草拟「宁缺毋滥」丢弃的表格（如表头多格为空的签名表）——这正是
    漏识别的人工出口；但任何与草拟槽位同签名的候选都是 bug。
    """
    data = _data()
    draft = draft_spec_from_bytes(data, name="技术调研报告")
    candidates = list_anchor_candidates(data, draft)
    draft_sigs = {anchor_signature(slot.anchors[0]) for slot in draft.slots if slot.anchors}
    assert all(anchor_signature(c.anchor) not in draft_sigs for c in candidates)
    assert all(c.kind == "table" for c in candidates), "补扫候选只应是草拟丢弃的整表位置"


def test_partially_occupied_filters_only_taken_positions() -> None:
    """只占用部分槽位：被占用的位置从候选里消失，其余保留。"""
    data = _data()
    full = list_anchor_candidates(data, None)
    draft = draft_spec_from_bytes(data, name="技术调研报告")
    partial = draft.model_copy(deep=True)
    partial.slots = partial.slots[:1]  # 只占用第一个检测到的位置
    remaining = list_anchor_candidates(data, partial)
    assert len(remaining) == len(full) - 1


def test_candidate_anchor_round_trips() -> None:
    """候选锚点必须能直接用于建槽位：序列化往返不丢类型信息。"""
    data = _data()
    candidates = list_anchor_candidates(data, None)
    assert candidates
    first = candidates[0]
    restored = Anchor.model_validate(first.anchor.model_dump(exclude_none=True))
    assert restored.type == first.anchor.type
    assert restored.model_dump(exclude_none=True) == first.anchor.model_dump(exclude_none=True)


# ---------------------------------------------------------------------------
# generate_slot_key：人工槽位没有业务 key，用递增序号保证唯一
# ---------------------------------------------------------------------------


def test_generate_slot_key_starts_at_one_for_empty_spec() -> None:
    assert generate_slot_key(_spec()) == "manual_1"


def test_generate_slot_key_skips_existing_manual_keys() -> None:
    spec = _spec(
        [
            Slot(key="manual_1", label="甲", anchors=[_anchor("甲")]),
            Slot(key="manual_2", label="乙", anchors=[_anchor("乙")]),
        ]
    )
    assert generate_slot_key(spec) == "manual_3"


def test_generate_slot_key_ignores_non_manual_keys() -> None:
    spec = _spec([Slot(key="project_name", label="项目名称", anchors=[_anchor()])])
    assert generate_slot_key(spec) == "manual_1"


# ---------------------------------------------------------------------------
# add_slot_to_spec：纯函数，就地追加并返回新槽位
# ---------------------------------------------------------------------------


def test_add_slot_appends_with_generated_key() -> None:
    spec = _spec()
    slot = add_slot_to_spec(spec, anchor=_anchor(), label="  受理号  ", kind="field", expects="text")
    assert spec.slots == [slot]
    assert slot.key == "manual_1"
    assert slot.label == "受理号"  # 去空白
    assert slot.kind == "field"
    assert slot.expects == "text"
    assert slot.review_state == "auto"
    assert slot.anchors == [_anchor()]


def test_add_slot_preserves_semantics() -> None:
    spec = _spec()
    slot = add_slot_to_spec(
        spec,
        anchor=_anchor(),
        label="含量",
        expects="percent",
        required=True,
        query_hint="HPLC 纯度",
        search_terms=["纯度", "assay"],
    )
    assert slot.expects == "percent"
    assert slot.required is True
    assert slot.query_hint == "HPLC 纯度"
    assert slot.search_terms == ["纯度", "assay"]


def test_add_slot_rejects_empty_label() -> None:
    with pytest.raises(ValueError, match="名称不能为空"):
        add_slot_to_spec(_spec(), anchor=_anchor(), label="   ")


def test_add_slot_accepts_table_with_columns() -> None:
    """表格类候选可整表成槽：列定义按顺序生成 c1..cN，table_rows 锚点原样保留。"""
    spec = _spec()
    slot = add_slot_to_spec(
        spec,
        anchor=Anchor(type="table_rows", table_header=["批号", "数量"]),
        label="批次表",
        kind="table",
        columns=["批号", "数量"],
    )
    assert slot.kind == "table"
    assert [c.key for c in slot.columns] == ["c1", "c2"]
    assert [c.label for c in slot.columns] == ["批号", "数量"]
    assert slot.table is not None and slot.table.header_rows == 1


def test_add_slot_table_uses_candidate_header_rows() -> None:
    """双行表头候选透传 header_rows=2，渲染期数据区从第二表头行之后开始。"""
    spec = _spec()
    slot = add_slot_to_spec(
        spec,
        anchor=Anchor(type="table_rows", table_header=["纯度", "收率"]),
        label="指标表",
        kind="table",
        columns=["纯度", "收率"],
        header_rows=2,
    )
    assert slot.table is not None and slot.table.header_rows == 2


def test_add_slot_rejects_table_without_columns() -> None:
    with pytest.raises(ValueError, match="列定义"):
        add_slot_to_spec(
            _spec(),
            anchor=Anchor(type="table_rows", table_header=["批号"]),
            label="批次表",
            kind="table",
        )


def test_add_slot_rejects_table_with_wrong_anchor() -> None:
    with pytest.raises(ValueError, match="table_rows 锚点"):
        add_slot_to_spec(
            _spec(),
            anchor=Anchor(type="paragraph_after_label", paragraph_label="批次表："),
            label="批次表",
            kind="table",
            columns=["批号"],
        )


def test_add_slot_rejects_cell_anchor_without_guard() -> None:
    """坐标锚点缺 guard 会被模板增删行错位填格子，必须拒绝。"""
    with pytest.raises(ValueError, match="guard"):
        add_slot_to_spec(
            _spec(),
            anchor=Anchor(type="table_cell", table_header=["批号"], row_index=1, col_index=0),
            label="批号格",
        )


def test_missed_table_candidate_round_trips_to_resolvable_slot() -> None:
    """补扫候选 → 人工成槽 → 渲染期可定位：漏识别的表格经补录后不再是死路。"""
    data = _data()
    draft = draft_spec_from_bytes(data, name="技术调研报告")
    missed = [c for c in list_anchor_candidates(data, draft) if c.kind == "table"]
    assert missed, "真实母本里草拟丢弃的待填表应被补扫成候选"
    chosen = missed[0]
    spec = _spec()
    slot = add_slot_to_spec(
        spec,
        anchor=chosen.anchor,
        label=chosen.label or "补录表格",
        kind="table",
        columns=chosen.columns,
        header_rows=chosen.header_rows,
    )
    resolve_slot(open_document(data), slot)  # 定位失败会抛 AnchorUnresolvedError


def test_add_slot_rejects_occupied_anchor() -> None:
    spec = _spec()
    add_slot_to_spec(spec, anchor=_anchor("项目名称"), label="项目名称")
    with pytest.raises(ValueError, match="已被现有填写项占用"):
        add_slot_to_spec(spec, anchor=_anchor("项目名称"), label="重复位置")


def test_add_slot_rejects_explicit_key_conflict() -> None:
    spec = _spec([Slot(key="manual_1", label="甲", anchors=[_anchor("甲")])])
    with pytest.raises(ValueError, match="已存在"):
        add_slot_to_spec(spec, anchor=_anchor("乙"), label="乙", key="manual_1")


def test_add_slot_accepts_explicit_unique_key() -> None:
    spec = _spec()
    slot = add_slot_to_spec(spec, anchor=_anchor(), label="自定义", key="my_slot")
    assert slot.key == "my_slot"


def test_add_slot_from_real_candidate_then_marks_occupied() -> None:
    """从真实母本枚举候选 → 点选非表格候选建槽位 → 该位置随即被占用、不再出现在候选里。"""
    data = _data()
    candidates = [c for c in list_anchor_candidates(data, None) if c.kind != "table"]
    assert candidates, "真实母本应能枚举出非表格候选位置"
    chosen = candidates[0]
    spec = _spec()
    slot = add_slot_to_spec(spec, anchor=chosen.anchor, label=chosen.label or "新增填写项", kind=chosen.kind)
    assert spec.slots == [slot]
    assert slot.key == "manual_1"
    remaining = list_anchor_candidates(data, spec)
    remaining_sigs = {c.anchor.model_dump_json(exclude_none=True) for c in remaining}
    assert chosen.anchor.model_dump_json(exclude_none=True) not in remaining_sigs
