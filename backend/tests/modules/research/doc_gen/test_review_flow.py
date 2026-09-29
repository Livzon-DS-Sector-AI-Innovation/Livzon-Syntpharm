"""两阶段任务（提取 → 人工确认 → 渲染）中可离线验证的部分。

流水线首次执行只走到 `awaiting_review` 并落库槽位结果，人工确认后的续跑完全
依赖「落库结果 → SlotResult 还原」这一步：字段还原错了，依据与候选值就会在
生成说明里静默丢失，所以这里逐字段把它钉死。
"""

from __future__ import annotations

from typing import Any

from app.modules.research.doc_gen import pipeline, status
from app.modules.research.doc_gen.models import JOB_STATUS_VALUES, DocGenSlotValue


def _row(**overrides: Any) -> DocGenSlotValue:
    base: dict[str, Any] = {
        "slot_key": "route_1",
        "label": "工艺路线1",
        "text": "以氯甲基吡啶起始。",
        "rows": None,
        "state": status.STATUS_OK,
        "reason": None,
        "confidence": 0.8,
        "evidence": [{"file_id": "m1", "page": 3, "quote": "以氯甲基吡啶起始"}],
        "candidates": ["候选A"],
    }
    base.update(overrides)
    return DocGenSlotValue(**base)


def test_results_from_rows_restores_evidence_and_candidates() -> None:
    """依据、候选值、置信度都必须原样还原（生成说明靠它们追溯出处）。"""
    result = pipeline._results_from_rows([_row()])["route_1"]
    assert result.text == "以氯甲基吡啶起始。"
    assert result.state == status.STATUS_OK
    assert result.confidence == 0.8
    assert result.candidates == ["候选A"]
    assert [item.file_id for item in result.evidence] == ["m1"]
    assert result.evidence[0].quote == "以氯甲基吡啶起始"


def test_results_from_rows_handles_null_columns_and_table_rows() -> None:
    """可空列（text/rows/reason/evidence/candidates）不得因为 None 而炸掉。"""
    rows = [
        _row(
            slot_key="empty",
            text=None,
            reason="材料未提供",
            state=status.STATUS_PENDING,
            evidence=None,
            candidates=None,
            confidence=None,
        ),
        _row(slot_key="material_cost_rows", text=None, rows=[{"material": "A", "usage": "1"}]),
    ]
    results = pipeline._results_from_rows(rows)
    assert results["empty"].text == ""
    assert results["empty"].reason == "材料未提供"
    assert results["empty"].evidence == []
    assert results["empty"].candidates == []
    assert results["material_cost_rows"].rows == [{"material": "A", "usage": "1"}]


def test_status_vocabulary_covers_review_flow() -> None:
    """状态词表必须包含两阶段流转用到的 awaiting_review / confirmed。"""
    assert "awaiting_review" in JOB_STATUS_VALUES
    assert "confirmed" in JOB_STATUS_VALUES
