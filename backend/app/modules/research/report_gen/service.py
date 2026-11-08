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
from app.modules.research.doc_template import store
from app.modules.research.models import (
    RdDeliverableTemplate,
    RdReport,
    RdReportGenJob,
    RdReportGenSlot,
    RdReportGenStep,
)
from app.modules.research.report_gen.agent import run_report_gen
from app.modules.research.report_gen.config import load_config
from app.modules.research.report_gen.examples import record_manual_example
from app.modules.research.report_gen.prompts_version import agent_prompt_version, structure_prompt_version
from app.modules.research.report_gen.schemas import (
    ReportGenJobCreateRequest,
    ReportGenJobData,
    ReportGenJobListData,
    ReportGenMetricsData,
    ReportGenModelTestData,
    ReportGenSlotData,
    ReportGenSlotListData,
    ReportGenSlotUpdateRequest,
    ReportGenStepData,
    ReportGenStepListData,
    ReportGenStructureDiff,
    ReportGenStructureRunData,
    ReportGenStructureRunListData,
)
from app.modules.research.report_gen.structure import normalize_structure
from app.modules.research.report_gen.structure_runs import list_structure_runs as _list_structure_runs

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = ("queued", "running")
TERMINAL_STATUSES = ("completed", "failed", "cancelled")
DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _now() -> datetime:
    return datetime.now(UTC)


def _to_job_data(job: RdReportGenJob, report_title: str | None = None) -> ReportGenJobData:
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


def _anchor_sort_key(anchor: dict[str, Any] | None) -> tuple[int, int, int, int, int]:
    """按母本中的阅读顺序排序；锚点缺失的排到最后。"""
    if not isinstance(anchor, dict):
        return (9, 0, 0, 0, 0)
    if anchor.get("kind") == "paragraph":
        return (0, int(anchor.get("index") or 0), 0, 0, 0)
    return (
        1,
        int(anchor.get("table_index") or 0),
        int(anchor.get("row") or 0),
        int(anchor.get("col") or 0),
        int(anchor.get("para_index") or 0),
    )


async def _titles(session: AsyncSession, report_ids: list[UUID]) -> dict[UUID, str]:
    """批量取报告标题：列表页避免 N+1。"""
    unique = [rid for rid in dict.fromkeys(report_ids)]
    if not unique:
        return {}
    result = await session.execute(select(RdReport.id, RdReport.title).where(RdReport.id.in_(unique)))
    return {row[0]: row[1] for row in result.all()}


