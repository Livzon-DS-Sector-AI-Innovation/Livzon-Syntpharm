"""槽位结构的人工编辑：规范化、生效过滤、按锚点合并与保存校验。

只测对外可观察的行为：结构 JSON 经过这些函数后，人工改过的字段是否还在、
停用槽位是否真的不进生成、AI 新识别的位置是否补进来、非法输入是否被拒。
"""

from __future__ import annotations

import pytest

from app.core.exceptions import BadRequestException
from app.modules.research.report_gen.structure import (
    STRUCTURE_VERSION,
    anchor_key,
    edited_fields_between,
    enabled_slots,
    merge_slots,
    normalize_structure,
    structure_is_stale,
    validate_slots,
)


def _para_slot(index: int, **overrides: object) -> dict[str, object]:
    slot: dict[str, object] = {
        "slot_key": f"p{index}",
        "label": f"第{index}段",
        "value_type": "text",
        "owner_hint": None,
        "hint": None,
        "location": f"正文第{index + 1}段",
        "anchor": {
            "kind": "paragraph",
            "index": index,
            "text": "",
            "style": "",
            "fingerprint": f"fp{index}",
        },
    }
    slot.update(overrides)
    return slot


def _cell_slot(table: int, row: int, col: int, para: int = 0, **overrides: object) -> dict[str, object]:
    slot: dict[str, object] = {
        "slot_key": f"t{table}r{row}c{col}p{para}",
        "label": f"表格{table + 1} 第{row + 1}行第{col + 1}列",
        "value_type": "text",
        "owner_hint": None,
        "hint": None,
        "location": f"表格{table + 1} 第{row + 1}行第{col + 1}列",
        "anchor": {
            "kind": "table_cell",
            "table_index": table,
            "row": row,
            "col": col,
            "para_index": para,
            "text": "",
            "style": "",
            "fingerprint": "fp",
        },
    }
    slot.update(overrides)
    return slot


# ---------------------------------------------------------------------------
# 规范化：老结构（version 1、无人工标记）读出来必须是「全部启用、无人工修改」
# ---------------------------------------------------------------------------


def test_legacy_structure_normalizes_to_enabled_without_manual_flags() -> None:
    legacy = {
        "version": 1,
        "source_key": "tmp/a.docx",
        "analyzed_at": "2026-11-01T00:00:00+00:00",
        "slots": [_para_slot(0)],
    }

    result = normalize_structure(legacy)

    assert result["version"] == STRUCTURE_VERSION
    assert result["source_key"] == "tmp/a.docx"
    assert result["analyzed_at"] == "2026-11-01T00:00:00+00:00"
    slot = result["slots"][0]
    assert slot["is_enabled"] is True
    assert slot["origin"] == "ai"
    assert slot["edited_fields"] == []


def test_normalize_keeps_manual_flags_and_disabled_state() -> None:
    raw = {
        "slots": [
            _para_slot(
                0,
                is_enabled=False,
                origin="manual",
                edited_fields=["label", "not_a_real_field"],
            )
        ]
    }

    slot = normalize_structure(raw)["slots"][0]

    assert slot["is_enabled"] is False
    assert slot["origin"] == "manual"
    # 未知的痕迹字段直接丢弃，避免把任意输入原样存回 JSON
    assert slot["edited_fields"] == ["label"]


def test_normalize_tolerates_empty_or_broken_structure() -> None:
    assert normalize_structure(None)["slots"] == []
    assert normalize_structure({"slots": ["oops", 42]})["slots"] == []


def test_normalize_falls_back_on_unknown_value_type() -> None:
    slot = normalize_structure({"slots": [_para_slot(0, value_type="rich_text")]})["slots"][0]

    assert slot["value_type"] == "text"


# ---------------------------------------------------------------------------
# 生成侧过滤：停用槽位不得进入建行、下发与回写
# ---------------------------------------------------------------------------


def test_enabled_slots_skips_disabled_slot() -> None:
    structure = {
        "slots": [
            _para_slot(0),
            _para_slot(1, is_enabled=False, origin="manual"),
        ]
    }

    assert [slot["label"] for slot in enabled_slots(structure)] == ["第0段"]


def test_enabled_slots_treats_missing_flag_as_enabled() -> None:
    assert len(enabled_slots({"slots": [_para_slot(0)]})) == 1


