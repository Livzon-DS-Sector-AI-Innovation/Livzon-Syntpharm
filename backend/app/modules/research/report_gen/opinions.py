"""全局意见库：把每次评审意见沉淀成可复用的写作要求，并在生成前汇总。

为什么不直接把 ``rd_report_gen_feedback`` 全塞进提示词：那张表按报告/任务散放，
同一类问题（「结果与讨论缺工艺参数与收率的因果关系」）会在几十份报告里重复出现，
几十条近似句子一起塞进去既稀释重点又容易互相矛盾。这里按归一化文本归并、累计
提出次数，生成前再让模型把「次数最高的一批」压成一段可执行的写作要求。

汇总失败必须降级而不是阻断生成：意见是增益项，报告能出稿优先级更高。
"""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm import llm_client
from app.modules.research.models import (
    RdReportGenFeedback,
    RdReportGenJob,
    RdReportGenOpinion,
    RdReportGenOpinionDigest,
)
from app.modules.research.report_gen.config import ReportGenConfig

logger = logging.getLogger(__name__)

# 汇总输入上限：条数太多时模型会把要求写成流水账，反而丢掉重点
DEFAULT_MAX_ITEMS = 40
# 汇总输出上限：system prompt 里这一段是「约束」，不是正文，太长会挤占写作任务
DIGEST_MAX_CHARS = 1200
# 降级时逐条列出的条数
FALLBACK_ITEMS = 10
# 模型生成的汇总最长接受多少字（超出截断，避免异常模型把整篇报告吐回来）
_DIGEST_ACCEPT_CHARS = 4000

_TRAILING = "。；;，,、!！?？ \t\n"


