"""槽位示例库：把人工修正沉淀成下次生成的 few-shot 参照。

为什么只收人工修正：模型自己填的东西本来就可能是错的，拿它当示例会把错误固化下来；
人工在详情页改过的值才有「正确答案」的资格。

注入方式刻意放在 ``read_template_outline`` 的返回里（每个槽位带一个 ``example``），
不动 system prompt：示例属于任务数据，塞进 system 会让提示词指纹随数据漂移，反而看不出
「提示词改没改」。
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.research.models import RdReportGenExample

logger = logging.getLogger(__name__)

# 注入前截断：示例只是一句写法参考，整段原文会把上下文挤爆
_EXAMPLE_VALUE_MAX = 400
_EXAMPLE_EVIDENCE_MAX = 200


def _clip(text: str | None, limit: int) -> str:
    value = (text or "").strip()
    return value if len(value) <= limit else value[:limit] + "…"


async def load_examples(
    session: AsyncSession,
    template_id: UUID | None,
    *,
    limit: int,
    exclude_keys: set[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """取该模板可用的示例，按「最近被人工改过」优先，最多 ``limit`` 条。

    上限按条数而非按槽位算：大模板动辄两百个槽位，全量下发会把工具返回撑爆；
    取最近修正的那批，实际效果等价于「先学最近改过的写法」。
    """
    if template_id is None or limit <= 0:
        return {}
    statement = (
        select(RdReportGenExample)
        .where(
            RdReportGenExample.template_id == template_id,
            RdReportGenExample.is_active.is_(True),
            RdReportGenExample.is_deleted.is_(False),
        )
        .order_by(RdReportGenExample.updated_at.desc())
        .limit(limit)
    )
    rows = list((await session.execute(statement)).scalars().all())
    if not rows:
        return {}
    excluded = exclude_keys or set()
    examples: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.slot_key in excluded:
            continue
        examples[row.slot_key] = {
            "value": _clip(row.value, _EXAMPLE_VALUE_MAX),
            "evidence": _clip(row.evidence_text, _EXAMPLE_EVIDENCE_MAX),
        }
        row.usage_count = int(row.usage_count or 0) + 1
    if not examples:
        return {}
    await session.flush()
    logger.info(
        "report-gen examples injected",
        extra={"template_id": str(template_id), "example_count": len(examples)},
    )
    return examples


async def load_all_examples(session: AsyncSession, template_id: UUID | None) -> dict[str, str]:
    """只读取该模板全部启用的示例写法（``slot_key -> value``）。

    与 :func:`load_examples` 分开是有意的：那个用于生成链路的 few-shot 注入，
    会累计 ``usage_count`` 并按条数截断；填充示例稿只是把示例「显示」到对应位置，
    既不该影响使用统计，也不该被 ``limit`` 截掉。
    """
    if template_id is None:
        return {}
    statement = select(RdReportGenExample.slot_key, RdReportGenExample.value).where(
        RdReportGenExample.template_id == template_id,
        RdReportGenExample.is_active.is_(True),
        RdReportGenExample.is_deleted.is_(False),
    )
    rows = (await session.execute(statement)).all()
    examples: dict[str, str] = {}
    for slot_key, value in rows:
        cleaned = (value or "").strip()
        if slot_key and cleaned:
            examples.setdefault(slot_key, cleaned)
    return examples


async def record_manual_example(
    session: AsyncSession,
    *,
    template_id: UUID | None,
    slot_key: str,
    slot_label: str,
    value: str | None,
    evidence: str | None = None,
    query_text: str | None = None,
    source: str = "manual_edit",
) -> bool:
    """人工保存槽位后同步示例库；返回是否发生了变更。

    人工把值清空（判定该槽位其实不该有内容）时，示例置为停用而不是删除：
    留着历史值便于追查「为什么以前这么填」，但不再拿它教下一次生成。

    ``source`` 记「这条正确答案是怎么来的」：直接改值记 ``manual_edit``，
    由评审意见落实后沉淀的记 ``feedback_promoted``，便于日后追查示例库的构成。
    """
    if template_id is None or not slot_key:
        return False
    result = await session.execute(
        select(RdReportGenExample).where(
            RdReportGenExample.template_id == template_id,
            RdReportGenExample.slot_key == slot_key,
            RdReportGenExample.is_deleted.is_(False),
        )
    )
    existing = result.scalars().first()
    cleaned = (value or "").strip()
    if not cleaned:
        if existing is None or not existing.is_active:
            return False
        existing.is_active = False
        await session.flush()
        return True

    if existing is None:
        session.add(
            RdReportGenExample(
                template_id=template_id,
                slot_key=slot_key,
                slot_label=slot_label or "",
                source=source,
                value=cleaned,
                evidence_text=(evidence or "").strip() or None,
                query_text=(query_text or "").strip() or None,
                usage_count=0,
                is_active=True,
            )
        )
        await session.flush()
        return True

    # 证据是可选的：人工只改值不给证据时保留旧证据，不能当成一次变更
    new_evidence = (evidence or "").strip()
    changed = existing.value != cleaned or not existing.is_active
    existing.value = cleaned
    existing.slot_label = slot_label or existing.slot_label
    existing.source = source
    if new_evidence:
        existing.evidence_text = new_evidence
    existing.is_active = True
    if changed:
        await session.flush()
    return changed


__all__ = ["load_all_examples", "load_examples", "record_manual_example"]
