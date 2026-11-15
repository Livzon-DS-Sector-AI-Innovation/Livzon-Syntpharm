"""槽位 ORM 行 → 渲染入参的映射。

Agent 首次出稿与「按写入记录重渲染」都要把 ``RdReportGenSlot`` 转成 ``SlotFill``；
放在这里只写一份，槽位字段一改就只改这一处，避免两条出稿路径的映射悄悄跑偏。

一个写入记录可能对应多个落点（历史数据里同一字段在正文与表格各出现一次，合并成一行管理）：
行里以 ``anchor["anchors"]`` 记录全部落点，这里按落点展开成多条 ``SlotFill``——
``render_document`` 本来就是逐条定位，展开后自然写满每一处，且不额外建槽位行
（否则同一件事会被写两遍、引用源也会重复计数）。
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.modules.research.models import RdReportGenSlot
from app.modules.research.report_gen.render import SlotFill


def _row_anchors(anchor: dict[str, Any] | None) -> list[dict[str, Any]]:
    """行里记录的落点；没有多落点信息时就是主锚点本身。"""
    data = anchor if isinstance(anchor, dict) else {}
    extra = [dict(item) for item in (data.get("anchors") or []) if isinstance(item, dict) and item]
    return extra or ([dict(data)] if data else [])


def slot_fill(row: RdReportGenSlot) -> SlotFill:
    """单行转 SlotFill：锚点里的 location 优先取显式字段，回落到 anchor 字典。"""
    return SlotFill(
        slot_key=row.slot_key,
        label=row.slot_label,
        anchor=row.anchor,
        location=str((row.anchor or {}).get("location") or "") or None,
        value=row.value,
        state=row.state,
        source_name=row.source_name,
        evidence=row.evidence,
        owner_hint=row.owner_hint,
    )


def build_fills(rows: Iterable[RdReportGenSlot]) -> list[SlotFill]:
    """批量转换并按落点展开；顺序沿用传入顺序（同一槽位的多个落点连续排布）。"""
    fills: list[SlotFill] = []
    for row in rows:
        base = slot_fill(row)
        anchors = _row_anchors(row.anchor)
        if len(anchors) <= 1:
            fills.append(base)
            continue
        for anchor in anchors:
            fills.append(
                SlotFill(
                    slot_key=base.slot_key,
                    label=base.label,
                    anchor=anchor,
                    location=base.location,
                    value=base.value,
                    state=base.state,
                    source_name=base.source_name,
                    evidence=base.evidence,
                    owner_hint=base.owner_hint,
                )
            )
    return fills


__all__ = ["build_fills", "slot_fill"]
