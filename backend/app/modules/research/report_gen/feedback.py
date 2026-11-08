"""评审修改意见：把「上一版哪里不对」变成下一轮生成的明确指令。

为什么拼进 ``supplement_text`` 而不是新造一个提示词变量：补充说明已经是 Agent 读人工
指令的唯一入口（``agent.py`` 的 user prompt 里直接引用），意见走同一条路就不必改提示词，
也就不会让提示词指纹随数据漂移。

生命周期只有三态：``open`` 待落实 → ``applied`` 被某次重生成带走，或 ``ignored`` 人工判定
不采纳。未落实的意见会一直挂在报告上，下次生成继续带上，直到有人处理掉。
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.research.models import RdReportGenFeedback

logger = logging.getLogger(__name__)

# 一次带入的条数与单条长度上限：意见是「必须落实的清单」，太多会把正文任务淹掉
MAX_FEEDBACK_ITEMS = 10
MAX_FEEDBACK_CHARS = 500

_HEADER = "【上一版评审意见（逐条落实；确实无法落实的，在缺口说明里写明原因）】"


async def list_open(session: AsyncSession, report_id: UUID) -> list[RdReportGenFeedback]:
    """取该报告下所有待落实意见，先提的先带入（评审通常是按顺序看的）。"""
    result = await session.execute(
        select(RdReportGenFeedback)
        .where(
            RdReportGenFeedback.report_id == report_id,
            RdReportGenFeedback.status == "open",
            RdReportGenFeedback.is_deleted.is_(False),
        )
        .order_by(RdReportGenFeedback.created_at.asc())
        .limit(MAX_FEEDBACK_ITEMS)
    )
    return list(result.scalars().all())


def merge_supplement(base: str | None, items: list[RdReportGenFeedback]) -> str:
    """把待落实意见拼到补充说明后面；没有意见时原样返回。"""
    base_text = (base or "").strip()
    if not items:
        return base_text
    lines = [_HEADER]
    for index, item in enumerate(items, start=1):
        scope = f"槽位 {item.slot_key}" if item.slot_key else "整篇"
        content = " ".join((item.content or "").split())
        if len(content) > MAX_FEEDBACK_CHARS:
            content = content[:MAX_FEEDBACK_CHARS] + "…"
        lines.append(f"{index}. [{scope}] {content}")
    body = "\n".join(lines)
    return f"{base_text}\n\n{body}" if base_text else body


async def mark_applied(session: AsyncSession, items: list[RdReportGenFeedback], job_id: UUID) -> int:
    """新任务接手这批意见：标记已落实并记住是哪次生成落实的。"""
    if not items:
        return 0
    for item in items:
        item.status = "applied"
        item.applied_job_id = job_id
    await session.flush()
    logger.info(
        "report-gen feedback applied",
        extra={"job_id": str(job_id), "feedback_count": len(items)},
    )
    return len(items)


__all__ = ["MAX_FEEDBACK_CHARS", "MAX_FEEDBACK_ITEMS", "list_open", "mark_applied", "merge_supplement"]
