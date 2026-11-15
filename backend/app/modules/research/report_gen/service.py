"""AI 报告生成的任务状态机与查询。

职责边界：本层只管「任务怎么建、怎么查、怎么改」，真正跑 Agent 的是
``agent.run_report_gen``，由 ``app/core/jobs.py`` 调度（一次性异步任务的唯一出口）。
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.core.jobs import submit_job_safe
from app.core.llm import llm_client
from app.core.llm.config import get_active_config, get_env_config
from app.modules.research.doc_template import store
from app.modules.research.models import (
    RdDeliverableTemplate,
    RdReport,
    RdReportGenEdit,
    RdReportGenFeedback,
    RdReportGenJob,
    RdReportGenOpinion,
    RdReportGenOpinionDigest,
    RdReportGenSlot,
    RdReportGenStep,
)
from app.modules.research.report_gen import editor as report_editor
from app.modules.research.report_gen import opinions, review, versions
from app.modules.research.report_gen.agent import run_report_gen
from app.modules.research.report_gen.config import load_config
from app.modules.research.report_gen.feedback import list_open as _list_open_feedback
from app.modules.research.report_gen.feedback import mark_applied as _mark_feedback_applied
from app.modules.research.report_gen.feedback import merge_supplement as _merge_feedback
from app.modules.research.report_gen.feedback import strip_merged as _strip_feedback_text
from app.modules.research.report_gen.outline import build_outline
from app.modules.research.report_gen.prompts_version import agent_prompt_version
from app.modules.research.report_gen.schemas import (
    ReportGenEditRejection,
    ReportGenEditRemoval,
    ReportGenEditRequest,
    ReportGenEditResultData,
    ReportGenFeedbackBrief,
    ReportGenFeedbackCreateRequest,
    ReportGenFeedbackData,
    ReportGenFeedbackListData,
    ReportGenFeedbackSlotStat,
    ReportGenFeedbackUpdateRequest,
    ReportGenJobCreateRequest,
    ReportGenJobData,
    ReportGenJobListData,
    ReportGenMetricsData,
    ReportGenModelTestData,
    ReportGenOpinionData,
    ReportGenOpinionDigestBrief,
    ReportGenOpinionDigestData,
    ReportGenOpinionDigestListData,
    ReportGenOpinionListData,
    ReportGenOpinionUpdateRequest,
    ReportGenRenderData,
    ReportGenStepData,
    ReportGenStepListData,
)
from app.modules.research.report_gen.structure import open_document
from app.modules.research.report_gen.template_access import load_template_bytes

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = ("queued", "running")
TERMINAL_STATUSES = ("completed", "failed", "cancelled")
DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _now() -> datetime:
    return datetime.now(UTC)


async def _effective_model_name(display: str | None) -> str | None:
    """档位留空时记录实际生效的默认模型名，详情页才不会显示成「未记录」。"""
    if display:
        return display
    try:
        fallback = await get_active_config("text") or get_env_config()
    except Exception:  # noqa: BLE001 - 仅展示字段，取不到不影响建任务
        logger.warning("report-gen default model lookup failed", exc_info=True)
        return None
    return fallback.model_name if fallback else None


def _digest_brief(row: RdReportGenOpinionDigest) -> ReportGenOpinionDigestBrief:
    return ReportGenOpinionDigestBrief(
        id=row.id,
        item_count=row.item_count,
        status=row.status,
        digest_preview=(row.digest_text or "")[:300],
        model_name=row.model_name,
        created_at=row.created_at,
    )


async def _digest_briefs(
    session: AsyncSession, digest_ids: list[UUID | None]
) -> dict[UUID, ReportGenOpinionDigestBrief]:
    """批量取汇总摘要：列表页一次查完，避免逐任务 N+1。"""
    unique = [item for item in dict.fromkeys(digest_ids) if item is not None]
    if not unique:
        return {}
    rows = await session.execute(
        select(RdReportGenOpinionDigest).where(RdReportGenOpinionDigest.id.in_(unique))
    )
    return {row.id: _digest_brief(row) for row in rows.scalars().all()}


def _to_job_data(
    job: RdReportGenJob,
    report_title: str | None = None,
    feedback_applied: list[ReportGenFeedbackBrief] | None = None,
    opinion_digest: ReportGenOpinionDigestBrief | None = None,
) -> ReportGenJobData:
    return ReportGenJobData(
        id=job.id,
        report_id=job.report_id,
        project_id=job.project_id,
        report_title=report_title,
        template_file_name=job.template_file_name,
        deliverable_template_id=job.deliverable_template_id,
        status=job.status,
        progress=job.progress,
        current_step=job.current_step,
        error_message=job.error_message,
        doc_code=job.doc_code,
        drug_name=job.drug_name,
        supplement_text=job.supplement_text,
        feedback_applied=feedback_applied or [],
        opinion_digest=opinion_digest,
        document_file_name=job.document_file_name,
        slot_total=job.slot_total,
        slot_filled=job.slot_filled,
        slot_gap=job.slot_gap,
        rounds=job.rounds,
        tool_mode=job.tool_mode,
        model_config_name=job.model_config_name,
        model_name=job.model_name,
        structure_model_name=job.structure_model_name,
        fallback_model_name=job.fallback_model_name,
        used_fallback=job.used_fallback,
        can_cancel=job.status in ACTIVE_STATUSES,
        has_document=bool(job.document_object_key),
        started_at=job.started_at,
        finished_at=job.finished_at,
        created_at=job.created_at,
    )


async def _titles(session: AsyncSession, report_ids: list[UUID]) -> dict[UUID, str]:
    """批量取报告标题：列表页避免 N+1。"""
    unique = [rid for rid in dict.fromkeys(report_ids)]
    if not unique:
        return {}
    result = await session.execute(select(RdReport.id, RdReport.title).where(RdReport.id.in_(unique)))
    return {row[0]: row[1] for row in result.all()}


def _carried_value(row: RdReportGenSlot) -> bool:
    return bool((row.value or "").strip())


def _manual_anchor(row: RdReportGenSlot) -> dict[str, Any]:
    return row.anchor if isinstance(row.anchor, dict) else {}


async def _carry_over_manual_slots(
    session: AsyncSession,
    job: RdReportGenJob,
    template: RdDeliverableTemplate,
    user_id: UUID | None,
) -> int:
    """把上一版人工确认过的内容带进新任务。

    为什么在新任务里预置槽位行、而不是只写进提示词：预置行是「事实」——渲染直接按它
    回放，AI 写入工具也会因为这些 key 已存在而拒写；只写提示词则模型仍可能覆盖。
    母本换版后按指纹校验，定位不到的一律跳过（写错位置比少写更糟）。
    """
    previous = (
        await session.execute(
            select(RdReportGenJob)
            .where(
                RdReportGenJob.report_id == job.report_id,
                RdReportGenJob.deliverable_template_id == job.deliverable_template_id,
                RdReportGenJob.status == "completed",
                RdReportGenJob.id != job.id,
                RdReportGenJob.is_deleted.is_(False),
            )
            .order_by(RdReportGenJob.created_at.desc())
            .limit(1)
        )
    ).scalars().first()
    if previous is None:
        return 0

    rows = (
        await session.execute(
            select(RdReportGenSlot)
            .where(
                RdReportGenSlot.job_id == previous.id,
                RdReportGenSlot.edit_source == "manual",
                RdReportGenSlot.is_deleted.is_(False),
            )
            .order_by(RdReportGenSlot.created_at.asc())
        )
    ).scalars().all()
    manual_rows = [row for row in rows if _carried_value(row)]
    if not manual_rows:
        return 0

    try:
        template_bytes = load_template_bytes(job, template)
        outline = build_outline(open_document(template_bytes))
    except Exception:  # noqa: BLE001 - 母本读不到时新任务照常跑，只是不继承人工值
        logger.exception("report-gen carry-over: 母本读取失败", extra={"job_id": str(job.id)})
        return 0

    positions = outline.by_key()
    key_map: dict[str, str] = {}
    carried: list[RdReportGenSlot] = []
    append_seq = 0
    for row in manual_rows:
        key = row.slot_key
        anchor = _manual_anchor(row)

        if key.startswith("ap"):
            after = str(anchor.get("after") or "")
            if after not in positions and after not in key_map:
                logger.info(
                    "report-gen carry-over: 追加段锚点失效，跳过",
                    extra={"job_id": str(job.id), "slot_key": key},
                )
                continue
            append_seq += 1
            new_key = f"ap{append_seq}"
            key_map[key] = new_key
            new_anchor = {
                **anchor,
                "after": key_map.get(after, after),
                "seq": append_seq,
                "location": f"追加段落{append_seq}",
                "human_locked": True,
            }
        elif key.startswith("at"):
            table_index = anchor.get("table_index")
            if not isinstance(table_index, int) or not (0 <= table_index < outline.table_count):
                continue
            append_seq += 1
            new_key = f"at{append_seq}"
            key_map[key] = new_key
            new_anchor = {**anchor, "seq": append_seq, "human_locked": True}
        else:
            position = positions.get(key)
            if position is None:
                continue
            stored_fp = anchor.get("fingerprint")
            stored_text = str(anchor.get("text") or "").strip()
            # 有指纹比指纹；老数据没有指纹时退回比原文。都对不上说明母本换版，跳过
            if (stored_fp and stored_fp != position.fingerprint) or (
                not stored_fp and stored_text != position.text.strip()
            ):
                logger.info(
                    "report-gen carry-over: 母本已换版，跳过",
                    extra={"job_id": str(job.id), "slot_key": key},
                )
                continue
            new_key = key
            new_anchor = {**anchor, "human_locked": True}

        carried.append(
            RdReportGenSlot(
                job_id=job.id,
                slot_key=new_key,
                slot_label=row.slot_label,
                anchor=new_anchor,
                value=row.value,
                state="filled",
                source_name=row.source_name,
                evidence=row.evidence,
                confidence=row.confidence,
                edit_source="manual",
                edited_at=_now(),
                created_by=user_id,
                updated_by=user_id,
            )
        )

    for item in carried:
        session.add(item)
    await session.flush()
    logger.info(
        "report-gen carry-over applied",
        extra={"job_id": str(job.id), "carried": len(carried), "skipped": len(manual_rows) - len(carried)},
    )
    return len(carried)


async def create_job(
    session: AsyncSession,
    payload: ReportGenJobCreateRequest,
    user_id: UUID | None,
) -> ReportGenJobData:
    """建任务并立刻提交后台执行；同一报告已有进行中的任务时直接复用。"""
    report = await session.get(RdReport, payload.report_id)
    if report is None or report.is_deleted:
        raise NotFoundException("报告")
    if report.project_id != payload.project_id:
        raise BadRequestException("这份报告不属于当前项目，请刷新页面后重试")

    running = await session.execute(
        select(RdReportGenJob)
        .where(
            RdReportGenJob.report_id == payload.report_id,
            RdReportGenJob.status.in_(ACTIVE_STATUSES),
            RdReportGenJob.is_deleted.is_(False),
        )
        .order_by(RdReportGenJob.created_at.desc())
        .limit(1)
    )
    existing = running.scalars().first()
    if existing is not None:
        return _to_job_data(existing, report.title)

    template = await session.get(RdDeliverableTemplate, payload.deliverable_template_id)
    if template is None or template.is_deleted:
        raise NotFoundException("模板")
    if not template.file_object_key:
        raise BadRequestException("这个模板还没有上传 Word 文件，没法生成报告。请先给模板上传文件")

    # 模型快照：任务发起时固定三档原值，执行期间改配置不影响本任务
    config = await load_config()

    # 未落实的评审意见跟着这次生成一起走：读失败只记日志，不能因此挡住生成
    try:
        pending_feedback = await _list_open_feedback(session, payload.report_id)
    except Exception:  # noqa: BLE001 - 意见是增益项，读失败不该阻断生成
        logger.exception("report-gen feedback load failed", extra={"report_id": str(payload.report_id)})
        pending_feedback = []

    job = RdReportGenJob(
        report_id=payload.report_id,
        project_id=payload.project_id,
        deliverable_template_id=template.id,
        template_file_key=template.file_object_key,
        template_file_name=template.file_name,
        model_config_name=config.model.raw,
        model_name=await _effective_model_name(config.model.display),
        fallback_model_name=config.fallback_model.raw,
        status="queued",
        progress=0,
        current_step="排队中",
        doc_code=payload.doc_code,
        drug_name=payload.drug_name,
        supplement_text=_merge_feedback(_strip_feedback_text(payload.supplement_text), pending_feedback),
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(job)
    await session.flush()
    carried = 0
    try:
        # 上一版人工确认的内容先落成本任务的槽位行：渲染与 AI 写入都以它为准
        carried = await _carry_over_manual_slots(session, job, template, user_id)
    except Exception:  # noqa: BLE001 - 继承失败只影响连续性，不能挡住新任务
        logger.exception("report-gen carry-over failed", extra={"job_id": str(job.id)})
    if pending_feedback:
        try:
            await _mark_feedback_applied(session, pending_feedback, job.id)
        except Exception:  # noqa: BLE001 - 标记失败只影响留痕，任务照常执行
            logger.exception("report-gen feedback mark failed", extra={"job_id": str(job.id)})
    await session.commit()
    await session.refresh(job)

    async def _runner(_core_job_id: UUID) -> dict[str, Any]:
        return await run_report_gen(job.id)

    submitted = await submit_job_safe("research.report-gen", _runner)
    if submitted is None:
        # 登记失败：任务不会被执行，直接落失败态，避免列表里永远「排队中」
        job.status = "failed"
        job.error_message = "系统正忙，这次没能开始生成。请过一会儿再点一次「用 AI 生成文档」"
        job.finished_at = _now()
        await session.commit()
        logger.error("report-gen job submit failed", extra={"job_id": str(job.id)})

    logger.info(
        "report-gen job created",
        extra={
            "job_id": str(job.id),
            "report_id": str(payload.report_id),
            "template_id": str(template.id),
            "carried_manual": carried,
            "biz_module": "research",
        },
    )
    applied = [
        ReportGenFeedbackBrief(id=item.id, slot_key=item.slot_key, content=item.content) for item in pending_feedback
    ]
    return _to_job_data(job, report.title, applied)


async def list_jobs(
    session: AsyncSession,
    *,
    project_id: UUID | None = None,
    report_id: UUID | None = None,
    limit: int = 100,
) -> ReportGenJobListData:
    """按项目/报告取任务；列表页一次取回，避免逐报告请求。"""
    statement = select(RdReportGenJob).where(RdReportGenJob.is_deleted.is_(False))
    if project_id is not None:
        statement = statement.where(RdReportGenJob.project_id == project_id)
    if report_id is not None:
        statement = statement.where(RdReportGenJob.report_id == report_id)
    result = await session.execute(statement.order_by(RdReportGenJob.created_at.desc()).limit(min(limit, 200)))
    jobs = list(result.scalars().all())
    titles = await _titles(session, [job.report_id for job in jobs])
    digests = await _digest_briefs(session, [job.opinion_digest_id for job in jobs])
    return ReportGenJobListData(
        items=[
            _to_job_data(
                job,
                titles.get(job.report_id),
                opinion_digest=digests.get(job.opinion_digest_id) if job.opinion_digest_id else None,
            )
            for job in jobs
        ],
        active_count=sum(1 for job in jobs if job.status in ACTIVE_STATUSES),
    )


async def _applied_feedback(session: AsyncSession, job_id: UUID) -> list[ReportGenFeedbackBrief]:
    """这一版实际带走了哪几条意见：按 ``applied_job_id`` 反查。

    没有这一步，详情页只能看到一整段拼好的 ``supplement_text``，
    分不清哪些是用户自己写的、哪些是系统按上版意见加的。
    """
    result = await session.execute(
        select(RdReportGenFeedback.id, RdReportGenFeedback.slot_key, RdReportGenFeedback.content)
        .where(
            RdReportGenFeedback.applied_job_id == job_id,
            RdReportGenFeedback.is_deleted.is_(False),
        )
        .order_by(RdReportGenFeedback.created_at.asc())
    )
    return [ReportGenFeedbackBrief(id=row[0], slot_key=row[1], content=row[2]) for row in result.all()]


async def get_job(session: AsyncSession, job_id: UUID) -> ReportGenJobData:
    job = await session.get(RdReportGenJob, job_id)
    if job is None or job.is_deleted:
        raise NotFoundException("生成任务")
    titles = await _titles(session, [job.report_id])
    applied = await _applied_feedback(session, job_id)
    digests = await _digest_briefs(session, [job.opinion_digest_id])
    digest = digests.get(job.opinion_digest_id) if job.opinion_digest_id else None
    return _to_job_data(job, titles.get(job.report_id), applied, digest)


async def list_steps(
    session: AsyncSession, job_id: UUID, *, after_seq: int = 0, limit: int = 200
) -> ReportGenStepListData:
    """执行过程按 seq 增量拉取：详情页轮询只取新步骤。"""
    result = await session.execute(
        select(RdReportGenStep)
        .where(
            RdReportGenStep.job_id == job_id,
            RdReportGenStep.is_deleted.is_(False),
            RdReportGenStep.seq > after_seq,
        )
        .order_by(RdReportGenStep.seq.asc())
        .limit(min(max(limit, 1), 500))
    )
    steps = list(result.scalars().all())
    return ReportGenStepListData(
        items=[
            ReportGenStepData(
                id=step.id,
                seq=step.seq,
                kind=step.kind,
                title=step.title,
                tool_name=step.tool_name,
                args_summary=step.args_summary,
                result_summary=step.result_summary,
                status=step.status,
                duration_ms=step.duration_ms,
                created_at=step.created_at,
            )
            for step in steps
        ],
        last_seq=steps[-1].seq if steps else after_seq,
    )


async def cancel_job(session: AsyncSession, job_id: UUID, user_id: UUID | None) -> ReportGenJobData:
    job = await session.get(RdReportGenJob, job_id)
    if job is None or job.is_deleted:
        raise NotFoundException("生成任务")
    if job.status in TERMINAL_STATUSES:
        raise BadRequestException("这次生成已经结束了，不用再停止")

    job.cancel_requested = True
    job.updated_by = user_id
    if job.status == "queued":
        # 还没被 worker 领走：直接落终态，避免迟到的 runner 再跑一遍
        job.status = "cancelled"
        job.current_step = "已取消"
        job.finished_at = _now()
    await session.commit()
    titles = await _titles(session, [job.report_id])
    return _to_job_data(job, titles.get(job.report_id))


async def document_payload(session: AsyncSession, job_id: UUID) -> tuple[str, bytes, str]:
    """成品 docx 的下载/预览字节。"""
    job = await session.get(RdReportGenJob, job_id)
    if job is None or job.is_deleted:
        raise NotFoundException("生成任务")
    if not job.document_object_key:
        raise BadRequestException("这次生成还没出结果，等它跑完再来下载")
    data = store.load_bytes(str(job.document_object_key))
    if data is None:
        raise BadRequestException("生成好的文件找不到了，请重新生成一次")
    return job.document_file_name or "report.docx", data, DOCX_CONTENT_TYPE


_PROBE_TIMEOUT_SECONDS = 20

# 统计窗口上限：超过 90 天样本混杂多轮提示词与模型调整，对比意义不大
_METRICS_MAX_DAYS = 90

# 意见集中在哪些槽位：只给前几个，多了就不是「集中」而是把全部槽位列一遍
_METRICS_FEEDBACK_SLOTS = 5


def _ratio(numerator: int, denominator: int) -> float | None:
    """比率：分母为 0 返回 None，让前端显示占位而不是假的 0%。"""
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


async def agent_metrics(session: AsyncSession, days: int = 30) -> ReportGenMetricsData:
    """配置页「Agent 运行情况」：一次聚合查询算完，不拉明细、不改任何配置。

    口径：
    - 窗口按 ``finished_at`` 落（历史任务该列为空时回退 ``created_at``），只统计已终态任务；
    - 平均轮次/耗时/缺口率/降级率只算 completed，避免失败的半成品拉偏均值；
    - 比率分母为 0 时返回 None，由前端显示占位。
    """
    window = min(max(days, 1), _METRICS_MAX_DAYS)
    since = _now() - timedelta(days=window)
    # 指纹要跟着「当前生效的提示词」走：库里整段覆盖过就按覆盖值算，改一个字即变
    config = await load_config()
    finished = func.coalesce(RdReportGenJob.finished_at, RdReportGenJob.created_at)
    is_completed = RdReportGenJob.status == "completed"
    duration_seconds = func.extract("epoch", RdReportGenJob.finished_at - RdReportGenJob.started_at)

    statement = select(
        func.count().label("total"),
        func.coalesce(func.sum(case((is_completed, 1), else_=0)), 0).label("completed"),
        func.coalesce(func.sum(case((RdReportGenJob.status == "failed", 1), else_=0)), 0).label("failed"),
        func.coalesce(func.sum(case((RdReportGenJob.status == "cancelled", 1), else_=0)), 0).label("cancelled"),
        func.avg(case((is_completed, RdReportGenJob.rounds), else_=None)).label("avg_rounds"),
        func.avg(case((is_completed, duration_seconds), else_=None)).label("avg_duration_seconds"),
        func.coalesce(func.sum(case((is_completed, RdReportGenJob.slot_total), else_=0)), 0).label("slot_total"),
        func.coalesce(func.sum(case((is_completed, RdReportGenJob.slot_gap), else_=0)), 0).label("slot_gap"),
        # 降级只对跑完的任务有意义：失败任务走兜底也说明不了模型质量
        func.coalesce(func.sum(case((is_completed & RdReportGenJob.used_fallback.is_(True), 1), else_=0)), 0).label(
            "fallback_completed"
        ),
    ).where(
        RdReportGenJob.is_deleted.is_(False),
        RdReportGenJob.status.in_(TERMINAL_STATUSES),
        finished >= since,
    )
    row = (await session.execute(statement)).one()

    # 意见按「提出时间」落窗口：它衡量的是人对成品的判断，不跟任务是否在窗口内开跑绑定
    feedback_row = (
        await session.execute(
            select(
                func.count().label("total"),
                func.coalesce(func.sum(case((RdReportGenFeedback.status == "open", 1), else_=0)), 0).label("open"),
                func.coalesce(func.sum(case((RdReportGenFeedback.status == "applied", 1), else_=0)), 0).label(
                    "applied"
                ),
                func.coalesce(func.sum(case((RdReportGenFeedback.status == "ignored", 1), else_=0)), 0).label(
                    "ignored"
                ),
            ).where(
                RdReportGenFeedback.is_deleted.is_(False),
                RdReportGenFeedback.created_at >= since,
            )
        )
    ).one()
    slot_rows = (
        await session.execute(
            select(RdReportGenFeedback.slot_key, func.count().label("slot_count"))
            .where(
                RdReportGenFeedback.is_deleted.is_(False),
                RdReportGenFeedback.created_at >= since,
                RdReportGenFeedback.slot_key.is_not(None),
            )
            .group_by(RdReportGenFeedback.slot_key)
            .order_by(func.count().desc())
            .limit(_METRICS_FEEDBACK_SLOTS)
        )
    ).all()

    total = int(row.total or 0)
    completed = int(row.completed or 0)
    slot_total = int(row.slot_total or 0)
    slot_gap = int(row.slot_gap or 0)
    avg_rounds = row.avg_rounds
    avg_duration = row.avg_duration_seconds
    feedback_applied = int(feedback_row.applied or 0)
    feedback_ignored = int(feedback_row.ignored or 0)

    return ReportGenMetricsData(
        window_days=window,
        total=total,
        completed=completed,
        failed=int(row.failed or 0),
        cancelled=int(row.cancelled or 0),
        success_rate=_ratio(completed, total),
        avg_rounds=None if avg_rounds is None else round(float(avg_rounds), 2),
        avg_duration_seconds=None if avg_duration is None else round(float(avg_duration), 1),
        gap_rate=_ratio(slot_gap, slot_total),
        fallback_rate=_ratio(int(row.fallback_completed or 0), completed),
        feedback_total=int(feedback_row.total or 0),
        feedback_open=int(feedback_row.open or 0),
        feedback_applied=feedback_applied,
        feedback_ignored=feedback_ignored,
        # 分母只算「有人处置过」的意见：还挂着的 open 既不算采纳也不算否决
        feedback_adoption_rate=_ratio(feedback_applied, feedback_applied + feedback_ignored),
        feedback_slot_top=[
            ReportGenFeedbackSlotStat(slot_key=str(item.slot_key), count=int(item.slot_count or 0))
            for item in slot_rows
        ],
        agent_prompt_version=agent_prompt_version(config.agent_prompt),
        generated_at=_now(),
    )


def _to_feedback_data(row: RdReportGenFeedback) -> ReportGenFeedbackData:
    return ReportGenFeedbackData(
        id=str(row.id),
        job_id=str(row.job_id),
        slot_key=row.slot_key,
        content=row.content,
        status=row.status,
        applied_job_id=str(row.applied_job_id) if row.applied_job_id else None,
        created_at=row.created_at,
    )


async def create_feedback(
    session: AsyncSession,
    job_id: UUID,
    payload: ReportGenFeedbackCreateRequest,
    user_id: UUID | None,
) -> ReportGenFeedbackData:
    """对某一版报告提一条意见；若指名位置，该位置必须属于这次生成。

    位置清单页面已经下线，前端不再提供选择；保留校验是为了挡住带着旧页面缓存的提交，
    避免落一条谁也定位不到的意见。
    """
    job = await session.get(RdReportGenJob, job_id)
    if job is None or job.is_deleted:
        raise NotFoundException("生成任务")

    slot_key = (payload.slot_key or "").strip() or None
    if slot_key:
        slot_exists = await session.execute(
            select(RdReportGenSlot.id).where(
                RdReportGenSlot.job_id == job_id,
                RdReportGenSlot.slot_key == slot_key,
                RdReportGenSlot.is_deleted.is_(False),
            )
        )
        if slot_exists.first() is None:
            raise BadRequestException("这个位置不属于这次生成，请刷新页面后重试")

    content = " ".join((payload.content or "").split())
    if not content:
        raise BadRequestException("还没有填写意见内容")

    row = RdReportGenFeedback(
        job_id=job_id,
        report_id=job.report_id,
        slot_key=slot_key,
        content=content[:1000],
        status="open",
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(row)
    await session.flush()
    # 每条意见都归入全局意见库：命中同类就累计次数，供生成前汇总使用
    await opinions.record_feedback(session, row, user_id)
    await session.commit()
    await session.refresh(row)
    return _to_feedback_data(row)


async def list_feedback(session: AsyncSession, job_id: UUID) -> ReportGenFeedbackListData:
    """列出该任务上提过的意见；新提的在前，便于评审时先看最近一条。"""
    job = await session.get(RdReportGenJob, job_id)
    if job is None or job.is_deleted:
        raise NotFoundException("生成任务")
    result = await session.execute(
        select(RdReportGenFeedback)
        .where(
            RdReportGenFeedback.job_id == job_id,
            RdReportGenFeedback.is_deleted.is_(False),
        )
        .order_by(RdReportGenFeedback.created_at.desc())
        .limit(100)
    )
    rows = list(result.scalars().all())
    items = [_to_feedback_data(row) for row in rows]
    return ReportGenFeedbackListData(
        total=len(items),
        open_count=sum(1 for row in rows if row.status == "open"),
        items=items,
    )


async def update_feedback(
    session: AsyncSession,
    feedback_id: UUID,
    payload: ReportGenFeedbackUpdateRequest,
    user_id: UUID | None,
) -> ReportGenFeedbackData:
    """人工处置：标不采纳，或把误标不采纳的重新打开（下次生成会再带上）。"""
    row = await session.get(RdReportGenFeedback, feedback_id)
    if row is None or row.is_deleted:
        raise NotFoundException("修改意见")
    row.status = payload.status
    if payload.status == "open":
        row.applied_job_id = None
    row.updated_by = user_id
    await session.commit()
    await session.refresh(row)
    return _to_feedback_data(row)


def _to_opinion_data(row: RdReportGenOpinion) -> ReportGenOpinionData:
    return ReportGenOpinionData(
        id=str(row.id),
        content=row.content,
        hit_count=row.hit_count,
        status=row.status,
        last_seen_at=row.last_seen_at,
        created_at=row.created_at,
    )


async def list_opinions(
    session: AsyncSession,
    *,
    status: str | None = None,
    keyword: str | None = None,
    limit: int = 200,
) -> ReportGenOpinionListData:
    """意见库列表：跨报告归并后的条目，次数高的在前。"""
    rows = await opinions.list_library(session, status=status, keyword=keyword, limit=limit)
    items = [_to_opinion_data(row) for row in rows]
    return ReportGenOpinionListData(
        total=len(items),
        active_count=sum(1 for row in rows if row.status == "active"),
        items=items,
    )


async def update_opinion(
    session: AsyncSession,
    opinion_id: UUID,
    payload: ReportGenOpinionUpdateRequest,
    user_id: UUID | None,
) -> ReportGenOpinionData:
    """人工停用/恢复一条意见：停用后不再进入生成前的汇总。"""
    row = await opinions.set_status(session, opinion_id, payload.status, user_id)
    if row is None:
        raise NotFoundException("意见库条目")
    return _to_opinion_data(row)


async def list_opinion_digests(session: AsyncSession, *, limit: int = 20) -> ReportGenOpinionDigestListData:
    """历史汇总快照：用于回答「某一版当时按哪份写作要求生成」。"""
    rows = await opinions.list_digests(session, limit=limit)
    return ReportGenOpinionDigestListData(
        total=len(rows),
        items=[
            ReportGenOpinionDigestData(
                id=str(row.id),
                item_count=row.item_count,
                status=row.status,
                digest_text=row.digest_text,
                model_name=row.model_name,
                created_at=row.created_at,
            )
            for row in rows
        ],
    )


async def test_model(slot: str) -> ReportGenModelTestData:
    """按档位解析绑定后发一次极短对话，供配置页「测试连通」使用。

    只验证能不能出字：不写库、不改配置、不影响全局活跃模型。失败只回异常类型与
    状态码，响应里不出现端点、上游响应与密钥。
    """
    config = await load_config()
    binding = {"main": config.model, "fallback": config.fallback_model}.get(slot)
    if binding is None:
        return ReportGenModelTestData(ok=False, slot=slot, detail="未知档位")
    if binding.is_empty:
        return ReportGenModelTestData(
            ok=False,
            slot=slot,
            detail="该档位未单独配置，当前沿用全局默认模型，无需测试",
        )

    started = time.perf_counter()
    try:
        await asyncio.wait_for(
            llm_client.chat(
                [{"role": "user", "content": "连通性测试，请只回复 ok"}],
                response_format=None,
                temperature=0.0,
                max_tokens=8,
                **binding.call_kwargs(),
            ),
            timeout=_PROBE_TIMEOUT_SECONDS,
        )
    except Exception as exc:  # noqa: BLE001 - 连通测试需要把任何失败原因回给管理员
        logger.warning(
            "report-gen model probe failed",
            extra={"slot": slot, "model": binding.display, "error": str(exc)[:200]},
        )
        return ReportGenModelTestData(
            ok=False,
            slot=slot,
            model=binding.display,
            latency_ms=_elapsed_ms(started),
            detail=_probe_failure_detail(exc),
        )
    return ReportGenModelTestData(
        ok=True,
        slot=slot,
        model=binding.display,
        latency_ms=_elapsed_ms(started),
        detail="连接正常",
    )


def _probe_failure_detail(exc: Exception) -> str:
    """失败原因只回异常类型与状态码。

    供应商异常文本常带 base_url、上游响应体甚至密钥片段，不能原样回给前端；
    完整信息只进后端日志。
    """
    status = getattr(exc, "status_code", None)
    reason = type(exc).__name__ + (f"（HTTP {status}）" if status else "")
    return f"连接失败：{reason}，详细原因见后端日志"


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


async def _apply_slot_changes(
    session: AsyncSession,
    job: RdReportGenJob,
    changes: list[report_editor.SlotChange],
    rows: dict[str, RdReportGenSlot],
    user_id: UUID | None,
) -> None:
    """把编辑器产出的槽位变更写回库；新增的追加段/追加行也要落行，下次清单才看得到。"""
    now = _now()
    for change in changes:
        row = rows.get(change.key)
        if change.action == "delete":
            if row is not None:
                row.is_deleted = True
                row.edit_source = "manual"
                row.edited_at = now
                row.updated_by = user_id
            continue
        if row is None:
            row = RdReportGenSlot(
                job_id=job.id,
                slot_key=change.key,
                slot_label=change.label,
                anchor=change.anchor,
                value=change.value,
                state="filled",
                edit_source="manual",
                edited_at=now,
                created_by=user_id,
                updated_by=user_id,
            )
            session.add(row)
            rows[change.key] = row
            continue
        row.value = change.value
        row.state = "filled"
        # 同批次里「先还原再改好」会把行软删过：重新写入时必须复活，否则新值不生效
        row.is_deleted = False
        if change.anchor:
            row.anchor = change.anchor
        row.edit_source = "manual"
        row.edited_at = now
        row.updated_by = user_id


def _record_edit_logs(
    session: AsyncSession,
    job: RdReportGenJob,
    run: report_editor.EditRun,
    version_id: UUID | None,
    user_id: UUID | None,
) -> None:
    """逐条记改前改后：版本只说「哪一版」，流水才能回答「这一段被谁改成了什么」。"""
    for change in run.slot_changes:
        session.add(
            RdReportGenEdit(
                job_id=job.id,
                slot_key=change.key,
                operation=change.operation,
                anchor=change.anchor or None,
                before_value=change.before,
                after_value=change.value,
                version_id=version_id,
                created_by=user_id,
                updated_by=user_id,
            )
        )


async def _refresh_slot_counters(session: AsyncSession, job: RdReportGenJob) -> None:
    """人工编辑后覆盖率会变；详情页与列表都读任务上的统计，必须一起刷新。"""
    data = await review.build_review(session, job.id)
    job.slot_total = data.stats.writable_total
    job.slot_filled = data.stats.written
    job.slot_gap = data.stats.blank


async def apply_job_edits(
    session: AsyncSession,
    job_id: UUID,
    payload: ReportGenEditRequest,
    user_id: UUID | None,
) -> ReportGenEditResultData:
    """在线编辑一次保存：逐条校验 → 原地改写 docx → 落版本/流水/槽位。

    不合法的操作只丢弃那一处（并尽量还原成母本原样），其余照常保存；只有一条都没生效
    时才不落版本，返回逐条原因。
    """
    job, outline, _table_starts, rows = await review.load_outline(session, job_id)
    if job.status != "completed" or not job.document_object_key:
        raise BadRequestException("这次生成还没出稿，等完成后再在线编辑")

    current_id = await versions.current_version_id(session, job.id)
    if payload.base_version_id is not None and current_id != payload.base_version_id:
        raise BadRequestException("这一版已经被改过，请刷新后再编辑")

    document_bytes = store.load_bytes(str(job.document_object_key))
    if not document_bytes:
        raise BadRequestException("生成好的文档找不到了，请重新生成一次")

    run = report_editor.apply_operations(document_bytes, outline, rows, payload.operations)
    removed = [
        ReportGenEditRemoval(key=item.key, op=item.op, reason=item.reason, restored=item.restored)
        for item in run.removals
    ]
    rejected = [ReportGenEditRejection(key=item.key, op=item.op, reason=item.reason) for item in run.removals]
    restored = sum(1 for item in run.removals if item.restored)
    if run.applied == 0 or run.document is None:
        # 一条都没生效：不落版本、不写流水，只回逐条原因（位置已按能定位到的范围还原）
        return ReportGenEditResultData(
            applied=0,
            removed=removed,
            restored=restored,
            rejected=rejected,
        )

    file_name = job.document_file_name or "report.docx"
    version, synced = await versions.record_manual_edit(
        session,
        job,
        data=run.document,
        file_name=file_name,
        note=f"站内编辑 {run.applied} 处",
        user_id=user_id,
    )
    await _apply_slot_changes(session, job, run.slot_changes, rows, user_id)
    _record_edit_logs(session, job, run, version.id, user_id)
    await _refresh_slot_counters(session, job)
    await session.commit()

    logger.info(
        "report gen document edited",
        extra={
            "job_id": str(job.id),
            "applied": run.applied,
            "removed": len(run.removals),
            "version_no": version.version_no,
            "biz_module": "research",
        },
    )
    return ReportGenEditResultData(
        applied=run.applied,
        removed=removed,
        restored=restored,
        rejected=rejected,
        version=versions.to_version_data(version),
        synced_deliverable=synced,
    )


async def restore_job_version(
    session: AsyncSession,
    job_id: UUID,
    version_id: UUID,
    *,
    base_version_id: UUID | None,
    user_id: UUID | None,
) -> ReportGenRenderData:
    """回滚到指定版本：不改写历史版本，而是把旧文件再落一个新版本。"""
    return await versions.restore_version(
        session, job_id, version_id, user_id, base_version_id=base_version_id
    )


__all__ = [
    "ACTIVE_STATUSES",
    "TERMINAL_STATUSES",
    "agent_metrics",
    "apply_job_edits",
    "cancel_job",
    "create_feedback",
    "create_job",
    "document_payload",
    "get_job",
    "list_feedback",
    "list_jobs",
    "list_opinion_digests",
    "list_opinions",
    "list_steps",
    "restore_job_version",
    "test_model",
    "update_feedback",
    "update_opinion",
]