def test_generation_prompt_only_counts_enabled_slots() -> None:
    """停用槽位必须在构造初始 prompt 之前就被过滤掉，否则模型仍会去填。"""
    from types import SimpleNamespace

    from app.modules.research.report_gen.agent import _build_messages

    structure = {"slots": [_para_slot(0), _para_slot(1, is_enabled=False, origin="manual")]}
    enabled_structure = {**structure, "slots": enabled_slots(structure)}

    job = SimpleNamespace(doc_code=None, drug_name=None, supplement_text=None)
    project = SimpleNamespace(name="示例项目", api_name="示例 API")
    report = SimpleNamespace(title="示例报告", report_type="阶段性报告", stage="临床前", version="v1")

    messages = _build_messages(job, project, report, enabled_structure, "系统提示词")

    assert messages[0]["content"] == "系统提示词"
    assert "槽位数量：1" in messages[1]["content"]


# ---------------------------------------------------------------------------
# 合并重解析：人工改过的字段不许被 AI 覆盖，AI 新增的位置要补进来
# ---------------------------------------------------------------------------


def test_merge_keeps_manual_fields_and_takes_ai_for_the_rest() -> None:
    existing = [
        _para_slot(3, label="人工品种名称", edited_fields=["label"], origin="manual"),
    ]
    ai = [_para_slot(3, label="品种名称", hint="AI 给的说明")]

    merged, stats = merge_slots(existing, ai)

    assert len(merged) == 1
    assert merged[0]["label"] == "人工品种名称"
    assert merged[0]["hint"] == "AI 给的说明"
    assert merged[0]["origin"] == "manual"
    assert stats == {"added": 0, "kept": 1, "removed": 0}


def test_merge_appends_new_ai_anchor() -> None:
    merged, stats = merge_slots([_para_slot(1)], [_para_slot(1), _para_slot(2, label="品种名称")])

    assert [slot["label"] for slot in merged] == ["第1段", "品种名称"]
    assert merged[1]["origin"] == "ai"
    assert merged[1]["edited_fields"] == []
    assert stats == {"added": 1, "kept": 1, "removed": 0}


def test_merge_keeps_manual_slot_that_ai_no_longer_recognizes() -> None:
    existing = [
        _para_slot(1),
        _para_slot(5, label="人工补的槽位", origin="manual"),
    ]

    merged, stats = merge_slots(existing, [_para_slot(1)])

    assert [slot["label"] for slot in merged] == ["第1段", "人工补的槽位"]
    assert stats == {"added": 0, "kept": 2, "removed": 0}


def test_merge_drops_untouched_slot_that_ai_no_longer_recognizes() -> None:
    existing = [_para_slot(1), _para_slot(6)]

    merged, stats = merge_slots(existing, [_para_slot(1)])

    assert [slot["label"] for slot in merged] == ["第1段"]
    assert stats == {"added": 0, "kept": 1, "removed": 1}


def test_merge_keeps_slot_keys_unique_against_retained_manual_slot() -> None:
    existing = [_para_slot(1, slot_key="drug_name", origin="manual")]
    ai = [_para_slot(2, slot_key="drug_name", label="品种名称")]

    merged, _ = merge_slots(existing, ai)

    keys = [slot["slot_key"] for slot in merged]
    assert len(keys) == len(set(keys)) == 2


def test_merge_orders_slots_by_document_position() -> None:
    # 两个旧槽位都标成人工保留，才不会被「AI 本次没识别」规则移除
    existing = [_cell_slot(0, 2, 1, origin="manual"), _para_slot(5, origin="manual")]
    ai = [_para_slot(1), _cell_slot(0, 0, 1, label="表头值")]

    merged, _ = merge_slots(existing, ai)

    assert [slot["label"] for slot in merged] == [
        "第1段",
        "第5段",
        "表头值",
        "表格1 第3行第2列",
    ]


def test_merge_distinguishes_paragraphs_inside_one_cell() -> None:
    existing = [_cell_slot(0, 1, 1, para=0)]
    ai = [_cell_slot(0, 1, 1, para=0), _cell_slot(0, 1, 1, para=1, label="同格第二段")]

    merged, stats = merge_slots(existing, ai)

    assert len(merged) == 2
    assert stats["added"] == 1


