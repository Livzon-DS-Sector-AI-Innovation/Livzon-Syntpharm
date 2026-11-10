"""槽位 ORM 行 → 渲染入参的映射。

Agent 首次出稿与「按当前槽位重新渲染」都要把 ``RdReportGenSlot`` 转成 ``SlotFill``；
放在这里只写一份，槽位字段一改就只改这一处，避免两条出稿路径的映射悄悄跑偏。
"""

from __future__ import annotations

from collections.abc import Iterable

from app.modules.research.models import RdReportGenSlot
from app.modules.research.report_gen.render import SlotFill


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
    """批量转换；顺序沿用传入顺序（调用方按 slot_key 排序后传入可保证出稿稳定）。"""
    return [slot_fill(row) for row in rows]


__all__ = ["build_fills", "slot_fill"]
