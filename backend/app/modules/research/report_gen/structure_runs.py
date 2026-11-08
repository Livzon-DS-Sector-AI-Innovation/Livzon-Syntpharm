"""母本结构解析留痕：记录每次真实解析，并给出「AI 选了什么 vs 人改了什么」。

没有留痕时，「这次解析漏选了几个」只能靠人回忆；有了留痕，漏选/多选就是两个集合差：
- 漏选（added）：当前启用但解析当时没选的槽位 —— 人工后补的；
- 多选（removed）：解析当时选了、现在被禁用或删掉的槽位 —— 人工否掉的。

注意这里比的是「解析当时的选择」和「现在的结构」，跨了多次人工编辑时两者会混在一起，
所以统计只当作趋势看，不做精确归因。
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.research.models import RdReportGenStructureRun

logger = logging.getLogger(__name__)

_ERROR_MAX = 500


async def record_structure_run(
    session: AsyncSession,
    *,
    template_id: UUID,
    source_key: str | None,
    prompt_version: str,
    model_name: str | None,
    candidate_count: int,
    slot_keys: list[str],
    duration_ms: int,
    status: str = "ok",
    error: str | None = None,
) -> None:
    """落一条解析留痕。写失败只记日志，不影响解析结果。"""
    try:
        session.add(
            RdReportGenStructureRun(
                template_id=template_id,
                source_key=(source_key or None) and source_key[:500],
                prompt_version=prompt_version,
                model_name=model_name,
                candidate_count=candidate_count,
                slot_count=len(slot_keys),
                slot_keys=list(slot_keys),
                duration_ms=max(duration_ms, 0),
                status=status,
                error=(error or "")[:_ERROR_MAX] or None,
            )
        )
        await session.flush()
    except SQLAlchemyError:
        logger.exception("report-gen structure run record failed", extra={"template_id": str(template_id)})


def summarize_edit(ai_keys: list[str] | None, slots: list[dict[str, Any]]) -> dict[str, Any]:
    """对比「解析当时的槽位集合」与「当前结构」，算漏选/多选。

    只看启用状态：人工把槽位停用等于否掉（算多选），重新启用等于要回来（算保留）。
    """
    ai = [str(key) for key in (ai_keys or [])]
    enabled = {str(slot.get("slot_key") or "") for slot in slots if slot.get("is_enabled", True)}
    ai_set = set(ai)
    added = sorted(enabled - ai_set)
    removed = sorted(ai_set - enabled)
    return {
        "ai_slot_count": len(ai),
        "current_slot_count": len(slots),
        "kept_count": len(ai_set & enabled),
        "missing_count": len(added),
        "extra_count": len(removed),
        "missing_keys": added[:10],
        "extra_keys": removed[:10],
    }


async def list_structure_runs(
    session: AsyncSession,
    template_id: UUID,
    *,
    current_slots: list[dict[str, Any]],
    limit: int = 10,
) -> list[dict[str, Any]]:
    """最近的解析留痕，附上与当前结构的差异（最新一条在最前）。"""
    rows = list(
        (
            await session.execute(
                select(RdReportGenStructureRun)
                .where(
                    RdReportGenStructureRun.template_id == template_id,
                    RdReportGenStructureRun.is_deleted.is_(False),
                )
                .order_by(RdReportGenStructureRun.created_at.desc())
                .limit(max(1, min(limit, 50)))
            )
        )
        .scalars()
        .all()
    )
    items: list[dict[str, Any]] = []
    for row in rows:
        items.append(
            {
                "id": str(row.id),
                "source_key": row.source_key,
                "prompt_version": row.prompt_version,
                "model_name": row.model_name,
                "candidate_count": row.candidate_count,
                "slot_count": row.slot_count,
                "duration_ms": row.duration_ms,
                "status": row.status,
                "error": row.error,
                "created_at": row.created_at,
                "diff": summarize_edit(row.slot_keys, current_slots),
            }
        )
    return items


__all__ = ["list_structure_runs", "record_structure_run", "summarize_edit"]