async def create_job(
    session: AsyncSession,
    payload: ReportGenJobCreateRequest,
    user_id: UUID | None,
) -> ReportGenJobData:
    """建任务并立刻提交后台执行；同一报告已有进行中的任务时直接复用。"""
    report = await session.get(RdReport, payload.report_id)
    if report is None or report.is_deleted:
        raise NotFoundException("研发报告不存在")
    if report.project_id != payload.project_id:
        raise BadRequestException("报告与项目不匹配")

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
        raise NotFoundException("交付物模板不存在")
    if not template.file_object_key:
        raise BadRequestException("该模板尚未上传 Word 母本，无法生成报告")

    # 模型快照：任务发起时固定三档原值，执行期间改配置不影响本任务
    config = await load_config()

    job = RdReportGenJob(
        report_id=payload.report_id,
        project_id=payload.project_id,
        deliverable_template_id=template.id,
        template_file_key=template.file_object_key,
        template_file_name=template.file_name,
        model_config_name=config.model.raw,
        model_name=config.model.display,
        structure_model_name=config.structure_model.raw,
        fallback_model_name=config.fallback_model.raw,
        status="queued",
        progress=0,
        current_step="排队中",
        doc_code=payload.doc_code,
        drug_name=payload.drug_name,
        supplement_text=payload.supplement_text,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    async def _runner(_core_job_id: UUID) -> dict[str, Any]:
        return await run_report_gen(job.id)

    submitted = await submit_job_safe("research.report-gen", _runner)
    if submitted is None:
        # 登记失败：任务不会被执行，直接落失败态，避免列表里永远「排队中」
        job.status = "failed"
        job.error_message = "任务调度失败，请稍后重试"
        job.finished_at = _now()
        await session.commit()
        logger.error("report-gen job submit failed", extra={"job_id": str(job.id)})

    logger.info(
        "report-gen job created",
        extra={"job_id": str(job.id), "report_id": str(payload.report_id), "template_id": str(template.id)},
    )
    return _to_job_data(job, report.title)


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
    return ReportGenJobListData(
        items=[_to_job_data(job, titles.get(job.report_id)) for job in jobs],
        active_count=sum(1 for job in jobs if job.status in ACTIVE_STATUSES),
    )


async def get_job(session: AsyncSession, job_id: UUID) -> ReportGenJobData:
    job = await session.get(RdReportGenJob, job_id)
    if job is None or job.is_deleted:
        raise NotFoundException("生成任务不存在")
    titles = await _titles(session, [job.report_id])
    return _to_job_data(job, titles.get(job.report_id))


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


async def list_slots(session: AsyncSession, job_id: UUID) -> ReportGenSlotListData:
    result = await session.execute(
        select(RdReportGenSlot).where(
            RdReportGenSlot.job_id == job_id, RdReportGenSlot.is_deleted.is_(False)
        )
    )
    rows = sorted(result.scalars().all(), key=lambda row: _anchor_sort_key(row.anchor))
    items = [
        ReportGenSlotData(
            slot_key=row.slot_key,
            slot_label=row.slot_label,
            location=str((row.anchor or {}).get("location") or "") or None,
            state=row.state,
            value=row.value,
            source_name=row.source_name,
            evidence=row.evidence,
            confidence=row.confidence,
            owner_hint=row.owner_hint,
        )
        for row in rows
    ]
    return ReportGenSlotListData(
        items=items,
        total=len(items),
        filled=sum(1 for row in rows if row.state in ("filled", "conflict")),
        gaps=sum(1 for row in rows if row.state in ("gap", "pending", "anchor_unresolved")),
    )


async def update_slot(
    session: AsyncSession,
    job_id: UUID,
    slot_key: str,
    payload: ReportGenSlotUpdateRequest,
    user_id: UUID | None,
) -> ReportGenSlotData:
    """人工修正：只改槽位与对照表口径，成品 docx 不重渲染（按确认的需求口径）。"""
    result = await session.execute(
        select(RdReportGenSlot).where(
            RdReportGenSlot.job_id == job_id,
            RdReportGenSlot.slot_key == slot_key,
            RdReportGenSlot.is_deleted.is_(False),
        )
    )
    row = result.scalars().first()
    if row is None:
        raise NotFoundException("槽位不存在")

    value = (payload.value or "").strip()
    if value:
        row.value = value
        row.state = "filled"
        if payload.evidence:
            row.evidence = f"[人工] {payload.evidence}"
    else:
        row.value = None
        row.state = "gap"
        if payload.evidence:
            row.evidence = payload.evidence
    if payload.owner_hint:
        row.owner_hint = payload.owner_hint
    row.updated_by = user_id
    await session.flush()

    job = await session.get(RdReportGenJob, job_id)
    if job is not None:
        slots = await list_slots(session, job_id)
        job.slot_total = slots.total
        job.slot_filled = slots.filled
        job.slot_gap = slots.gaps
        # 人工修正顺手沉淀成示例：下次同模板生成读它当 few-shot 参照（失败不影响保存）
        try:
            await record_manual_example(
                session,
                template_id=job.deliverable_template_id,
                slot_key=row.slot_key,
                slot_label=row.slot_label,
                value=row.value,
                evidence=payload.evidence or row.evidence,
            )
        except Exception:  # noqa: BLE001 - 示例库是增益项，不能反过来卡住人工保存
            logger.exception("report-gen example record failed", extra={"job_id": str(job_id)})
    await session.commit()

    return ReportGenSlotData(
        slot_key=row.slot_key,
        slot_label=row.slot_label,
        location=str((row.anchor or {}).get("location") or "") or None,
        state=row.state,
        value=row.value,
        source_name=row.source_name,
        evidence=row.evidence,
        confidence=row.confidence,
        owner_hint=row.owner_hint,
    )


async def cancel_job(session: AsyncSession, job_id: UUID, user_id: UUID | None) -> ReportGenJobData:
    job = await session.get(RdReportGenJob, job_id)
    if job is None or job.is_deleted:
        raise NotFoundException("生成任务不存在")
    if job.status in TERMINAL_STATUSES:
        raise BadRequestException("任务已结束，无需终止")

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


async def _artifact(session: AsyncSession, job_id: UUID, field: str) -> tuple[str, bytes, str]:
    job = await session.get(RdReportGenJob, job_id)
    if job is None or job.is_deleted:
        raise NotFoundException("生成任务不存在")
    key = getattr(job, field, None)
    if not key:
        raise NotFoundException("该任务的成品还未生成")

    data = store.load_bytes(str(key))
    if data is None:
        raise NotFoundException("成品文件已丢失，请重新生成")

    if field == "document_object_key":
        return job.document_file_name or "report.docx", data, DOCX_CONTENT_TYPE
    return "槽位对照表.md", data, "text/markdown; charset=utf-8"


async def document_payload(session: AsyncSession, job_id: UUID) -> tuple[str, bytes, str]:
    return await _artifact(session, job_id, "document_object_key")


async def comparison_payload(session: AsyncSession, job_id: UUID) -> tuple[str, bytes, str]:
    return await _artifact(session, job_id, "comparison_object_key")


_PROBE_TIMEOUT_SECONDS = 20

# 统计窗口上限：超过 90 天样本混杂多轮提示词与模型调整，对比意义不大
_METRICS_MAX_DAYS = 90


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

    statement = (
        select(
            func.count().label("total"),
            func.coalesce(func.sum(case((is_completed, 1), else_=0)), 0).label("completed"),
            func.coalesce(func.sum(case((RdReportGenJob.status == "failed", 1), else_=0)), 0).label("failed"),
            func.coalesce(func.sum(case((RdReportGenJob.status == "cancelled", 1), else_=0)), 0).label(
                "cancelled"
            ),
            func.avg(case((is_completed, RdReportGenJob.rounds), else_=None)).label("avg_rounds"),
            func.avg(case((is_completed, duration_seconds), else_=None)).label("avg_duration_seconds"),
            func.coalesce(func.sum(case((is_completed, RdReportGenJob.slot_total), else_=0)), 0).label(
                "slot_total"
            ),
            func.coalesce(func.sum(case((is_completed, RdReportGenJob.slot_gap), else_=0)), 0).label(
                "slot_gap"
            ),
            # 降级只对跑完的任务有意义：失败任务走兜底也说明不了模型质量
            func.coalesce(
                func.sum(case((is_completed & RdReportGenJob.used_fallback.is_(True), 1), else_=0)), 0
            ).label("fallback_completed"),
        )
        .where(
            RdReportGenJob.is_deleted.is_(False),
            RdReportGenJob.status.in_(TERMINAL_STATUSES),
            finished >= since,
        )
    )
    row = (await session.execute(statement)).one()

    total = int(row.total or 0)
    completed = int(row.completed or 0)
    slot_total = int(row.slot_total or 0)
    slot_gap = int(row.slot_gap or 0)
    avg_rounds = row.avg_rounds
    avg_duration = row.avg_duration_seconds

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
        agent_prompt_version=agent_prompt_version(config.agent_prompt),
        structure_prompt_version=structure_prompt_version(config.structure_prompt),
        generated_at=_now(),
    )


