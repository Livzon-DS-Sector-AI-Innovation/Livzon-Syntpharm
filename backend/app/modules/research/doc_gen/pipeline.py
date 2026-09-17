"""任务执行流水线：解析资料 → 槽位取值 → 章节实例化 →（成文）→ 渲染 docx → 生成说明 → 落库。

**两种运行形态**（由运行时配置 ``DOC_GEN_CHAT_ENABLED`` 在 Service 建任务时决定）：

1. 对话复核（开）：首次领取解析 + 提取后停在 ``awaiting_review`` 等人工确认，不渲染；
   确认后置 ``confirmed`` 被重新领取，检测到已落库的槽位结果便跳过解析与提取，
   直接成文 + 渲染，**不重复调用提取模型**（提取是整条链路最贵的一步）；
2. 直达生成（关，默认）：新建即排队，一次领取得跑完「解析 → 提取 → 成文 → 渲染」，
   结果以「已验证 + 已确认」呈现，人工修正后点「重新生成」开新任务重跑。

**成文阶段**（AI 报告生成，``DOC_GEN_COMPOSE_ENABLED``）：把人工确认的槽位取值交给
成文模型润色成连续叙述；含未确认数字或超字数上限的输出整槽回退人工文本。

**动态章节的取值顺序**（模板声明了扩展点时才会走）：
骨架槽位第一轮提取 → 用它的值（及解析信号）做触发判定 → 实例化章节 → 只对
实例化出来的章节局部槽位跑第二轮提取。这样既不会为没出现的章节白花模型调用，
又能在进入取值前把结构摊平成普通槽位 key，让下游全部无感。

一次执行只持有自己的中间结果（blocks/results/sections），不做进程内任务缓存，
因此任务失败或重启都不会留下脏状态。
"""

from __future__ import annotations

import asyncio
import contextlib
import io
import logging
import os
import tempfile
import uuid
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.modules.research import models as rd_models
from app.modules.research.doc_gen import cancellation, compose, conversation, status, store
from app.modules.research.doc_gen import repository as repo
from app.modules.research.doc_gen.cancellation import AbortHandle
from app.modules.research.doc_gen.content_validator import ValidationResult, validate_extraction
from app.modules.research.doc_gen.extraction import (
    DATABASE_ROLE,
    DB_FILE_PREFIX,
    SUPPLEMENT_FILE_ID,
    SUPPLEMENT_ROLE,
    EvidenceModel,
    ExtractionAbortError,
    ExtractStats,
    SlotExtractor,
    SlotResult,
)
from app.modules.research.doc_gen.direct_generator import DirectGenStats, direct_generate
from app.modules.research.doc_gen.file_analyzer import (
    FileAnalysisBatchResult,
    analyze_files,
    build_file_analysis_context,
)
from app.modules.research.doc_gen.models import DocGenInputFile, DocGenJob, DocGenSection, DocGenSlotValue
from app.modules.research.doc_gen.parsing import IMAGE_EXTENSIONS, TextBlock, parse_file
from app.modules.research.doc_gen.renderer import RenderReport, SectionPlan, SlotValue, render_document
from app.modules.research.doc_gen.report import build_report_markdown, summarize_states
from app.modules.research.doc_gen.runtime_config import RuntimeConfig, load_runtime_config, resolve_model
from app.modules.research.doc_gen.sections import SectionInstance, build_trigger_context, instantiate
from app.modules.research.doc_gen.spec_enrich import enrich_search_terms
from app.modules.research.doc_gen.spec_source import resolve_for_job
from app.modules.research.doc_gen.template_analyzer import (
    TemplateAnalysisResult,
    analyze_template,
    apply_analysis_to_spec,
)
from app.modules.research.doc_gen.template_spec import (
    SECTION_INSTANCE_SEP,
    Slot,
    TemplateSpec,
    expand_slot_key,
    split_slot_key,
)

logger = logging.getLogger(__name__)

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MAX_PARSE_CHARS = 2_000_000
# 渲染与产物上传都是同步阻塞调用（python-docx / MinIO 客户端），给一个足够宽裕的硬超时
RENDER_TIMEOUT_SECONDS = 300


async def _run_blocking(
    func: Any, /, *args: Any, timeout_seconds: float = RENDER_TIMEOUT_SECONDS, **kwargs: Any
) -> Any:
    """把同步阻塞调用放线程池执行并施加超时。

    第三方库卡在 C 层时事件循环会被整条拖住，那时前端轮询和取消请求都进不来，
    「强制终止」就无从实施——所以任何同步 IO/CPU 调用都不允许直接在协程里裸调。
    """
    return await asyncio.wait_for(asyncio.to_thread(func, *args, **kwargs), timeout=timeout_seconds)


