"""文档生成数据访问。"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.research.doc_gen.models import (
    RUNNING_STATUSES as RUNNING_STATUSES,  # noqa: PLC0414 - 状态分组唯一来源在 models
)
from app.modules.research.doc_gen.models import (
    DocGenInputFile,
    DocGenJob,
    DocGenSection,
    DocGenSlotValue,
)

logger = logging.getLogger(__name__)

# 可被 worker 领取的状态：待提取 + 人工确认后续跑成文与渲染
CLAIMABLE_STATUSES = ("pending", "confirmed")


async def create_job(session: AsyncSession, job: DocGenJob) -> DocGenJob:
    """新增任务。"""
    session.add(job)
    await session.flush()
    return job


async def add_input_files(session: AsyncSession, files: Sequence[DocGenInputFile]) -> None:
    """批量新增资料记录。"""
    for item in files:
        session.add(item)
    await session.flush()


async def add_slot_values(session: AsyncSession, values: Sequence[DocGenSlotValue]) -> None:
    """批量写入槽位结果。"""
    for item in values:
        session.add(item)
    await session.flush()


async def add_sections(session: AsyncSession, sections: Sequence[DocGenSection]) -> None:
    """批量写入章节实例（任务大纲）。"""
    for item in sections:
        session.add(item)
    await session.flush()


async def list_sections(session: AsyncSession, job_id: uuid.UUID) -> Sequence[DocGenSection]:
    """任务的大纲，按渲染顺序返回。"""
    result = await session.execute(
        select(DocGenSection)
        .where(DocGenSection.job_id == job_id, DocGenSection.is_deleted.is_(False))
        .order_by(DocGenSection.order_index, DocGenSection.section_key)
    )
    return result.scalars().all()


async def get_job(session: AsyncSession, job_id: uuid.UUID) -> DocGenJob | None:
    """按 ID 取任务。"""
    result = await session.execute(
        select(DocGenJob).where(DocGenJob.id == job_id, DocGenJob.is_deleted.is_(False))
    )
    return result.scalar_one_or_none()


async def list_jobs_by_report(session: AsyncSession, report_id: uuid.UUID) -> Sequence[DocGenJob]:
    """某报告下的历次生成任务（新→旧）。"""
    result = await session.execute(
        select(DocGenJob)
        .where(DocGenJob.report_id == report_id, DocGenJob.is_deleted.is_(False))
        .order_by(DocGenJob.created_at.desc())
    )
    return result.scalars().all()


async def latest_jobs_by_reports(
    session: AsyncSession, report_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, DocGenJob]:
    """批量取每个报告的最新一次生成任务，避免列表页 N+1 查询。"""
    if not report_ids:
        return {}
    result = await session.execute(
        select(DocGenJob)
        .where(DocGenJob.report_id.in_(list(report_ids)), DocGenJob.is_deleted.is_(False))
        .order_by(DocGenJob.report_id, DocGenJob.created_at.desc())
    )
    latest: dict[uuid.UUID, DocGenJob] = {}
    for job in result.scalars().all():
        if job.report_id is not None and job.report_id not in latest:
            latest[job.report_id] = job
    return latest


async def list_jobs_by_project(session: AsyncSession, project_id: uuid.UUID) -> Sequence[DocGenJob]:
    """某研发项目下的全部生成任务（列表页一次取回，避免逐报告查询）。"""
    result = await session.execute(
        select(DocGenJob)
        .where(DocGenJob.project_id == project_id, DocGenJob.is_deleted.is_(False))
        .order_by(DocGenJob.created_at.desc())
    )
    return result.scalars().all()


async def list_input_files(session: AsyncSession, job_id: uuid.UUID) -> Sequence[DocGenInputFile]:
    """任务的资料清单。"""
    result = await session.execute(
        select(DocGenInputFile).where(DocGenInputFile.job_id == job_id, DocGenInputFile.is_deleted.is_(False))
    )
    return result.scalars().all()


async def get_input_file(
    session: AsyncSession, job_id: uuid.UUID, file_id: uuid.UUID
) -> DocGenInputFile | None:
    """按 ID 取单条资料文件记录。"""
    result = await session.execute(
        select(DocGenInputFile).where(
            DocGenInputFile.id == file_id,
            DocGenInputFile.job_id == job_id,
            DocGenInputFile.is_deleted.is_(False),
        )
    )
    return result.scalar_one_or_none()


async def list_slot_values(session: AsyncSession, job_id: uuid.UUID) -> Sequence[DocGenSlotValue]:
    """任务的槽位结果清单。"""
    result = await session.execute(
        select(DocGenSlotValue)
        .where(DocGenSlotValue.job_id == job_id, DocGenSlotValue.is_deleted.is_(False))
        .order_by(DocGenSlotValue.slot_key)
    )
    return result.scalars().all()


async def claim_next_job(session: AsyncSession, lease_seconds: int, max_concurrency: int) -> DocGenJob | None:
    """按租约领取一个待处理任务；租约过期任务可被重新领取（重启不丢）。"""
    now = datetime.now(UTC)
    running = await session.scalar(
        select(func.count())
        .select_from(DocGenJob)
        .where(DocGenJob.status.in_(RUNNING_STATUSES), DocGenJob.lease_expires_at > now)
    )
    if (running or 0) >= max_concurrency:
        return None
    stale_lease = DocGenJob.status.in_(RUNNING_STATUSES) & (DocGenJob.lease_expires_at < now)
    result = await session.execute(
        select(DocGenJob)
        .where(
            DocGenJob.is_deleted.is_(False),
            DocGenJob.status.in_(CLAIMABLE_STATUSES) | stale_lease,
        )
        .order_by(DocGenJob.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    job = result.scalar_one_or_none()
    if job is None:
        return None
    job.status = job.status if job.status in RUNNING_STATUSES else "parsing"
    job.lease_expires_at = now + timedelta(seconds=lease_seconds)
    job.attempts += 1
    await session.flush()
    return job


async def list_failed_jobs(session: AsyncSession, max_attempts: int) -> Sequence[DocGenJob]:
    """列出可重试的失败任务。"""
    result = await session.execute(
        select(DocGenJob)
        .where(
            DocGenJob.status == "failed",
            DocGenJob.attempts < max_attempts,
            DocGenJob.is_deleted.is_(False),
        )
        .order_by(DocGenJob.created_at)
    )
    return result.scalars().all()


# ─────────────────────────── 取消 / 租约 / 恢复 ───────────────────────────

# 终态：不再被 worker 领取，也不允许被执行中的任务覆写
TERMINAL_STATUSES = ("completed", "ready", "failed", "cancelled")


async def read_status(session: AsyncSession, job_id: uuid.UUID) -> str | None:
    """直查数据库里的任务状态。

    必须走列查询而不是 ``session.get``：全局 session 工厂是 ``expire_on_commit=False``，
    ORM 身份映射会一直返回 worker 自己写的内存值，取消请求在库里改了也"看不见"。
    """
    value = await session.scalar(select(DocGenJob.status).where(DocGenJob.id == job_id))
    return str(value) if value is not None else None


async def cancel_requested(session: AsyncSession, job_id: uuid.UUID) -> bool:
    """外部是否已请求取消/终止该任务。"""
    return (await read_status(session, job_id)) == "cancelled"


async def heartbeat(session: AsyncSession, job_id: uuid.UUID, lease_seconds: int) -> None:
    """续租：长任务必须周期性刷新租约，否则超过租约时长会被其它进程重复领取造成双跑。"""
    await session.execute(
        update(DocGenJob)
        .where(DocGenJob.id == job_id)
        .values(lease_expires_at=datetime.now(UTC) + timedelta(seconds=lease_seconds))
    )
    await session.commit()


async def mark_cancelled(session: AsyncSession, job_id: uuid.UUID, step: str = "已取消") -> bool:
    """把任务落为已取消终态并释放租约。返回是否确实变更（已终态则不动）。"""
    result = await session.execute(
        update(DocGenJob)
        .where(DocGenJob.id == job_id, DocGenJob.status.notin_(TERMINAL_STATUSES))
        .values(status="cancelled", step=step, lease_expires_at=None, finished_at=datetime.now(UTC))
    )
    await session.commit()
    return bool(result.rowcount)  # type: ignore[attr-defined]


async def release_lease(session: AsyncSession, job_id: uuid.UUID) -> None:
    """释放租约（任务结束或转待确认时调用）。"""
    await session.execute(update(DocGenJob).where(DocGenJob.id == job_id).values(lease_expires_at=None))
    await session.commit()


async def recover_stale_jobs(session: AsyncSession) -> int:
    """启动恢复：把租约已失效却仍停在执行中状态的任务判为失败。

    worker 被热重载或 OOM 杀掉时，任务会永久停在 parsing/extracting，前端一直显示
    "提取中"，用户既等不到结果也分不清是否还在跑。启动时统一收口成失败（可重试）。
    """
    now = datetime.now(UTC)
    result = await session.execute(
        update(DocGenJob)
        .where(
            DocGenJob.status.in_(RUNNING_STATUSES),
            or_(DocGenJob.lease_expires_at.is_(None), DocGenJob.lease_expires_at < now),
        )
        .values(
            status="failed",
            step="执行中断",
            error_code="worker_restart_lost",
            error_message="服务重启或租约到期导致任务中断，请重新发起生成",
            lease_expires_at=None,
            finished_at=now,
        )
    )
    await session.commit()
    count = int(result.rowcount or 0)  # type: ignore[attr-defined]
    if count:
        logger.warning("启动恢复：已标记中断任务为失败", extra={"count": count})
    return count


async def finalize_job(session: AsyncSession, job_id: uuid.UUID, target: str, code: str, message: str) -> bool:
    """强制落终态（执行体被打断后由 worker 用独立 session 收尾）。

    保护规则：``ready`` 永不被覆写（产物已经生成，不能倒回去说它失败）；
    取消与失败互不覆写，谁先到终态算谁，避免前端状态在两者之间来回跳。
    """
    skip = ("ready", "completed") if target != "failed" else ("ready", "completed", "cancelled")
    result = await session.execute(
        update(DocGenJob)
        .where(DocGenJob.id == job_id, DocGenJob.status.notin_(skip))
        .values(
            status=target,
            step="已取消" if target == "cancelled" else "失败",
            error_code=code,
            error_message=message[:1000],
            lease_expires_at=None,
            finished_at=datetime.now(UTC),
        )
    )
    await session.commit()
    return bool(result.rowcount)  # type: ignore[attr-defined]


# ─────────────────────── 输入变更 / 重新提取 / 重新生成 ───────────────────────


async def list_jobs_by_parent(session: AsyncSession, job_id: uuid.UUID) -> Sequence[DocGenJob]:
    """某次任务之后重跑出来的任务（新→旧），用于展示重新生成次数。"""
    result = await session.execute(
        select(DocGenJob)
        .where(DocGenJob.parent_job_id == job_id, DocGenJob.is_deleted.is_(False))
        .order_by(DocGenJob.created_at.desc())
    )
    return result.scalars().all()


async def soft_delete_input_file(session: AsyncSession, job_id: uuid.UUID, file_id: uuid.UUID) -> bool:
    """删除任务下的一份资料（软删）。返回是否命中该任务下的文件。"""
    result = await session.execute(
        update(DocGenInputFile)
        .where(DocGenInputFile.id == file_id, DocGenInputFile.job_id == job_id)
        .values(is_deleted=True)
    )
    await session.flush()
    return bool(result.rowcount)  # type: ignore[attr-defined]


async def reset_extraction_results(session: AsyncSession, job_id: uuid.UUID) -> None:
    """重新提取前清掉上一轮的槽位结果与章节实例。

    只软删结果行，资料文件与母本引用保持不动：重新提取改的是「取值」，
    不是「输入」，输入变更由上传/删除资料单独表达。
    """
    for model in (DocGenSlotValue, DocGenSection):
        await session.execute(update(model).where(model.job_id == job_id).values(is_deleted=True))
    await session.flush()


async def copy_input_files(session: AsyncSession, source_job_id: uuid.UUID, target_job_id: uuid.UUID) -> int:
    """把上一次任务的资料原样挂到新任务（复用存储键，不重新上传）。

    返回 ``stats.cloned_files``，渲染报告与审计据此说明「素材未变」。
    """
    files = await list_input_files(session, source_job_id)
    count = 0
    for item in files:
        session.add(
            DocGenInputFile(
                job_id=target_job_id,
                original_filename=item.original_filename,
                object_key=item.object_key,
                file_id=item.file_id,
                sha256=item.sha256,
                size_bytes=item.size_bytes,
                mime_type=item.mime_type,
                role=item.role,
                page_count=item.page_count,
                char_count=item.char_count,
                parse_status=item.parse_status,
                warnings=item.warnings,
            )
        )
        count += 1
    await session.flush()
    return count


async def copy_extraction_results(session: AsyncSession, source_job_id: uuid.UUID, target_job_id: uuid.UUID) -> int:
    """把已提取的槽位值与章节大纲整表克隆到新任务（「重新生成」沿用人工确认值）。

    行原样复制（text/state/reason/evidence/pre_compose_text 不变），新流水线
    检测到已有落库结果即走「直接渲染」续跑分支，不重复调用提取模型。
    返回复制的槽位行数。
    """
    values = await list_slot_values(session, source_job_id)
    for row in values:
        session.add(
            DocGenSlotValue(
                job_id=target_job_id,
                slot_key=row.slot_key,
                section_key=row.section_key,
                instance_index=row.instance_index,
                label=row.label,
                text=row.text,
                rows=row.rows,
                state=row.state,
                reason=row.reason,
                confidence=row.confidence,
                evidence=row.evidence,
                candidates=row.candidates,
                pre_compose_text=row.pre_compose_text,
            )
        )
    for section in await list_sections(session, source_job_id):
        session.add(
            DocGenSection(
                job_id=target_job_id,
                section_key=section.section_key,
                fragment_key=section.fragment_key,
                extension_point_key=section.extension_point_key,
                parent_section_key=section.parent_section_key,
                level=section.level,
                title=section.title,
                order_index=section.order_index,
                source=section.source,
                state=section.state,
                trigger_trace=section.trigger_trace,
            )
        )
    await session.flush()
    return len(values)


async def enqueue_extract(session: AsyncSession, job_id: uuid.UUID) -> None:
    """「AI 提取信息」重新入队：状态回到 ``pending`` 并清掉上一轮执行痕迹。"""
    await session.execute(
        update(DocGenJob)
        .where(DocGenJob.id == job_id, DocGenJob.is_deleted.is_(False))
        .values(
            status="pending",
            step="排队提取",
            progress=0,
            attempts=0,
            error_code=None,
            error_message=None,
            finished_at=None,
            lease_expires_at=None,
            updated_at=datetime.now(UTC),
        )
    )


async def list_superseded_sibling_jobs(
    session: AsyncSession, job_id: uuid.UUID, parent_job_id: uuid.UUID | None
) -> Sequence[DocGenJob]:
    """重新生成链上已被取代的历史任务：祖先链、祖先下的兄弟分支、以及本任务的其它子孙。"""
    chain: list[DocGenJob] = []
    seen: set[uuid.UUID] = {job_id}

    def _remember(item: DocGenJob) -> None:
        if item.id not in seen:
            seen.add(item.id)
            chain.append(item)

    cursor = parent_job_id
    while cursor is not None:
        ancestor = await get_job(session, cursor)
        if ancestor is None:
            break
        _remember(ancestor)
        for sibling in await list_jobs_by_parent(session, ancestor.id):
            _remember(sibling)
        cursor = ancestor.parent_job_id
    for descendant in await list_jobs_by_parent(session, job_id):
        _remember(descendant)
    return chain