async def list_structure_runs(
    session: AsyncSession,
    template_id: UUID,
    limit: int = 10,
) -> ReportGenStructureRunListData:
    """母本解析留痕 + 与当前结构的差异（漏选/多选）。只读，不改结构。"""
    template = await session.get(RdDeliverableTemplate, template_id)
    if template is None or template.is_deleted:
        raise NotFoundException("交付物模板不存在")
    current_slots = normalize_structure(template.template_structure).get("slots") or []
    rows = await _list_structure_runs(
        session,
        template_id,
        current_slots=current_slots,
        limit=limit,
    )
    items = [
        ReportGenStructureRunData(
            id=str(row["id"]),
            source_key=row["source_key"],
            prompt_version=row["prompt_version"],
            model_name=row["model_name"],
            candidate_count=row["candidate_count"],
            slot_count=row["slot_count"],
            duration_ms=row["duration_ms"],
            status=row["status"],
            error=row["error"],
            created_at=row["created_at"],
            diff=ReportGenStructureDiff(**row["diff"]),
        )
        for row in rows
    ]
    return ReportGenStructureRunListData(total=len(items), items=items)


async def test_model(slot: str) -> ReportGenModelTestData:
    """按档位解析绑定后发一次极短对话，供配置页「测试连通」使用。

    只验证能不能出字：不写库、不改配置、不影响全局活跃模型。失败只回异常类型与
    状态码，响应里不出现端点、上游响应与密钥。
    """
    config = await load_config()
    binding = {
        "main": config.model,
        "structure": config.structure_model,
        "fallback": config.fallback_model,
    }.get(slot)
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


__all__ = [
    "ACTIVE_STATUSES",
    "TERMINAL_STATUSES",
    "agent_metrics",
    "cancel_job",
    "comparison_payload",
    "create_job",
    "document_payload",
    "get_job",
    "list_jobs",
    "list_slots",
    "list_steps",
    "test_model",
    "update_slot",
]
