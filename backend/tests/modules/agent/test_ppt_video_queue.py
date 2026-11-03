"""渲染队列单测：抢占、幂等入队、失败重试与心跳超时重排。

这些用例要真实数据库（`FOR UPDATE SKIP LOCKED` 无法用 mock 验证），
因此依赖 `db_session` fixture；本地跑需要先 `alembic upgrade head`。
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agent import queue
from app.modules.agent.models import (
    JOB_STATUS_FAILED,
    JOB_STATUS_QUEUED,
    JOB_STATUS_RUNNING,
    JOB_STATUS_SUCCEEDED,
    PptVideoJob,
    PptVideoProject,
    PptVideoVersion,
)


async def _make_project(session: AsyncSession) -> PptVideoProject:
    project = PptVideoProject(
        id=uuid.uuid4(),
        name=f"队列测试-{uuid.uuid4().hex[:6]}",
        source_object_key=f"agent/ppt-video/source/{uuid.uuid4().hex}.pptx",
        source_filename="deck.pptx",
        source_sha256=uuid.uuid4().hex * 2,  # 64 位十六进制，等价于真实指纹长度
        slide_count=3,
        default_language="zh",
        default_voice_id="zf_001",
        speed=1.0,
    )
    session.add(project)
    await session.flush()
    return project


async def _make_version(session: AsyncSession, project: PptVideoProject) -> PptVideoVersion:
    """成片版本行：job.version_id 有外键，mark_succeeded 前必须先有版本"""
    version = PptVideoVersion(
        id=uuid.uuid4(),
        project_id=project.id,
        version_no=1,
        file_name="queue-test-v1.mp4",
        object_key=f"agent/ppt-video/render/{uuid.uuid4().hex}.mp4",
        file_sha256=uuid.uuid4().hex * 2,
        head_key="head-key",
        body_key="body-key",
        manifest={"slides": []},
    )
    session.add(version)
    await session.flush()
    return version


async def test_enqueue_is_idempotent_while_queued(db_session: AsyncSession) -> None:
    project = await _make_project(db_session)

    first = await queue.enqueue(db_session, project.id, requested_by_name="张三")
    second = await queue.enqueue(db_session, project.id, requested_by_name="李四")

    assert first.id == second.id
    assert first.status == JOB_STATUS_QUEUED
    assert first.attempts == 0


async def test_claim_marks_running_and_counts_attempt(db_session: AsyncSession) -> None:
    project = await _make_project(db_session)
    await queue.enqueue(db_session, project.id)

    claimed = await queue.claim(db_session, "worker-1")

    assert claimed is not None
    assert claimed.status == JOB_STATUS_RUNNING
    assert claimed.worker_id == "worker-1"
    assert claimed.attempts == 1
    assert claimed.stage == "parse"
    assert claimed.heartbeat_at is not None


async def test_claim_returns_none_when_nothing_queued(db_session: AsyncSession) -> None:
    await db_session.execute(PptVideoJob.__table__.delete())
    assert await queue.claim(db_session, "worker-1") is None


async def test_heartbeat_writes_stage_and_clamps_progress(db_session: AsyncSession) -> None:
    project = await _make_project(db_session)
    job = await queue.enqueue(db_session, project.id)
    await queue.claim(db_session, "worker-1")

    await queue.heartbeat(db_session, job.id, "tts", 240)
    await db_session.refresh(job)
    assert job.stage == "tts"
    assert job.progress == 100


async def test_mark_failed_requeues_until_attempts_exhausted(db_session: AsyncSession) -> None:
    project = await _make_project(db_session)
    job = await queue.enqueue(db_session, project.id, max_attempts=2)
    await queue.claim(db_session, "worker-1")

    await queue.mark_failed(db_session, job.id, "第 3 页 TTS 失败", retry=True)
    await db_session.refresh(job)
    assert job.status == JOB_STATUS_QUEUED
    assert job.attempts == 1
    assert "TTS" in (job.error_message or "")

    # 第二次失败时 attempts 已到上限，必须落成 failed 而不是无限重试
    await queue.claim(db_session, "worker-1")
    await queue.mark_failed(db_session, job.id, "仍然失败", retry=True)
    await db_session.refresh(job)
    assert job.status == JOB_STATUS_FAILED
    assert job.stage == "failed"


async def test_requeue_stale_releases_dead_worker(db_session: AsyncSession) -> None:
    project = await _make_project(db_session)
    job = await queue.enqueue(db_session, project.id)
    await queue.claim(db_session, "worker-dead")
    job.heartbeat_at = datetime.now(UTC) - timedelta(seconds=1200)
    await db_session.flush()

    requeued = await queue.requeue_stale(db_session, stale_seconds=600)

    await db_session.refresh(job)
    assert requeued == 1
    assert job.status == JOB_STATUS_QUEUED
    assert job.worker_id is None


async def test_requeue_stale_fails_job_without_attempts_left(db_session: AsyncSession) -> None:
    project = await _make_project(db_session)
    job = await queue.enqueue(db_session, project.id, max_attempts=1)
    await queue.claim(db_session, "worker-dead")
    job.heartbeat_at = datetime.now(UTC) - timedelta(seconds=1200)
    await db_session.flush()

    await queue.requeue_stale(db_session, stale_seconds=600)

    await db_session.refresh(job)
    assert job.status == JOB_STATUS_FAILED
    assert "重试次数" in (job.error_message or "")


async def test_mark_succeeded_records_version(db_session: AsyncSession) -> None:
    project = await _make_project(db_session)
    job = await queue.enqueue(db_session, project.id)
    await queue.claim(db_session, "worker-1")

    version = await _make_version(db_session, project)
    await queue.mark_succeeded(db_session, job.id, version.id)
    await db_session.refresh(job)
    assert job.status == JOB_STATUS_SUCCEEDED
    assert job.progress == 100
    assert job.version_id == version.id


@pytest.mark.parametrize("stale", [600, 1800])
async def test_get_latest_returns_latest_job(db_session: AsyncSession, stale: int) -> None:
    project = await _make_project(db_session)
    job = await queue.enqueue(db_session, project.id)

    latest = await queue.get_latest(db_session, project.id)

    assert latest is not None
    assert latest.id == job.id