def normalize(content: str | None) -> str:
    """归一化：全半角统一、空白压缩、去首尾标点。"""
    text = unicodedata.normalize("NFKC", content or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text.strip(_TRAILING)


def normalized_key(content: str | None) -> str:
    """相同/近似写法的归并键：再小写化，避免英文大小写制造重复条目。"""
    return hashlib.sha256(normalize(content).casefold().encode("utf-8")).hexdigest()


@dataclass(slots=True)
class DigestResult:
    """一次汇总的产物：是否走了降级、收了几条意见。"""

    digest: RdReportGenOpinionDigest
    reused: bool = False


async def record_feedback(
    session: AsyncSession,
    feedback: RdReportGenFeedback,
    user_id: UUID | None,
) -> RdReportGenOpinion | None:
    """把一条原始意见归入意见库：命中则累计次数，未命中则新建。

    独立 savepoint：意见库写失败不能把「意见本身」一起回滚——用户提的意见必须留下，
    库只是增益。
    """
    content = normalize(feedback.content)
    if not content:
        return None
    key = normalized_key(content)
    # created_at 是 server_default：极端情况下 flush 后仍为空，别把 last_seen_at 写成 NULL
    seen_at = getattr(feedback, "created_at", None) or datetime.now(UTC)
    try:
        async with session.begin_nested():
            opinion = (
                await session.execute(
                    select(RdReportGenOpinion).where(RdReportGenOpinion.normalized_key == key)
                )
            ).scalars().first()
            if opinion is None:
                opinion = RdReportGenOpinion(
                    content=content,
                    normalized_key=key,
                    hit_count=1,
                    status="active",
                    last_feedback_id=feedback.id,
                    last_seen_at=seen_at,
                    created_by=user_id,
                    updated_by=user_id,
                )
                session.add(opinion)
            elif opinion.status == "active":
                # 停用的保持停用：人工判断「这条不该再影响生成」不能被后续同类意见推翻
                opinion.hit_count = int(opinion.hit_count or 0) + 1
                opinion.last_feedback_id = feedback.id
                opinion.last_seen_at = seen_at
                opinion.updated_by = user_id
            else:
                opinion.last_feedback_id = feedback.id
                opinion.last_seen_at = seen_at
            await session.flush()
        return opinion
    except Exception:  # noqa: BLE001 - 归库失败不影响意见落库
        logger.warning(
            "report-gen opinion record failed",
            exc_info=True,
            extra={"job_id": str(feedback.job_id), "biz_module": "research"},
        )
        return None


async def list_library(
    session: AsyncSession,
    *,
    status: str | None = None,
    keyword: str | None = None,
    limit: int = 200,
) -> list[RdReportGenOpinion]:
    """意见库列表：次数高的在前，便于人先处置最普遍的要求。"""
    statement = select(RdReportGenOpinion).where(RdReportGenOpinion.is_deleted.is_(False))
    if status in ("active", "disabled"):
        statement = statement.where(RdReportGenOpinion.status == status)
    text = normalize(keyword)
    if text:
        statement = statement.where(RdReportGenOpinion.content.ilike(f"%{text}%"))
    statement = statement.order_by(
        RdReportGenOpinion.hit_count.desc(), RdReportGenOpinion.updated_at.desc()
    ).limit(limit)
    return list((await session.execute(statement)).scalars().all())


async def set_status(
    session: AsyncSession,
    opinion_id: UUID,
    status: str,
    user_id: UUID | None,
) -> RdReportGenOpinion | None:
    row = await session.get(RdReportGenOpinion, opinion_id)
    if row is None or row.is_deleted:
        return None
    row.status = status
    row.updated_by = user_id
    await session.commit()
    await session.refresh(row)
    return row


async def list_digests(session: AsyncSession, *, limit: int = 20) -> list[RdReportGenOpinionDigest]:
    result = await session.execute(
        select(RdReportGenOpinionDigest)
        .where(RdReportGenOpinionDigest.is_deleted.is_(False))
        .order_by(RdReportGenOpinionDigest.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


def _source_hash(ids: list[UUID]) -> str:
    joined = ",".join(sorted(str(item) for item in ids))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _items_text(opinions: list[RdReportGenOpinion]) -> str:
    return "\n".join(
        f"{index}.（{int(item.hit_count or 1)} 次）{normalize(item.content)}"
        for index, item in enumerate(opinions, start=1)
    )


def _fallback_text(opinions: list[RdReportGenOpinion]) -> str:
    return "\n".join(
        f"{index}. {normalize(item.content)}"
        for index, item in enumerate(opinions[:FALLBACK_ITEMS], start=1)
    )


async def build_digest(
    session: AsyncSession,
    job: RdReportGenJob,
    config: ReportGenConfig,
) -> DigestResult | None:
    """生成前的意见汇总：返回快照行并把任务指向它；意见库为空返回 None。

    相同意见集合复用上一份汇总：集合没变时再调一次模型只会得到措辞不同的同一段话，
    白花一次调用还让「这次按哪份要求写的」变得不可复现。
    """
    if not config.opinion_digest_enabled:
        return None

    opinions = list(
        (
            await session.execute(
                select(RdReportGenOpinion)
                .where(
                    RdReportGenOpinion.status == "active",
                    RdReportGenOpinion.is_deleted.is_(False),
                )
                .order_by(
                    RdReportGenOpinion.hit_count.desc(),
                    func.coalesce(RdReportGenOpinion.last_seen_at, RdReportGenOpinion.created_at).desc(),
                )
                .limit(config.opinion_max_items)
            )
        )
        .scalars()
        .all()
    )
    if not opinions:
        return None

    source_hash = _source_hash([item.id for item in opinions])
    existing = (
        await session.execute(
            select(RdReportGenOpinionDigest)
            .where(
                RdReportGenOpinionDigest.source_hash == source_hash,
                RdReportGenOpinionDigest.is_deleted.is_(False),
            )
            .order_by(RdReportGenOpinionDigest.created_at.desc())
            .limit(1)
        )
    ).scalars().first()
    if existing is not None:
        job.opinion_digest_id = existing.id
        await session.flush()
        return DigestResult(digest=existing, reused=True)

    prompt = config.opinion_digest_prompt.format(items=_items_text(opinions))
    status = "ok"
    model_name: str | None = config.model.display
    try:
        text = await llm_client.chat(
            [{"role": "user", "content": prompt}],
            response_format=None,
            temperature=0.0,
            max_tokens=1200,
            **config.model.call_kwargs(),
        )
        digest_text = (text or "").strip()[:_DIGEST_ACCEPT_CHARS]
        if not digest_text:
            raise ValueError("汇总结果为空")
    except Exception:  # noqa: BLE001 - 汇总失败必须降级，不能挡住出稿
        logger.warning(
            "report-gen opinion digest fallback",
            exc_info=True,
            extra={"job_id": str(job.id), "biz_module": "research"},
        )
        status = "fallback"
        model_name = None
        digest_text = _fallback_text(opinions)

    row = RdReportGenOpinionDigest(
        digest_text=digest_text[:DIGEST_MAX_CHARS] if status == "ok" else digest_text,
        item_count=len(opinions),
        opinion_ids=[str(item.id) for item in opinions],
        model_name=model_name,
        status=status,
        source_hash=source_hash,
    )
    session.add(row)
    await session.flush()
    job.opinion_digest_id = row.id
    await session.flush()
    logger.info(
        "report-gen opinion digest built",
        extra={
            "job_id": str(job.id),
            "item_count": len(opinions),
            "digest_status": status,
            "biz_module": "research",
        },
    )
    return DigestResult(digest=row)


__all__ = [
    "DEFAULT_MAX_ITEMS",
    "DIGEST_MAX_CHARS",
    "DigestResult",
    "build_digest",
    "list_digests",
    "list_library",
    "normalize",
    "normalized_key",
    "record_feedback",
    "set_status",
]