class JobAbortedError(Exception):
    """可预期的任务失败（模板缺失、资料无文字、超出规模上限等）。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class JobContext:
    """单次任务执行的上下文。"""

    job: DocGenJob
    spec: TemplateSpec
    files: list[DocGenInputFile]
    blocks: list[TextBlock] = field(default_factory=list)
    results: dict[str, SlotResult] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    render_report: RenderReport | None = None
    sections: list[SectionInstance] = field(default_factory=list)
    # 章节实例 key → 实际标题，供成文 prompt 标注槽位所属章节
    section_titles: dict[str, str] = field(default_factory=dict)
    # 提取阶段统计（模型调用/重试/检索未命中等），供 stats 落库
    extract_stats: ExtractStats = field(default_factory=ExtractStats)
    # 成文阶段统计（改写/拒绝/失败数），未成文时为空
    compose_stats: compose.ComposeStats | None = None
    # 提取开始时间戳（用于计算耗时）
    extract_start_time: float | None = None
    # 模板分析产物（LLM 解析模板后输出的槽位指引）
    template_analysis: TemplateAnalysisResult | None = None
    # 文件分析产物（LLM 异步逐文件分析后的结构化摘要）
    file_analysis: FileAnalysisBatchResult | None = None
    # 交叉校验产物（文件分析 vs 槽位提取的一致性检查）
    cross_validation: ValidationResult | None = None


def _now() -> datetime:
    return datetime.now(UTC)


async def execute_job(job_id: uuid.UUID, handle: AbortHandle | None = None) -> str:
    """用独立 session 执行一个任务，返回终态。由后台 worker 调用。

    执行期间并行跑两个基础设施协程（各自用独立 session，不与执行 session 交叉）：

    - ``_heartbeat_loop``：按 ``heartbeat_seconds`` 续租，防止长任务租约过期被重复领取；
    - ``_cancel_watch_loop``：秒级轮询数据库取消标志，命中就置位进程内 ``handle``。

    两者收敛到同一个 ``handle``，解析器与模型调用只需一个同步探针即可在检查点退出——
    这是「强制终止」能生效的关键：全局 session 工厂是 ``expire_on_commit=False``，
    执行 session 里的 ORM 对象永远看不见别的事务改的状态，必须另开通道。
    """
    owns_handle = handle is None
    active = handle if handle is not None else cancellation.register(job_id)
    config = await load_runtime_config()

    # 使用独立 session 执行任务
    session = async_session_factory()
    try:
        current = await repo.read_status(session, job_id)
        if current == "cancelled":
            if owns_handle:
                cancellation.unregister(job_id)
            return "cancelled"
        job = await repo.get_job(session, job_id)
        if job is None or job.is_deleted:
            if owns_handle:
                cancellation.unregister(job_id)
            return "missing"
        guards = [
            asyncio.create_task(_heartbeat_loop(job_id, active, config)),
            asyncio.create_task(_cancel_watch_loop(job_id, active, config)),
        ]
        try:
            await run_job(session, job, config, active)
        except JobAbortedError as exc:
            logger.warning("文档生成任务中止", extra={"job_id": str(job_id), "code": exc.code})
            await _fail_with_new_session(job_id, exc.code, exc.message)
        except ExtractionAbortError as exc:
            logger.warning("文档生成提取被终止", extra={"job_id": str(job_id), "reason": exc.reason})
            await _fail_with_new_session(job_id, "cancelled", "任务已终止")
        except Exception as exc:  # noqa: BLE001 - 后台任务不允许把异常抛出去
            logger.exception("文档生成任务异常", extra={"job_id": str(job_id)})
            await _fail_with_new_session(job_id, "internal_error", f"{type(exc).__name__}: {exc}"[:400])
        finally:
            for guard in guards:
                guard.cancel()
            await asyncio.gather(*guards, return_exceptions=True)
            if owns_handle:
                cancellation.unregister(job_id)
            # 尝试清理租约
            try:
                job.lease_expires_at = None
                await session.commit()
            except Exception:
                logger.exception("文档生成任务清理租约失败")
        return job.status
    finally:
        await session.close()


async def _fail_with_new_session(job_id: uuid.UUID, code: str, message: str) -> None:
    """使用新 session 标记任务失败，避免原 session 状态不一致的问题。"""
    try:
        async with async_session_factory() as session:
            job = await repo.get_job(session, job_id)
            if job is None:
                return
            # 检查是否已被取消
            if await repo.cancel_requested(session, job_id):
                job.status = "cancelled"
                job.step = "已取消"
                job.finished_at = _now()
            else:
                _fail(job, code, message)
            await session.commit()
    except Exception:
        logger.exception("文档生成任务标记失败状态时出错")


async def _safe_rollback(session: AsyncSession) -> None:
    """安全回滚：异常后清理 session 状态，失败只记日志。"""
    try:
        await session.rollback()
    except Exception:  # noqa: BLE001 - rollback 也可能失败
        logger.exception("文档生成任务回滚失败")


async def _commit_quietly(session: AsyncSession) -> None:
    """收尾提交：失败只记日志，绝不在后台任务里抛出。"""
    try:
        await session.commit()
    except Exception:  # noqa: BLE001 - 收尾提交失败不能再抛
        logger.exception("文档生成任务状态收尾提交失败")
        await _safe_rollback(session)


async def _heartbeat_loop(job_id: uuid.UUID, handle: AbortHandle, config: RuntimeConfig) -> None:
    """续租心跳：任务还在跑就一直把租约往后推，直到被取消。"""
    interval = max(5, config.heartbeat_seconds)
    while not handle.should_cancel():
        try:
            await asyncio.sleep(interval)
            async with async_session_factory() as session:
                await repo.heartbeat(session, job_id, config.lease_seconds)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - 续租失败不能让任务崩
            logger.exception("文档生成租约续期失败", extra={"job_id": str(job_id)})


async def _cancel_watch_loop(job_id: uuid.UUID, handle: AbortHandle, config: RuntimeConfig) -> None:
    """轮询数据库取消标志：命中即置位进程内句柄，让同步解析与模型调用立刻退出。"""
    interval = min(5.0, max(1.0, config.heartbeat_seconds / 4))
    while True:
        try:
            await asyncio.sleep(interval)
            async with async_session_factory() as session:
                if await repo.cancel_requested(session, job_id):
                    handle.request("cancelled")
                    return
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - 轮询失败继续下一轮
            logger.exception("文档生成取消标志轮询失败", extra={"job_id": str(job_id)})


def _fail(job: DocGenJob, code: str, message: str) -> None:
    """记录失败终态。"""
    job.status = "failed"
    job.error_code = code
    job.error_message = message[:1000]
    job.step = "失败"
    job.finished_at = _now()


async def _fail_protected(session: AsyncSession, job: DocGenJob, code: str, message: str) -> None:
    """落失败终态，但**不覆盖已生效的取消**。

    用户点了终止后库里已是 cancelled，若这里再写 failed，前端就会从「已取消」
    弹回「失败」，看起来像取消失败。
    """
    try:
        if await repo.cancel_requested(session, job.id):
            job.status = "cancelled"
            job.step = "已取消"
            job.finished_at = _now()
            return
    except Exception:  # noqa: BLE001 - 查询失败就直接标失败，不阻塞收尾
        logger.exception("文档生成任务取消状态查询失败，直接标失败")
    _fail(job, code, message)


async def _check_cancelled(session: AsyncSession, job: DocGenJob, handle: AbortHandle | None) -> None:
    """取消检查：进程内句柄（即时）+ 数据库状态（跨进程）双通道。"""
    if handle is not None and handle.should_cancel():
        raise JobAbortedError("cancelled", "任务已取消")
    if await repo.cancel_requested(session, job.id):
        if handle is not None:
            handle.request("cancelled")
        raise JobAbortedError("cancelled", "任务已取消")


async def run_job(
    session: AsyncSession, job: DocGenJob, config: RuntimeConfig, handle: AbortHandle | None = None
) -> None:
    """执行任务主体。

    已存在落库的槽位结果（人工确认后续跑，或渲染阶段中断后重试）时只补成文与渲染；
    否则先解析 + 提取：对话模式停在 ``awaiting_review`` 等人工确认，
    直达生成模式（对话关闭）一路跑完成文与渲染。
    """
    try:
        spec = await resolve_for_job(session, job)
    except KeyError as exc:
        raise JobAbortedError("template_missing", str(exc)) from exc
    files = list(await repo.list_input_files(session, job.id))
    if not files:
        raise JobAbortedError("no_files", "任务没有可解析的资料文件")
    ctx = JobContext(job=job, spec=spec, files=files)
    reviewed = list(await repo.list_slot_values(session, job.id))
    if reviewed:
        ctx.results = _results_from_rows(reviewed)
        ctx.sections = _sections_from_rows(spec, list(await repo.list_sections(session, job.id)))
        ctx.section_titles = {instance.section_key: instance.title for instance in ctx.sections}
        # 解析阶段的告警已落在资料记录里，续跑时按首次执行的格式补回文件名前缀
        ctx.warnings = [f"{record.original_filename}：{warn}" for record in files for warn in (record.warnings or [])]
        # 确认后续跑只补提取，资料集未变无需重新解析，补上补充信息块即可成文
        supplement = _supplement_block(job.supplement_text)
        if supplement is not None:
            ctx.blocks.append(supplement)
        await _compose_stage(session, ctx, config, handle)
        await _render_stage(session, ctx, handle)
        return
    # 直接生成模式：跳过模板分析/文件分析/逐槽位提取/成文，一次性生成全部内容
    if config.direct_generation_enabled:
        await _parse_stage(session, ctx, config, handle)
        ctx.blocks.extend(await _project_database_blocks(session, job))
        supplement = _supplement_block(job.supplement_text)
        if supplement is not None:
            ctx.blocks.append(supplement)
        await _direct_generate_stage(session, ctx, config, handle)
        # 动态章节：直接生成模式下暂不支持章节局部槽位的二次提取，
        # 但仍做实例化以保留章节结构（骨架槽位已在直接生成中覆盖）
        if ctx.spec.has_sections:
            await _instantiate_stage(session, ctx, handle)
        await _render_stage(session, ctx, handle)
        return

    # 模板分析：用 LLM 解析模板结构，输出每槽位的抽取指引（失败静默降级）
    await _template_analysis_stage(session, ctx, config, handle)
    await _parse_stage(session, ctx, config, handle)
    # 登记结构化数据以虚拟资料（role=database）注入，检索与取值即可引用项目权威事实
    ctx.blocks.extend(await _project_database_blocks(session, job))
    # 人工补充信息同样作为虚拟资料（role=supplement）参与检索与取值
    supplement = _supplement_block(job.supplement_text)
    if supplement is not None:
        ctx.blocks.append(supplement)
    # AI 辅助标注：自动识别模板的槽位缺检索词时补同义词（失败静默降级）
    await _enrich_spec(ctx, config)
    # 文件分析：异步逐文件读取，用 LLM 提取与模板匹配的结构化摘要（失败静默降级）
    await _file_analysis_stage(session, ctx, config, handle)
    chat_mode = config.chat_enabled
    # 直达生成模式要在提取后继续成文+渲染，把「等待确认」的进度带让给成文阶段
    first_to = 70 if chat_mode else 55
    second_from, second_to = (74, 88) if chat_mode else (57, 65)
    if ctx.spec.has_sections:
        # 有动态章节时把进度带切开：第一轮只跑骨架槽位，章节槽位在实例化之后才存在
        await _extract_stage(session, ctx, config, handle, progress_from=20, progress_to=first_to)
        await _instantiate_stage(session, ctx, handle)
        section_slots = [slot for instance in ctx.sections for slot in instance.slots]
        if section_slots:
            await _extract_stage(
                session,
                ctx,
                config,
                handle,
                slots=section_slots,
                progress_from=second_from,
                progress_to=second_to,
                step_label="AI 分析章节内容",
            )
    else:
        await _extract_stage(
            session, ctx, config, handle, progress_from=20, progress_to=second_to, step_label="AI 提取信息"
        )
    # 交叉校验：对比文件分析摘要与槽位提取结果，标记不一致（失败静默降级）
    await _cross_validation_stage(session, ctx, config, handle)
    await _review_stage(session, ctx, config, handle, stop_for_review=chat_mode)
    if not chat_mode:
        await _compose_stage(session, ctx, config, handle)
        await _render_stage(session, ctx, handle)


async def _review_stage(
    session: AsyncSession,
    ctx: JobContext,
    config: RuntimeConfig,
    handle: AbortHandle | None = None,
    *,
    stop_for_review: bool = True,
) -> None:
    """提取完成后落库（槽位 + 大纲）。

    ``stop_for_review=True``（对话模式）停在「等待人工确认」，不渲染，并自动创建
    对话会话生成首轮盘点卡——用户进入详情页即可看到会话；会话创建失败不阻塞任务。
    ``stop_for_review=False``（直达生成模式）只落库提取结果，随后继续成文与渲染。
    """
    job = ctx.job
    await _check_cancelled(session, job, handle)
    await _persist_slot_values(session, job, ctx)
    await _persist_sections(session, job, ctx)
    if not stop_for_review:
        job.step = "AI 提取信息完成，准备成文"
        await session.commit()
        return
    if config.chat_enabled:
        try:
            rows = await conversation.load_slot_rows(session, job.id)
            await conversation.ensure_conversation(session, job.id, ctx.spec, rows, config=config)
        except Exception:  # noqa: BLE001 - 会话是增强能力，失败不能拖垮任务
            logger.exception("对话会话创建失败（任务继续）", extra={"job_id": str(job.id)})
    job.status = "awaiting_review"
    job.step = "等待人工确认"
    job.progress = 90
    job.lease_expires_at = None
    # 提取统计：供前端 review 阶段展示总述
    state_counts = summarize_states(list(ctx.results.values()))
    # 计算提取耗时
    import time
    extract_duration = None
    if ctx.extract_start_time:
        extract_duration = round(time.time() - ctx.extract_start_time, 1)
    job.stats = {
        "sections": len(ctx.sections),
        "section_titles": [s.title for s in ctx.sections],
        "substantive": state_counts.get(status.STATUS_OK, 0),
        "pending": state_counts.get(status.STATUS_PENDING, 0) + state_counts.get(status.STATUS_FAILED, 0),
        "manual": state_counts.get(status.STATUS_MANUAL, 0),
        "drafts": state_counts.get(status.STATUS_DRAFT, 0),
        "conflicts": state_counts.get(status.STATUS_CONFLICT, 0),
        "needs_verify": state_counts.get(status.STATUS_NEEDS_VERIFY, 0),
        "low_confidence": ctx.extract_stats.low_confidence if ctx.extract_stats else 0,
        "retrieval_misses": ctx.extract_stats.retrieval_misses if ctx.extract_stats else 0,
        "total_slots": len(ctx.results),
        "slot_states": state_counts,
        "warnings": list(ctx.warnings),
        "extract_duration_seconds": extract_duration,
    }
    await session.commit()


def _supplement_block(text: str | None) -> TextBlock | None:
    """把人工补充说明包装成虚拟资料块（role=supplement），空文本返回 None。"""
    body = (text or "").strip()
    if not body:
        return None
    return TextBlock(file_id=SUPPLEMENT_FILE_ID, page=1, index=0, text=body, kind="paragraph")


async def _compose_stage(
    session: AsyncSession, ctx: JobContext, config: RuntimeConfig, handle: AbortHandle | None = None
) -> None:
    """成文阶段：把人工确认的槽位取值交给成文模型改写成连续正文。

    确定性防线在 :mod:`compose` 内：引入未确认数字或超字数上限的输出整槽回退。
    本阶段整体可降级——模型不可用时逐槽保留人工确认文本，任务照常渲染，
    只有「成文期间被取消」才中断（人工确认文本本身就是可用产物）。
    """
    job = ctx.job
    await _check_cancelled(session, job, handle)
    if not config.compose_enabled:
        return
    slots: list[Slot] = list(ctx.spec.slots) + [slot for instance in ctx.sections for slot in instance.slots]
    if not any(r.state in compose.COMPOSABLE_STATES for r in ctx.results.values()):
        return
    job.status = "composing"
    job.step = "AI 撰写报告正文"
    job.progress = 78 if config.chat_enabled else 68
    await session.commit()
    choice = await resolve_model(config.write_model_name)
    try:
        outcome = await compose.compose_results(
            slots,
            ctx.results,
            supplement=(job.supplement_text or "").strip(),
            section_titles=ctx.section_titles,
            llm_kwargs={"model_override": choice.model_override, "config_name": choice.config_name},
            max_context_chars=config.context_chars,
            timeout_seconds=config.llm_call_timeout_seconds,
            should_cancel=handle.should_cancel if handle is not None else None,
            max_concurrent_batches=config.compose_concurrency,
        )
    except RuntimeError as exc:  # 成文循环里的取消探针异常，归一化为任务中止
        raise JobAbortedError("cancelled", str(exc)) from exc
    ctx.results.update(outcome.results)
    ctx.compose_stats = outcome.stats
    ctx.warnings.extend(outcome.stats.warnings)
    if outcome.results:
        # 成文改写了文本，立刻落库，渲染中断后重跑不会丢失已确认原文与成文结果
        await _persist_slot_values(session, job, ctx)
    await _check_cancelled(session, job, handle)
    job.progress = 88 if config.chat_enabled else 85
    await session.commit()


def _results_from_rows(rows: Sequence[DocGenSlotValue]) -> dict[str, SlotResult]:
    """把落库的槽位结果还原成 SlotResult（人工确认后续跑用）。"""
    results: dict[str, SlotResult] = {}
    for row in rows:
        results[row.slot_key] = SlotResult(
            key=row.slot_key,
            pre_compose_text=row.pre_compose_text or "",
            text=row.text or "",
            rows=[dict(item) for item in (row.rows or [])],
            state=row.state,
            reason=row.reason or "",
            evidence=[EvidenceModel.model_validate(item) for item in (row.evidence or [])],
            candidates=list(row.candidates or []),
            confidence=row.confidence,
        )
    return results


def _sections_from_rows(spec: TemplateSpec, rows: Sequence[DocGenSection]) -> list[SectionInstance]:
    """把落库的大纲还原成章节实例。

    槽位定义从模板规格重新展开而不是落库：规格是唯一真相，模板改了槽位也不会
    出现「库里的旧槽位定义」与「新母本」对不上的情况。
    """
    instances: list[SectionInstance] = []
    for row in rows:
        fragment = spec.fragment(row.fragment_key)
        slots = (
            [slot.model_copy(update={"key": expand_slot_key(row.section_key, slot.key)}) for slot in fragment.slots]
            if fragment is not None
            else []
        )
        instances.append(
            SectionInstance(
                section_key=row.section_key,
                fragment_key=row.fragment_key,
                extension_point_key=row.extension_point_key,
                parent_section_key=row.parent_section_key,
                level=row.level,
                title=row.title,
                order_index=row.order_index,
                source=row.source,
                state=row.state,
                trigger_trace=dict(row.trigger_trace or {}),
                slots=slots,
            )
        )
    return instances


def _instance_index(section_key: str | None) -> int | None:
    """从章节实例 key 里取出序号（``route_study__2`` → 2）。"""
    if not section_key or SECTION_INSTANCE_SEP not in section_key:
        return None
    tail = section_key.rpartition(SECTION_INSTANCE_SEP)[2]
    return int(tail) if tail.isdigit() else None


def _section_plans(ctx: JobContext) -> list[SectionPlan]:
    """把章节实例转成渲染计划；被禁用的章节连同其子章节一并跳过。"""
    disabled = {instance.section_key for instance in ctx.sections if instance.state != "enabled"}
    by_key = {instance.section_key: instance for instance in ctx.sections}

    def _blocked(section_key: str | None) -> bool:
        """向上追溯：任一祖先被禁用，本节也不渲染。"""
        seen: set[str] = set()
        while section_key and section_key not in seen:
            seen.add(section_key)
            if section_key in disabled:
                return True
            parent = by_key.get(section_key)
            section_key = parent.parent_section_key if parent is not None else None
        return False

    plans: list[SectionPlan] = []
    for instance in sorted(ctx.sections, key=lambda item: item.order_index):
        if _blocked(instance.section_key):
            continue
        fragment = ctx.spec.fragment(instance.fragment_key)
        plans.append(
            SectionPlan(
                section_key=instance.section_key,
                fragment_key=instance.fragment_key,
                anchor_key=instance.anchor_key,
                level=instance.level,
                title=instance.title,
                parent_section_key=instance.parent_section_key,
                slots=list(instance.slots),
                on_empty=fragment.on_empty if fragment is not None else "keep_title",
            )
        )
    return plans


async def _parse_stage(
    session: AsyncSession, ctx: JobContext, config: RuntimeConfig, handle: AbortHandle | None = None
) -> None:
    """并发解析所有资料文件为带页码的文本块。

    多文件并发解析（最多 ``parse_concurrency`` 个同时），CPU 密集型（OCR）与 IO 密集型
    （纯文本/PDF 文字层）混合场景下显著提速。进度更新与取消检查通过锁保护。
    """
    job = ctx.job
    job.status = "parsing"
    job.step = "解析资料"
    job.progress = 5
    # 初始化文件解析进度列表（存入 meta.parse_progress 供前端展示）
    parse_progress: list[dict[str, str]] = [
        {"name": f.original_filename, "status": "pending"} for f in ctx.files
    ]
    meta = dict(job.meta or {})
    meta["parse_progress"] = parse_progress
    job.meta = meta
    await session.commit()  # 前端每 3 秒轮询这一行，必须实时提交，否则进度永远停在「排队中」
    total_pages = 0
    completed_count = 0
    parse_lock = asyncio.Lock()
    concurrency = max(1, config.parse_concurrency)
    sem = asyncio.Semaphore(concurrency)
    # 文件名 → 进度索引映射，用于快速更新状态
    file_index_map = {f.original_filename: i for i, f in enumerate(ctx.files)}

    async def _parse_with_guard(record: DocGenInputFile) -> tuple[list[TextBlock], list[str], int]:
        nonlocal completed_count, total_pages
        async with sem:
            # 并发解析时只使用进程内 handle 检查取消，避免 session 并发操作错误
            if handle is not None and handle.should_cancel():
                raise JobAbortedError("cancelled", "任务已取消")
            # 标记为「解析中」
            async with parse_lock:
                idx = file_index_map.get(record.original_filename)
                if idx is not None:
                    parse_progress[idx]["status"] = "parsing"
                    job.step = f"解析资料 {completed_count + 1}/{len(ctx.files)}：{record.original_filename}"[:64]
                    meta = dict(job.meta or {})
                    meta["parse_progress"] = parse_progress
                    job.meta = meta
                    await session.commit()
            try:
                blocks, warnings, pages = await _parse_one(record, config, handle)
                file_status = "done"
            except Exception as exc:  # noqa: BLE001 - 单个文件解析异常不能拖垮整个任务
                logger.exception("资料解析异常", extra={"job_id": str(job.id), "file_id": record.file_id})
                record.parse_status = "failed"
                record.warnings = [f"解析异常：{type(exc).__name__}: {exc}"[:300]]
                blocks, warnings, pages = [], [f"{record.original_filename}：解析异常（{type(exc).__name__}）"], 0
                file_status = "failed"
            async with parse_lock:
                ctx.blocks.extend(blocks)
                ctx.warnings.extend(warnings)
                total_pages += pages
                completed_count += 1
                position = completed_count
                # 更新该文件的最终状态
                idx = file_index_map.get(record.original_filename)
                if idx is not None:
                    parse_progress[idx]["status"] = file_status
                job.step = f"解析资料 {position}/{len(ctx.files)}：{record.original_filename}"[:64]
                job.progress = 5 + int(15 * position / max(1, len(ctx.files)))
                meta = dict(job.meta or {})
                meta["parse_progress"] = parse_progress
                job.meta = meta
                await session.commit()
            return blocks, warnings, pages

    await asyncio.gather(*(_parse_with_guard(record) for record in ctx.files))
    if total_pages > config.max_total_pages:
        raise JobAbortedError(
            "too_large", f"资料合计 {total_pages} 页，超过上限 {config.max_total_pages} 页，请拆分任务"
        )
    if not ctx.blocks:
        failed_names = [record.original_filename for record in ctx.files if record.parse_status == "failed"]
        detail = f"失败文件：{'、'.join(failed_names[:5])}" if failed_names else "可能是无文字层的图片集"
        raise JobAbortedError("no_text", f"资料未能解析出可分析的文字（{detail}）")


async def _load_object(object_key: str, timeout_seconds: int) -> bytes | None:
    """从对象存储取资料原件（带超时）。

    MinIO 客户端是同步阻塞的，网络异常时能把事件循环整条拖住——那时前端的取消请求
    都进不来，所以必须放线程池并施加超时。
    """
    try:
        return await asyncio.wait_for(asyncio.to_thread(store.load_bytes, object_key), timeout=max(5, timeout_seconds))
    except (TimeoutError, OSError, ValueError):
        logger.warning("资料原件读取超时或失败", extra={"object_key": object_key})
        return None
    except Exception:  # noqa: BLE001 - 存储异常种类多，统一按读取失败降级
        logger.exception("资料原件读取异常")
        return None


def _roles_of(ctx: JobContext) -> dict[str, list[str]]:
    """构造 file_id → 角色映射：上传资料按记录，登记数据虚拟块固定为 database，
    人工补充说明固定为 supplement，二者对模板全部槽位始终可见。"""
    roles = {f.file_id: [f.role] for f in ctx.files}
    for block in ctx.blocks:
        if block.file_id.startswith(DB_FILE_PREFIX):
            roles.setdefault(block.file_id, [DATABASE_ROLE])
        elif block.file_id == SUPPLEMENT_FILE_ID:
            roles.setdefault(block.file_id, [SUPPLEMENT_ROLE])
    return roles


async def _project_database_blocks(session: AsyncSession, job: DocGenJob) -> list[TextBlock]:
    """项目登记结构化数据 → 虚拟资料块（role=database）。

    登记数据（品种名、CAS 号、分子式等）是内部权威事实，注入后可以像普通资料一样
    被检索召回并作为取值依据；文件 id 用 db: 前缀，提取层据此豁免引用回检。
    """
    if job.project_id is None:
        return []
    project = await session.get(rd_models.RdProject, job.project_id)
    if project is None or project.is_deleted:
        return []
    fields: list[tuple[str, str]] = [
        ("品种名称", project.name or ""),
        ("API全称", project.api_name or ""),
        ("CAS号", project.cas_number or ""),
        ("分子式", project.molecular_formula or ""),
        ("分子量", "" if project.molecular_weight is None else f"{project.molecular_weight:g}"),
        ("适应症", project.indication or ""),
        ("项目类型", project.project_type or ""),
        ("当前阶段", project.current_stage or project.status or ""),
        ("总体进度", "" if project.overall_progress is None else f"{project.overall_progress:g}%"),
        ("开始日期", str(project.start_date) if project.start_date else ""),
        ("目标申报日期", str(project.target_filing_date) if project.target_filing_date else ""),
        ("实际申报日期", str(project.actual_filing_date) if project.actual_filing_date else ""),
        ("备注", (project.notes or "").strip()),
    ]
    lines = [f"{label}：{value}" for label, value in fields if value]
    if not lines:
        return []
    logger.info(
        "项目登记数据注入任务资料", extra={"job_id": str(job.id), "fields": len(lines), "module_name": "research"}
    )
    text = "【项目登记数据】\n" + "\n".join(lines)
    return [TextBlock(file_id=f"db:{project.id}", page=1, index=0, text=text, kind="paragraph")]


async def _enrich_spec(ctx: JobContext, config: RuntimeConfig) -> None:
    """AI 辅助标注：为自动识别模板里缺检索词的槽位补同义词（失败静默降级）。

    读模板结构属于「模板模型」的职责，与提取/成文分走不同配置。
    """
    choice = await resolve_model(config.template_model_name)
    enriched = await enrich_search_terms(
        ctx.spec,
        timeout_seconds=config.llm_call_timeout_seconds,
        llm_kwargs={"model_override": choice.model_override, "config_name": choice.config_name},
    )
    if enriched:
        logger.info("槽位检索词 AI 标注完成", extra={"job_id": str(ctx.job.id), "slots": enriched})


async def _template_analysis_stage(
    session: AsyncSession,
    ctx: JobContext,
    config: RuntimeConfig,
    handle: AbortHandle | None = None,
) -> None:
    """模板分析阶段：用 LLM 解析模板结构，输出每槽位的抽取指引。

    在 spec 解析之后、文件解析之前运行。分析结果写回 spec 实例（增强 search_terms），
    同时存入 ctx.template_analysis 供后续文件分析阶段使用。
    失败时静默降级，不影响任务继续。
    """
    if not config.template_analysis_enabled:
        return
    job = ctx.job
    job.step = "AI 分析模板结构"
    await session.commit()

    choice = await resolve_model(config.template_model_name)
    analysis = await analyze_template(
        ctx.spec,
        timeout_seconds=config.llm_call_timeout_seconds,
        llm_kwargs={"model_override": choice.model_override, "config_name": choice.config_name},
    )
    ctx.template_analysis = analysis
    if analysis.failed:
        return

    # 把分析结果应用到 spec（增强空 search_terms 的槽位）
    applied = apply_analysis_to_spec(ctx.spec, analysis)
    if applied:
        logger.info(
            "模板分析增强检索词",
            extra={"job_id": str(job.id), "enhanced_slots": applied},
        )
    job.step = "模板分析完成"
    await session.commit()


async def _file_analysis_stage(
    session: AsyncSession,
    ctx: JobContext,
    config: RuntimeConfig,
    handle: AbortHandle | None = None,
) -> None:
    """文件分析阶段：异步逐文件读取，用 LLM 提取与模板匹配的结构化摘要。

    在文件解析之后、提取阶段之前运行。对每个已解析的文件并发调用 LLM，
    输出文件-槽位关联矩阵，供提取阶段作为增强上下文。
    失败时静默降级，提取阶段走原有检索策略。
    """
    if not config.file_analysis_enabled:
        return
    if not ctx.blocks:
        return
    job = ctx.job
    job.step = "AI 逐文件分析内容"
    await session.commit()

    # 使用模板分析产物作为指引；如果没有模板分析结果，用 spec 的槽位构建基础指引
    guides = {}
    if ctx.template_analysis and ctx.template_analysis.guides:
        guides = ctx.template_analysis.guides
    else:
        # 降级：从 spec 构建基础指引
        from app.modules.research.doc_gen.template_analyzer import SlotGuide

        for slot in ctx.spec.slots:
            if not slot.from_meta and not slot.manual_only and slot.kind in {"field", "paragraph", "table"}:
                guides[slot.key] = SlotGuide(
                    key=slot.key,
                    key_indicators=list(slot.search_terms),
                    content_pattern=slot.query_hint,
                )

    choice = await resolve_model(config.template_model_name)

    async def _on_progress(done: int, total: int) -> None:
        if handle and handle.should_cancel():
            return
        job.step = f"AI 分析文件内容（{done}/{total}）"
        job.progress = 15 + int(10 * done / max(1, total))
        await session.commit()

    # 构建 file_id → original_filename 映射
    file_names_map = {f.file_id: f.original_filename for f in ctx.files}
    batch_result = await analyze_files(
        ctx.blocks,
        template_guides=guides,
        file_names=file_names_map,
        timeout_seconds=config.llm_call_timeout_seconds,
        llm_kwargs={"model_override": choice.model_override, "config_name": choice.config_name},
        concurrency=config.file_analysis_concurrency,
        should_cancel=handle.should_cancel if handle is not None else None,
        on_progress=_on_progress,
    )
    ctx.file_analysis = batch_result
    logger.info(
        "文件分析阶段完成",
        extra={
            "job_id": str(job.id),
            "analyzed": batch_result.total_analyzed,
            "failed": batch_result.total_failed,
            "slots_with_content": len(batch_result.slot_to_files),
        },
    )


async def _cross_validation_stage(
    session: AsyncSession,
    ctx: JobContext,
    config: RuntimeConfig,
    handle: AbortHandle | None = None,
) -> None:
    """交叉校验阶段：对比文件分析摘要与槽位提取结果，标记不一致。

    在提取阶段完成后运行。用 LLM 对比两个阶段的产物，发现潜在遗漏或冲突。
    校验结果作为告警写入任务统计，供人工复核时参考。
    失败时静默降级。
    """
    if not config.cross_validation_enabled:
        return
    if ctx.file_analysis is None or ctx.file_analysis.total_analyzed == 0:
        return
    if not ctx.results:
        return

    job = ctx.job
    job.step = "AI 交叉校验提取结果"
    await session.commit()

    choice = await resolve_model(config.template_model_name)
    result = await validate_extraction(
        ctx.file_analysis,
        ctx.results,
        timeout_seconds=config.llm_call_timeout_seconds,
        llm_kwargs={"model_override": choice.model_override, "config_name": choice.config_name},
    )
    ctx.cross_validation = result

    # 把校验告警写入任务统计
    if result.warnings:
        if job.stats is None:
            job.stats = {}
        existing_warnings = job.stats.get("warnings", [])
        if isinstance(existing_warnings, list):
            existing_warnings.extend(result.warnings)
        else:
            job.stats["warnings"] = list(result.warnings)
        job.stats["validation_misses"] = result.potential_misses
        job.stats["validation_conflicts"] = result.potential_conflicts
        logger.warning(
            "交叉校验发现不一致",
            extra={
                "job_id": str(job.id),
                "misses": result.potential_misses,
                "conflicts": result.potential_conflicts,
            },
        )
    job.step = "校验完成"
    await session.commit()


_VISION_PROMPT = (
    "请从以下文件页面的图片中提取全部可读文字，保持原有段落与表格结构。"
    "只输出提取到的文字，不要添加解释或评论。"
    "如果确实无法识别任何文字，请只输出：[无法识别]"
)


@contextlib.contextmanager
def _materialize(data: bytes, suffix: str) -> Iterator[Path]:
    """把对象存储里的字节落到一个带正确后缀的临时文件，供同步解析库读取。

    解析库（pdfplumber/openpyxl/python-docx…）只吃文件路径，而类型判定又依赖后缀，
    所以临时文件必须保留原始后缀；用完即删，不在磁盘上留残留。
    """
    fd, raw = tempfile.mkstemp(prefix="docgen-src-", suffix=suffix or "")
    path = Path(raw)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        yield path
    finally:
        path.unlink(missing_ok=True)


async def _parse_with_library(
    record: DocGenInputFile,
    data: bytes,
    config: RuntimeConfig,
    handle: AbortHandle | None,
    *,
    ocr_structured: bool = False,
) -> tuple[list[TextBlock], list[str], int]:
    """兜底链第一/二级：用专用提取库解析（doc_gen/parsing.py）。

    覆盖 PDF 文字层、Office、OpenDocument、CSV/JSON/XML/HTML、RTF、纯文本，
    以及扫描页与图片的 OCR；``ocr_structured=True`` 时 OCR 改走 PP-StructureV3 输出
    Markdown，保留表格与版式（比快速 OCR 慢数倍，只在第二级启用）。
    """
    suffix = Path(record.original_filename).suffix.lower()
    with _materialize(data, suffix) as path:
        result = await parse_file(
            path,
            file_id=record.file_id,
            role=record.role or "material",
            max_chars=MAX_PARSE_CHARS,
            max_pages=config.max_pages_per_file,
            max_ocr_pages=config.max_ocr_pages_per_file,
            mime_hint=record.mime_type,
            timeout_seconds=config.parse_timeout_seconds,
            should_cancel=handle.should_cancel if handle is not None else None,
            ocr_structured=ocr_structured,
        )
    warnings = list(result.warnings)
    if result.aborted == "timeout":
        warnings.append("库解析超时，已强制终止")
    logger.info(
        "库解析结束",
        extra={
            "job_id": str(record.job_id),
            "file_id": record.file_id,
            "format": result.format_name,
            "ocr_structured": ocr_structured,
            "blocks": len(result.blocks),
            "chars": result.char_count,
        },
    )
    return list(result.blocks), warnings, max(0, result.page_count)


def _compress_image_for_vision(image: Any, quality: int, max_width: int) -> bytes:
    """压缩图片供视觉模型调用：限制宽度 + 转 JPEG，大幅减少 base64 体积。

    视觉模型对清晰度要求不高（只需读出文字），JPEG 60% 质量 + 1600px 宽度通常能把
    单页体积从 2-5MB PNG 压到 100-300KB，token 数降一个数量级。
    """
    from PIL import Image

    # 等比缩放：宽度超过上限时按比例缩小
    if image.width > max_width:
        ratio = max_width / image.width
        new_size = (max_width, int(image.height * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    # 转 RGB（JPEG 不支持 alpha 通道）
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()


async def _parse_with_vision(
    record: DocGenInputFile,
    data: bytes,
    config: RuntimeConfig,
) -> tuple[list[TextBlock], list[str], int]:
    """兜底链第三级：把页面转成图片交给视觉模型。

    只对「图片」与「PDF」生效——其它二进制格式转不了图，硬送过去模型看到的是
    一团 base64，读不出任何东西（这正是旧实现失败的根因）。

    图片会压缩（JPEG + 限宽）后再 base64，避免多页 PDF 的 token 数超模型 context window。
    """
    import base64

    from app.core.llm import llm_client

    suffix = Path(record.original_filename).suffix.lower()
    warnings: list[str] = []
    data_uris: list[str] = []
    page_count = 0
    try:
        with _materialize(data, suffix) as path:
            if suffix in IMAGE_EXTENSIONS:
                from PIL import Image

                img = Image.open(path)
                compressed = _compress_image_for_vision(img, config.vision_image_quality, config.vision_max_width)
                data_uris = [f"data:image/jpeg;base64,{base64.b64encode(compressed).decode('ascii')}"]
                page_count = 1
            elif suffix == ".pdf":
                from pdf2image import convert_from_path

                images = await _run_blocking(
                    convert_from_path,
                    str(path),
                    dpi=120,
                    first_page=1,
                    last_page=max(1, config.vision_max_pages),
                    timeout_seconds=config.parse_timeout_seconds,
                )
                for image in images:
                    compressed = _compress_image_for_vision(image, config.vision_image_quality, config.vision_max_width)
                    data_uris.append(f"data:image/jpeg;base64,{base64.b64encode(compressed).decode('ascii')}")
                page_count = len(data_uris)
            else:
                return [], [], 0
    except TimeoutError:
        warnings.append("页面转图超时，已跳过视觉模型兜底")
        return [], warnings, 0
    except Exception as exc:  # noqa: BLE001 - 兜底链路里的失败一律降级，不能拖垮任务
        logger.warning("页面转图失败，已跳过视觉模型兜底", extra={"file_name": record.original_filename})
        warnings.append(f"页面转图失败（{type(exc).__name__}），已跳过视觉模型兜底")
        return [], warnings, 0

    if not data_uris:
        return [], warnings, 0

    # 动态计算 max_tokens：模型 context window 减去预估 input tokens，留 2048 给输出
    # base64 编码后 1 token ≈ 3 字节，图片 token 数 ≈ (总字节数 / 3) / 4（JPEG 压缩后）
    total_bytes = sum(len(uri.split(",", 1)[1]) * 3 // 4 for uri in data_uris if "," in uri)
    estimated_input_tokens = max(1000, int(total_bytes / 3))  # 保守估计
    model_context = 32768  # 大多数 vision 模型的 context window
    max_output_tokens = max(1024, min(8192, model_context - estimated_input_tokens - 2048))

    try:
        text = await asyncio.wait_for(
            llm_client.chat_vision(_VISION_PROMPT, data_uris, max_tokens=max_output_tokens),
            timeout=max(5, config.llm_call_timeout_seconds),
        )
    except TimeoutError:
        warnings.append("视觉模型调用超时")
        return [], warnings, 0
    except Exception as exc:  # noqa: BLE001 - 未登记 vision 配置时必然抛错，属预期降级
        logger.warning(
            "视觉模型兜底不可用",
            extra={"file_name": record.original_filename, "error": type(exc).__name__},
        )
        warnings.append(f"视觉模型不可用（{type(exc).__name__}）")
        return [], warnings, 0

    if not text or "[无法识别]" in text:
        warnings.append("视觉模型未能识别出文字")
        return [], warnings, 0

    blocks: list[TextBlock] = []
    char_count = 0
    for idx, line in enumerate(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        if char_count + len(line) > MAX_PARSE_CHARS:
            warnings.append("视觉模型提取内容超出字符上限，已截断")
            break
        blocks.append(TextBlock(file_id=record.file_id, page=1, index=idx, text=line, kind="paragraph"))
        char_count += len(line)
    if not blocks:
        warnings.append("视觉模型未提取到有效文字")
        return [], warnings, 0
    warnings.append("已使用视觉模型识别页面文字")
    return blocks, warnings, page_count


async def _parse_one(
    record: DocGenInputFile, config: RuntimeConfig, handle: AbortHandle | None = None
) -> tuple[list[TextBlock], list[str], int]:
    """解析单个资料文件为文本块，返回 (文本块, 告警, 页数)。

    **分级兜底链**：解析的可靠性是整个文档生成的地基——解析不出文字，后面所有槽位
    都是空的。因此按「确定性高、零成本」到「不确定、有成本」逐级降级：

    1. **库解析**（``doc_gen/parsing.py``）：PDF 文字层 / Office / 表格 / 纯文本，
       扫描页与图片顺带走快速 OCR；
    2. **结构化 OCR**：上一步无结果时改用 PP-StructureV3 出 Markdown，保留表格与版式
       （``DOC_GEN_OCR_STRUCTURED_ENABLED``，默认关，因为它慢）；
    3. **视觉模型**：页面转图交给 vision 模型（``DOC_GEN_VISION_FALLBACK_ENABLED``）；
    4. **明确失败**：给出「另存为 .docx / 文本版 PDF」的可执行提示，而不是静默留空槽位。

    曾经的写法是把 Office 等二进制格式 base64 后塞进 prompt 让模型「提取文字」——
    LLM 不是 zip/OLE 解码器，只能回「无法识别」，或者更糟：编出一段看着合理的文字；
    而这条路径没有回检，编造值会直接落进槽位。模型擅长读文字，不擅长解码容器，
    所以一律先转成文字再交给模型。
    """
    data = await _load_object(record.object_key, config.parse_timeout_seconds)
    if data is None:
        record.parse_status = "failed"
        record.warnings = ["资料文件读取失败（存储不可用或文件缺失）"]
        return [], [f"{record.original_filename}：文件读取失败"], 0

    # 检查是否被取消
    if handle is not None and handle.should_cancel():
        record.parse_status = "failed"
        record.warnings = ["任务已取消"]
        return [], [f"{record.original_filename}：任务已取消"], 0

    suffix = Path(record.original_filename).suffix.lower()
    # 只有这两类可能「有画面但没文字层」，值得再花 OCR / 视觉调用去兜底
    needs_visual_fallback = suffix in IMAGE_EXTENSIONS or suffix == ".pdf"

    logger.info(
        "开始解析资料文件",
        extra={"job_id": str(record.job_id), "file_id": record.file_id, "file_name": record.original_filename},
    )

    attempted = ["库解析"]
    blocks, warnings, page_count = await _parse_with_library(record, data, config, handle)

    if not blocks and needs_visual_fallback and config.ocr_structured_enabled:
        attempted.append("结构化OCR")
        blocks, warnings, page_count = await _parse_with_library(record, data, config, handle, ocr_structured=True)

    if not blocks and needs_visual_fallback and config.vision_fallback_enabled:
        attempted.append("视觉模型")
        vision_blocks, vision_warnings, vision_pages = await _parse_with_vision(record, data, config)
        if vision_blocks:
            blocks, warnings, page_count = vision_blocks, vision_warnings, vision_pages
        else:
            warnings = warnings + vision_warnings

    if not blocks:
        warnings = warnings + ["所有解析通道均未提取到文字，建议另存为 .docx 或带文字层的 PDF 后重新上传"]

    record.page_count = page_count
    record.char_count = sum(len(b.text) for b in blocks)
    record.warnings = warnings
    record.parse_status = "done" if blocks else "failed"

    logger.info(
        "资料解析结束",
        extra={
            "job_id": str(record.job_id),
            "file_id": record.file_id,
            "channels": "→".join(attempted),
            "blocks": len(blocks),
            "chars": record.char_count,
            "status": record.parse_status,
        },
    )
    prefixed_warnings = [f"{record.original_filename}：{w}" for w in warnings]
    return blocks, prefixed_warnings, page_count


async def _extract_stage(
    session: AsyncSession,
    ctx: JobContext,
    config: RuntimeConfig,
    handle: AbortHandle | None = None,
    slots: Sequence[Slot] | None = None,
    progress_from: int = 20,
    progress_to: int = 80,
    step_label: str = "AI 分析资料",
) -> None:
    """槽位取值 + 元数据槽位回填。

    ``slots`` 为空时抽取整份模板（骨架槽位），传入子集则只抽这些槽位并把结果
    合并进已有结果——动态章节的局部槽位在实例化之后才知道有哪些。

    当向量检索启用时，先构建向量索引（批量 embedding），再传给 SlotExtractor
    做双路召回（关键词 + 向量融合）。
    """
    job = ctx.job
    incremental = slots is not None
    job.status = "extracting"
    job.step = step_label
    # 记录提取开始时间
    import time
    ctx.extract_start_time = time.time()
    await session.commit()
    roles = _roles_of(ctx)
    # 提取阶段用「提取模型」：命中登记的 LLM 配置则整份切换（端点+密钥），否则按同名覆盖
    choice = await resolve_model(config.extract_model_name)
    # 辅助模型（强模型）兜底：主模型（快模型）重试失败后切换
    fallback_choice = await resolve_model(config.fallback_model_name) if config.fallback_model_name else None

    # 向量索引构建（可选）：后台异步构建，与首批提取重叠执行
    # 首批提取会用纯关键词检索（is_built=False），后续批次自动切换双路召回
    vector_index = None
    embedding_model = None
    vector_build_task: asyncio.Task[None] | None = None
    if config.vector_retrieval_enabled and config.embedding_model_name:
        from app.core.llm import llm_client
        from app.modules.research.doc_gen.vector_retrieval import VectorIndex

        async def _embed_fn(texts: list[str]) -> list[list[float]]:
            return await llm_client.embed(texts, model_override=config.embedding_model_name)

        vector_index = VectorIndex(ctx.blocks, embed_fn=_embed_fn)

        async def _build_vector_index() -> None:
            try:
                await vector_index.build(batch_size=32)  # type: ignore[union-attr]
                logger.info(
                    "向量索引构建完成", extra={"blocks": len(ctx.blocks), "model": config.embedding_model_name}
                )
            except Exception:
                logger.exception("向量索引构建失败，退化为纯关键词检索")

        vector_build_task = asyncio.create_task(_build_vector_index())
        embedding_model = config.embedding_model_name

    # 构建文件分析上下文：为每个槽位提供预提取内容参考
    file_analysis_context: dict[str, list[dict[str, Any]]] = {}
    if ctx.file_analysis is not None:
        for slot in ctx.spec.slots:
            if slot.from_meta or slot.manual_only:
                continue
            items = build_file_analysis_context(ctx.file_analysis, slot.key, max_files=2)
            if items:
                file_analysis_context[slot.key] = items

    extractor = SlotExtractor(
        ctx.spec,
        ctx.blocks,
        roles_by_file=roles,
        batch_size=config.batch_size,
        candidate_limit=config.candidate_limit,
        max_context_chars=config.context_chars,
        confidence_high=config.confidence_high,
        confidence_mid=config.confidence_mid,
        max_retries=max(1, config.max_attempts),
        should_cancel=handle.should_cancel if handle is not None else None,
        call_timeout_seconds=config.llm_call_timeout_seconds,
        model_override=choice.model_override,
        config_name=choice.config_name,
        max_concurrent_batches=config.extract_concurrency,
        enable_cache=config.extract_cache_enabled,
        vector_index=vector_index,
        vector_alpha=config.vector_alpha,
        embedding_model=embedding_model,
        fallback_model_override=fallback_choice.model_override if fallback_choice else None,
        fallback_config_name=fallback_choice.config_name if fallback_choice else None,
        file_analysis_context=file_analysis_context or None,
    )
    # 提取器的进度基数固定按整份模板算，这里换算到本次调用的进度带
    band = max(1, progress_to - progress_from)

    # 计算总批次数供进度展示：简单槽位按 batch_size 分批 + 每个表格槽位单独一批
    simple_targets = [s for s in (slots or list(ctx.spec.slots)) if s.kind != "table" and not s.from_meta]
    table_targets = [s for s in (slots or list(ctx.spec.slots)) if s.kind == "table" and not s.from_meta]
    total_batches = (len(simple_targets) + max(1, config.batch_size) - 1) // max(1, config.batch_size) + len(
        table_targets
    )
    completed_batches = 0

    async def on_progress(done: int, total: int) -> None:
        nonlocal completed_batches
        # 进度回调是提取循环里唯一能查数据库的检查点。这里必须把取消转成 ExtractionAbortError
        # 抛出——extractor 对进度回调有兜底 try，普通异常会被当成「回调写库失败」吞掉，
        # 那样取消就永远不生效。
        try:
            await _check_cancelled(session, job, handle)
        except JobAbortedError as exc:
            raise ExtractionAbortError(exc.code) from exc
        completed_batches = min(completed_batches + 1, total_batches)
        job.progress = progress_from + int(band * done / max(1, total))
        job.step = f"{step_label} 第{completed_batches}/{total_batches}批 {done}/{total}项"
        await session.commit()

    try:
        extracted = await extractor.run(on_progress=on_progress, slots=slots)
    except ExtractionAbortError as exc:
        raise JobAbortedError(exc.reason or "cancelled", "提取已终止") from exc
    finally:
        # 确保向量索引后台任务结束，释放资源
        if vector_build_task is not None and not vector_build_task.done():
            vector_build_task.cancel()
            try:
                await vector_build_task
            except (asyncio.CancelledError, Exception):
                pass
    if incremental:
        ctx.results.update(extracted)
    else:
        ctx.results = extracted
        for key, value in _meta_values(job, ctx).items():
            ctx.results[key] = SlotResult(key=key, text=value, state=status.STATUS_OK)
    ctx.warnings.extend(extractor.stats.warnings)
    ctx.extract_stats = extractor.stats
    await session.commit()
    if extractor.stats.failures:
        ctx.warnings.append(f"模型调用降级 {extractor.stats.failures} 次，相关填充项需人工确认")
    # 质量检查：所有提取的槽位全部失败时，任务没有继续下去的意义
    non_meta = {k: v for k, v in ctx.results.items() if not k.startswith("meta.")}
    if non_meta and all(r.state == status.STATUS_FAILED for r in non_meta.values()):
        raise JobAbortedError(
            "extract_all_failed",
            "所有填充项均提取失败（模型调用可能不可用），请检查 LLM 配置后重试",
        )
    job.progress = progress_to
    await session.flush()


async def _direct_generate_stage(
    session: AsyncSession, ctx: JobContext, config: RuntimeConfig, handle: AbortHandle | None = None
) -> None:
    """直接生成模式：一次性把全部资料文本交给 LLM，直接生成所有填充项内容。

    替代 _extract_stage + _compose_stage，将 LLM 调用从 30+ 次降到 1 次。
    适用于对速度要求高于对逐槽位证据追溯要求的场景。
    """
    job = ctx.job
    await _check_cancelled(session, job, handle)
    job.status = "extracting"
    job.step = "AI 一次性生成报告内容"
    job.progress = 20
    await session.commit()

    import time
    ctx.extract_start_time = time.time()

    # 解析模型选择
    choice = await resolve_model(config.write_model_name)

    # 收集补充信息
    supplement_text = (job.supplement_text or "").strip()

    # file_id → 原始文件名映射，用于资料来源标注
    file_names = {f.file_id: f.original_filename for f in ctx.files}

    # 调用直接生成
    results, gen_stats = await direct_generate(
        ctx.spec,
        ctx.blocks,
        max_chars=config.direct_gen_max_chars,
        timeout_seconds=config.llm_call_timeout_seconds,
        model_override=choice.model_override,
        config_name=choice.config_name,
        supplement_text=supplement_text,
        file_names=file_names,
        should_cancel=handle.should_cancel if handle is not None else None,
    )

    # 回填元数据槽位
    for key, value in _meta_values(job, ctx).items():
        results[key] = SlotResult(key=key, text=value, state=status.STATUS_OK)

    ctx.results = results

    # 把直接生成统计映射到 ExtractStats（复用现有字段）
    ctx.extract_stats = ExtractStats(
        calls=gen_stats.calls,
        failures=gen_stats.failures,
        retrieval_misses=0,
        low_confidence=0,
    )

    if gen_stats.failures:
        ctx.warnings.append("直接生成模式 LLM 调用失败，相关填充项需人工确认")

    # 质量检查：所有槽位都失败时中止
    non_meta = {k: v for k, v in ctx.results.items() if not k.startswith("meta.")}
    if non_meta and all(r.state == status.STATUS_FAILED for r in non_meta.values()):
        raise JobAbortedError(
            "extract_all_failed",
            "直接生成模式所有填充项均失败（模型调用可能不可用），请检查 LLM 配置后重试",
        )

    job.progress = 65
    await session.flush()

    logger.info(
        "直接生成阶段完成",
        extra={
            "job_id": str(job.id),
            "calls": gen_stats.calls,
            "failures": gen_stats.failures,
            "source_chars": gen_stats.source_chars,
            "results": gen_stats.result_count,
        },
    )


async def _instantiate_stage(session: AsyncSession, ctx: JobContext, handle: AbortHandle | None = None) -> None:
    """触发判定 → 章节实例化 → 展开局部槽位。

    整步是纯确定性计算，不调用模型；触发求值异常只降级为「该章节不出现」并记告警，
    判定依据随章节落库，供复核界面显示「为何出现 / 为何不出现」。
    """
    job = ctx.job
    await _check_cancelled(session, job, handle)
    job.step = "确定章节结构"
    ctx.job.progress = 72
    await session.commit()
    trigger_ctx = build_trigger_context(
        results=ctx.results,
        blocks=ctx.blocks,
        roles=_roles_of(ctx),
        meta=dict(job.meta or {}),
    )
    outcome = instantiate(ctx.spec, trigger_ctx)
    ctx.sections = outcome.instances
    ctx.section_titles = {instance.section_key: instance.title for instance in outcome.instances}
    ctx.warnings.extend(f"章节结构：{warn}" for warn in outcome.warnings)
    logger.info(
        "章节结构确定",
        extra={
            "job_id": str(job.id),
            "sections": len(outcome.instances),
            "titles": [s.title for s in outcome.instances][:10],
            "warnings": len(outcome.warnings),
        },
    )
    await session.flush()


def _meta_values(job: DocGenJob, ctx: JobContext) -> dict[str, str]:
    """任务元数据槽位（受控编码、版本号、品种名等，人工在表单里填一次）。"""
    meta: dict[str, Any] = dict(job.meta or {})
    fallback_name = str(meta.get("project_name") or meta.get("drug_name") or "").strip()
    values: dict[str, str] = {}
    for slot in ctx.spec.slots:
        if not slot.from_meta:
            continue
        raw = str(meta.get(slot.key) or "").strip()
        if not raw and slot.key == "drug_name":
            raw = fallback_name
        values[slot.key] = raw or status.pending("生成时未提供该信息")
    return values


async def _render_stage(session: AsyncSession, ctx: JobContext, handle: AbortHandle | None = None) -> None:
    """渲染 docx 与生成说明，写回任务行。"""
    job = ctx.job
    await _check_cancelled(session, job, handle)
    job.status = "rendering"
    job.step = "填充模板"
    await session.commit()
    # 母本优先级：任务指定的交付物模板 → 同槽位定义下最近的母本 → 代码内置母本
    meta = dict(ctx.job.meta or {})
    master = await store.load_master_by_id(str(meta.get("deliverable_template_id") or ""))
    if master is None:
        master = await store.load_master_by_code(ctx.spec.code)
    if master is None:
        master = await _run_blocking(store.load_master, ctx.spec.master_asset)
    if master is None:
        raise JobAbortedError("master_missing", f"Word 模板原件缺失：{ctx.spec.master_asset}")
    values = {key: SlotValue(text=r.text, rows=r.rows, state=r.state) for key, r in ctx.results.items()}
    plans = _section_plans(ctx)
    docx, report = await _run_blocking(render_document, master, ctx.spec, values, plans)
    report.warnings.extend(ctx.warnings)
    filenames = {f.file_id: f.original_filename for f in ctx.files}
    for block in ctx.blocks:
        if block.file_id.startswith(DB_FILE_PREFIX):
            filenames.setdefault(block.file_id, "项目登记数据")
        elif block.file_id == SUPPLEMENT_FILE_ID:
            filenames.setdefault(block.file_id, "人工补充说明")
    markdown = build_report_markdown(
        ctx.spec,
        ctx.results,
        report,
        filenames=filenames,
        project_name=str((job.meta or {}).get("project_name") or ""),
        sections=ctx.sections,
    )
    job.docx_object_key = await _run_blocking(store.save_bytes, "document.docx", docx, DOCX_MIME)
    job.report_object_key = await _run_blocking(
        store.save_bytes, "report.md", markdown.encode("utf-8"), "text/markdown"
    )
    if (job.docx_object_key or "").startswith("local:") or (job.report_object_key or "").startswith("local:"):
        # 对象存储不可用时是静默降级，必须在生成说明里让使用者看得见文件落在哪台机器上
        ctx.warnings.append("对象存储（MinIO）不可用，产物已降级保存到应用服务器本地 uploads 目录，请尽快下载留存")
    await _persist_slot_values(session, job, ctx)
    # 统计口径：written 会把 [待补充] 占位也算进去，不能当「实质内容」用，
    # 因此按槽位状态额外给出 实质内容/待补充/需人工 三个口径，供前端与生成说明统一引用。
    state_counts = summarize_states(list(ctx.results.values()))
    job.stats = {
        "written": report.written,
        "substantive": state_counts.get(status.STATUS_OK, 0),
        "pending": state_counts.get(status.STATUS_PENDING, 0) + state_counts.get(status.STATUS_FAILED, 0),
        "manual": state_counts.get(status.STATUS_MANUAL, 0),
        "drafts": state_counts.get(status.STATUS_DRAFT, 0),
        "conflicts": state_counts.get(status.STATUS_CONFLICT, 0),
        "needs_verify": state_counts.get(status.STATUS_NEEDS_VERIFY, 0),
        "retrieval_misses": ctx.extract_stats.retrieval_misses,
        "low_confidence": ctx.extract_stats.low_confidence,
        "composed": ctx.compose_stats.composed if ctx.compose_stats else 0,
        "compose_rejected": ctx.compose_stats.rejected if ctx.compose_stats else 0,
        "unresolved": len(report.unresolved),
        "occupied": len(report.occupied),
        "overflow": len(report.overflow),
        "slot_states": state_counts,
        "toc_paragraphs": report.toc_paragraphs,
        "sections_total": len(ctx.sections),
        "sections_added": report.sections_added,
        "sections_skipped": len(report.sections_skipped),
        "section_titles": report.section_titles,
        "warnings": ctx.warnings,
    }
    ctx.render_report = report
    job.status = "completed"
    job.step = "完成"
    job.progress = 100
    job.finished_at = _now()


async def _persist_slot_values(session: AsyncSession, job: DocGenJob, ctx: JobContext) -> None:
    """写入槽位结果（重跑先清掉上一次，保证一个任务一套结果）。

    章节槽位的 key 带实例前缀，落库时另存 ``section_key``/``instance_index`` 两列，
    这样既保持链路上下文的 key 语义不变，又能按章节查询。
    """
    labels = {slot.key: slot.label for slot in ctx.spec.slots}
    labels.update({slot.key: slot.label for instance in ctx.sections for slot in instance.slots})
    await session.execute(delete(DocGenSlotValue).where(DocGenSlotValue.job_id == job.id))
    rows = []
    for result in ctx.results.values():
        section_key, raw_key = split_slot_key(result.key)
        rows.append(
            DocGenSlotValue(
                job_id=job.id,
                slot_key=result.key,
                section_key=section_key,
                instance_index=_instance_index(section_key),
                label=labels.get(result.key, raw_key),
                text=result.text,
                rows=result.rows,
                state=result.state,
                reason=result.reason or None,
                confidence=result.confidence,
                evidence=[e.model_dump() for e in result.evidence],
                candidates=result.candidates,
                pre_compose_text=result.pre_compose_text or None,
            )
        )
    await repo.add_slot_values(session, rows)


async def _persist_sections(session: AsyncSession, job: DocGenJob, ctx: JobContext) -> None:
    """写入任务大纲（重跑先清掉上一次）。"""
    await session.execute(delete(DocGenSection).where(DocGenSection.job_id == job.id))
    if not ctx.sections:
        return
    rows = [
        DocGenSection(
            job_id=job.id,
            section_key=instance.section_key,
            fragment_key=instance.fragment_key,
            extension_point_key=instance.extension_point_key,
            parent_section_key=instance.parent_section_key,
            level=instance.level,
            title=instance.title,
            order_index=instance.order_index,
            source=instance.source,
            state=instance.state,
            trigger_trace=instance.trigger_trace,
        )
        for instance in ctx.sections
    ]
    await repo.add_sections(session, rows)


async def project_display_name(session: AsyncSession, project_id: uuid.UUID | None) -> str:
    """取项目名用于元数据回填（同模块内直接访问 ORM）。"""
    if project_id is None:
        return ""
    project = await session.get(rd_models.RdProject, project_id)
    return project.name if project is not None else ""