# ---------------------------------------------------------------------------
# 保存时的差异回填：只记录人工真正改过的字段
# ---------------------------------------------------------------------------


def test_edited_fields_between_reports_changed_fields_only() -> None:
    old = _para_slot(1)
    new = _para_slot(1, label="品种名称", is_enabled=False)

    assert edited_fields_between(old, new) == ["is_enabled", "label"]


def test_edited_fields_between_ignores_untouched_slot() -> None:
    assert edited_fields_between(_para_slot(1), _para_slot(1)) == []


def test_edited_fields_between_detects_rebound_anchor() -> None:
    old = _para_slot(1)
    new = _para_slot(1, anchor={"kind": "paragraph", "index": 7, "text": "", "style": "", "fingerprint": "x"})

    assert "anchor" in edited_fields_between(old, new)


# ---------------------------------------------------------------------------
# 保存校验：重复标识、不存在的锚点、非法枚举都要拦在写库之前
# ---------------------------------------------------------------------------


def test_validate_slots_rejects_duplicate_slot_key() -> None:
    slots = [_para_slot(1), _para_slot(2, slot_key="p1")]

    with pytest.raises(BadRequestException):
        validate_slots(slots, {anchor_key(_para_slot(1)["anchor"]), anchor_key(_para_slot(2)["anchor"])})


def test_validate_slots_rejects_anchor_outside_mother_document() -> None:
    with pytest.raises(BadRequestException):
        validate_slots([_para_slot(9)], {anchor_key(_para_slot(1)["anchor"])})


def test_validate_slots_rejects_empty_label() -> None:
    with pytest.raises(BadRequestException):
        validate_slots([_para_slot(1, label="  ")], {anchor_key(_para_slot(1)["anchor"])})


def test_validate_slots_accepts_valid_payload() -> None:
    validate_slots([_para_slot(1), _cell_slot(0, 0, 0)], set())  # 空集合 = 跳过锚点校验


# ---------------------------------------------------------------------------
# 过期判定：母本换版后旧结构不能被当成有效结构保存
# ---------------------------------------------------------------------------


def test_structure_is_stale_when_source_key_differs() -> None:
    assert structure_is_stale({"source_key": "a"}, "b") is True
    assert structure_is_stale({"source_key": "a"}, "a") is False
    assert structure_is_stale({}, "a") is True
    assert structure_is_stale(None, "a") is True


# ---------------------------------------------------------------------------
# 服务层纯逻辑：候选位对齐与人工痕迹回填（不碰数据库）
# ---------------------------------------------------------------------------


def _candidate(candidate_id: str, slot: dict[str, object]) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "kind": "paragraph",
        "label": slot["location"],
        "text": "",
        "style": "",
        "context": "",
        "anchor": slot["anchor"],
    }


def test_resolve_slots_maps_candidate_id_to_real_anchor() -> None:
    from app.modules.research.doc_template.service import _resolve_slots

    candidates = [_candidate("p0", _para_slot(0))]

    resolved = _resolve_slots([{"slot_key": "name", "label": "品种名称", "candidate_id": "p0"}], candidates)

    assert resolved[0]["anchor"]["index"] == 0
    assert resolved[0]["location"] == "正文第1段"


def test_resolve_slots_rejects_position_outside_current_mother() -> None:
    from app.modules.research.doc_template.service import _resolve_slots

    candidates = [_candidate("p0", _para_slot(0))]

    with pytest.raises(BadRequestException):
        _resolve_slots([{"slot_key": "x", "label": "X", "anchor": _para_slot(9)["anchor"]}], candidates)

    with pytest.raises(BadRequestException):
        _resolve_slots([{"slot_key": "x", "label": "X"}], candidates)


def test_stamp_manual_edits_marks_only_real_changes_and_locks_new_rows() -> None:
    from app.modules.research.doc_template.service import _stamp_manual_edits

    stamped = _stamp_manual_edits(
        [_para_slot(0, label="人工名称"), _para_slot(1, slot_key="added_by_human")],
        [_para_slot(0)],
    )

    assert stamped[0]["edited_fields"] == ["label"]
    assert stamped[0]["origin"] == "manual"
    # 人工新增的行锁住身份字段，重解析不会把它改名或挪走
    assert set(stamped[1]["edited_fields"]) == {"anchor", "label", "slot_key"}
    assert stamped[1]["origin"] == "manual"
