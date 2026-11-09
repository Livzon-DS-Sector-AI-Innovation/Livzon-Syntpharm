"""渲染任务队列（agent schema 自有表，跨进程抢占）。

为什么不用 `core.background_jobs`：那是全局表且没有「抢占/心跳/进度」字段，
跨容器消费需要加行锁与心跳重排，会动到全局层；放在本模块表里自治更清晰。

抢占语义：
- `FOR UPDATE SKIP LOCKED` 保证同一任务只会被一个 worker 拿到；
- worker 每处理一页写一次心跳，心跳超过 `stale_seconds` 视为 worker 已死，
  `requeue_stale` 把它放回队列；`attempts > max_attempts` 直接置失败。
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agent.models import (
    JOB_STATUS_FAILED,
    JOB_STATUS_QUEUED,
    JOB_STATUS_RUNNING,
    JOB_STATUS_SUCCEEDED,
    PptVideoJob,
)


def _now() -> datetime:
    return datetime.now(UTC)


async def enqueue(
    session: AsyncSession,
    project_id: uuid.UUID,
    requested_by_name: str | None = None,
    max_attempts: int = 3,
) -> PptVideoJob:
    """入队一次渲染任务；同一项目已有排队任务时复用它（避免连点产生重复渲染）。"""
    existing = await session.scalar(
        select(PptVideoJob)
        .where(
            PptVideoJob.project_id == project_id,
            PptVideoJob.status == JOB_STATUS_QUEUED,
            PptVideoJob.is_deleted.is_(False),
        )
        .order_by(PptVideoJob.created_at.desc())
        .limit(1)
    )
    if existing is not None:
        return existing

    job = PptVideoJob(
        id=uuid.uuid4(),
        project_id=project_id,
        status=JOB_STATUS_QUEUED,
        stage="queued",
        progress=0,
        attempts=0,
        max_attempts=max_attempts,
        requested_by_name=requested_by_name,
    )
    session.add(job)
    await session.flush()
    return job


async def claim(session: AsyncSession, worker_id: str) -> PptVideoJob | None:
    """抢占一个排队任务（无任务时返回 None）。"""
    job = await session.scalar(
        select(PptVideoJob)
        .where(PptVideoJob.status == JOB_STATUS_QUEUED, PptVideoJob.is_deleted.is_(False))
        .order_by(PptVideoJob.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if job is None:
        return None

    job.status = JOB_STATUS_RUNNING
    job.worker_id = worker_id
    job.stage = "parse"
    job.progress = 1
    job.attempts = (job.attempts or 0) + 1
    job.started_at = _now()
    job.heartbeat_at = _now()
    job.finished_at = None
    job.error_message = None
    await session.flush()
    return job


async def heartbeat(session: AsyncSession, job_id: uuid.UUID, stage: str, progress: int) -> None:
    """回写进度与心跳（调用方按页节流，不要每帧写）。"""
    await session.execute(
        update(PptVideoJob)
        .where(PptVideoJob.id == job_id)
        .values(stage=stage, progress=max(0, min(100, progress)), heartbeat_at=_now())
    )


async def mark_succeeded(session: AsyncSession, job_id: uuid.UUID, version_id: uuid.UUID) -> None:
    await session.execute(
        update(PptVideoJob)
        .where(PptVideoJob.id == job_id)
        .values(
            status=JOB_STATUS_SUCCEEDED,
            stage="done",
            progress=100,
            version_id=version_id,
            finished_at=_now(),
            heartbeat_at=_now(),
            error_message=None,
        )
    )


async def mark_failed(session: AsyncSession, job_id: uuid.UUID, message: str, retry: bool) -> None:
    """失败处理：还能重试则回到队列，否则置失败。"""
    job = await session.get(PptVideoJob, job_id)
    if job is None:
        return
    if retry and (job.attempts or 0) < (job.max_attempts or 3):
        job.status = JOB_STATUS_QUEUED
        job.stage = "queued"
        job.worker_id = None
        job.heartbeat_at = None
        job.error_message = message[:2000]
    else:
        job.status = JOB_STATUS_FAILED
        job.stage = "failed"
        job.finished_at = _now()
        job.error_message = message[:2000]
    await session.flush()


async def requeue_stale(session: AsyncSession, stale_seconds: int = 300) -> int:
    """把心跳超时的 running 任务放回队列（worker 崩溃/容器重启场景）。"""
    deadline = _now() - timedelta(seconds=stale_seconds)
    stale = (
        await session.scalars(
            select(PptVideoJob).where(
                PptVideoJob.status == JOB_STATUS_RUNNING,
                PptVideoJob.is_deleted.is_(False),
                func.coalesce(PptVideoJob.heartbeat_at, PptVideoJob.started_at) < deadline,
            )
        )
    ).all()

    for job in stale:
        if (job.attempts or 0) >= (job.max_attempts or 3):
            job.status = JOB_STATUS_FAILED
            job.stage = "failed"
            job.finished_at = _now()
            job.error_message = "渲染超时且重试次数已用尽"
        else:
            job.status = JOB_STATUS_QUEUED
            job.stage = "queued"
            job.worker_id = None
            job.heartbeat_at = None
    await session.flush()
    return len(stale)


async def get_latest(session: AsyncSession, project_id: uuid.UUID) -> PptVideoJob | None:
    job: PptVideoJob | None = await session.scalar(
        select(PptVideoJob)
        .where(PptVideoJob.project_id == project_id, PptVideoJob.is_deleted.is_(False))
        .order_by(PptVideoJob.created_at.desc())
        .limit(1)
    )
    return job


async def cancel_pending(session: AsyncSession, project_id: uuid.UUID) -> int:
    """项目删除时清掉排队中的任务（运行中的由 worker 自己收尾）。"""
    result = await session.execute(
        update(PptVideoJob)
        .where(PptVideoJob.project_id == project_id, PptVideoJob.status == JOB_STATUS_QUEUED)
        .values(status="canceled", stage="canceled", finished_at=_now())
    )
    rowcount = getattr(result, "rowcount", 0)
    return int(rowcount or 0)
