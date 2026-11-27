"""渲染队列单测：抢占、幂等入队、失败重试与心跳超时重排。

这些用例要真实数据库（`FOR UPDATE SKIP LOCKED` 无法用 mock 验证），
因此依赖 `db_session` fixture；本地跑需要先 `alembic upgrade head`。
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agent import queue
from app.modules.agent.models import (
    JOB_KIND_AUDIO,
    JOB_KIND_PARSE,
    JOB_KIND_RENDER,
    JOB_KIND_SOURCE_PREVIEW,
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
    await db_session.execute(delete(PptVideoJob))
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


# ── 任务类别隔离（解析/试听/换源预览不再混进渲染队列） ──────────────────────


async def test_enqueue_dedupes_per_kind(db_session: AsyncSession) -> None:
    """同项目同一时刻可以各有一条 render / parse 排队任务，互不复用。"""
    project = await _make_project(db_session)

    render_job = await queue.enqueue(db_session, project.id, kind=JOB_KIND_RENDER)
    parse_job = await queue.enqueue(db_session, project.id, kind=JOB_KIND_PARSE)

    assert render_job.id != parse_job.id
    assert parse_job.kind == JOB_KIND_PARSE
    again = await queue.enqueue(db_session, project.id, kind=JOB_KIND_PARSE)
    assert again.id == parse_job.id


async def test_claim_filters_by_kind(db_session: AsyncSession) -> None:
    """渲染循环只拿 render，解析循环只拿其余类别。"""
    project = await _make_project(db_session)
    render_job = await queue.enqueue(db_session, project.id, kind=JOB_KIND_RENDER)
    parse_job = await queue.enqueue(db_session, project.id, kind=JOB_KIND_PARSE)

    claimed_render = await queue.claim(db_session, "worker-render", kinds=[JOB_KIND_RENDER])
    assert claimed_render is not None
    assert claimed_render.id == render_job.id

    claimed_parse = await queue.claim(db_session, "worker-parse", kinds=[JOB_KIND_PARSE])
    assert claimed_parse is not None
    assert claimed_parse.id == parse_job.id


async def test_cancel_pending_can_target_kind(db_session: AsyncSession) -> None:
    project = await _make_project(db_session)
    render_job = await queue.enqueue(db_session, project.id, kind=JOB_KIND_RENDER)
    parse_job = await queue.enqueue(db_session, project.id, kind=JOB_KIND_PARSE)

    await queue.cancel_pending(db_session, project.id, kinds=[JOB_KIND_RENDER])

    await db_session.refresh(render_job)
    await db_session.refresh(parse_job)
    assert render_job.status == "canceled"
    assert parse_job.status == JOB_STATUS_QUEUED


async def test_mark_succeeded_without_version_records_result(db_session: AsyncSession) -> None:
    """试听/换源预览没有视频版本，产物写 result。"""
    project = await _make_project(db_session)
    job = await queue.enqueue(db_session, project.id, kind=JOB_KIND_AUDIO)
    await queue.claim(db_session, "worker-1", kinds=[JOB_KIND_AUDIO])

    await queue.mark_succeeded(db_session, job.id, result={"audio_url": "/x.wav"})
    await db_session.refresh(job)

    assert job.status == JOB_STATUS_SUCCEEDED
    assert job.version_id is None
    assert job.result == {"audio_url": "/x.wav"}


async def test_get_latest_filters_kind(db_session: AsyncSession) -> None:
    project = await _make_project(db_session)
    await queue.enqueue(db_session, project.id, kind=JOB_KIND_PARSE)
    render_job = await queue.enqueue(db_session, project.id, kind=JOB_KIND_RENDER)

    latest = await queue.get_latest(db_session, project.id)
    assert latest is not None and latest.id == render_job.id
    parse_latest = await queue.get_latest(db_session, project.id, kind=JOB_KIND_PARSE)
    assert parse_latest is not None and parse_latest.kind == JOB_KIND_PARSE


# ── 带 payload 的去重（#243：json 列没有等值运算符，必须 cast 到 jsonb） ────────


async def test_enqueue_dedupes_same_payload(db_session: AsyncSession) -> None:
    """试听/换源预览每次都带 payload：同入参连点两次只能有一条排队任务。

    修复前这里会直接抛 `operator does not exist: json = json`（接口 500）。
    """
    project = await _make_project(db_session)
    payload = {"slide_uid": uuid.uuid4().hex}

    first = await queue.enqueue(db_session, project.id, kind=JOB_KIND_AUDIO, payload=payload)
    second = await queue.enqueue(db_session, project.id, kind=JOB_KIND_AUDIO, payload=payload)

    assert first.id == second.id
    rows = (
        await db_session.scalars(
            select(PptVideoJob).where(
                PptVideoJob.project_id == project.id,
                PptVideoJob.kind == JOB_KIND_AUDIO,
            )
        )
    ).all()
    assert len(rows) == 1


async def test_enqueue_new_job_for_different_payload(db_session: AsyncSession) -> None:
    """入参不同（比如换一页试听）不能复用上一条排队任务。"""
    project = await _make_project(db_session)

    first = await queue.enqueue(db_session, project.id, kind=JOB_KIND_AUDIO, payload={"slide_uid": uuid.uuid4().hex})
    second = await queue.enqueue(db_session, project.id, kind=JOB_KIND_AUDIO, payload={"slide_uid": uuid.uuid4().hex})

    assert first.id != second.id


async def test_enqueue_payload_dedupe_is_key_order_insensitive(db_session: AsyncSession) -> None:
    """JSONB 是结构化比较：键序不同但内容相同视为同一入参。"""
    project = await _make_project(db_session)

    first = await queue.enqueue(
        db_session, project.id, kind=JOB_KIND_SOURCE_PREVIEW, payload={"filename": "a.pptx", "suffix": ".pptx"}
    )
    second = await queue.enqueue(
        db_session, project.id, kind=JOB_KIND_SOURCE_PREVIEW, payload={"suffix": ".pptx", "filename": "a.pptx"}
    )

    assert first.id == second.id


# ── 租约（#236：心跳/收尾带 worker_id，避免重排后双跑） ──────────────────────


async def test_heartbeat_fenced_by_worker_id(db_session: AsyncSession) -> None:
    """任务被别的 worker 持有后，原 worker 的心跳必须写 0 行并返回 False。"""
    project = await _make_project(db_session)
    job = await queue.enqueue(db_session, project.id)
    await queue.claim(db_session, "worker-1")
    job.worker_id = "worker-2"
    await db_session.flush()

    alive = await queue.heartbeat(db_session, job.id, "tts", 42, worker_id="worker-1")

    await db_session.refresh(job)
    assert alive is False
    assert job.stage != "tts"
    assert job.progress != 42


async def test_heartbeat_without_worker_id_keeps_old_behavior(db_session: AsyncSession) -> None:
    project = await _make_project(db_session)
    job = await queue.enqueue(db_session, project.id)
    await queue.claim(db_session, "worker-1")

    assert await queue.heartbeat(db_session, job.id, "render", 12) is True


async def test_heartbeat_fenced_returns_false_when_requeued(db_session: AsyncSession) -> None:
    """requeue_stale 把任务打回队列后，原 worker 的心跳必须失败（否则双跑）。"""
    project = await _make_project(db_session)
    job = await queue.enqueue(db_session, project.id)
    await queue.claim(db_session, "worker-dead")
    job.heartbeat_at = datetime.now(UTC) - timedelta(seconds=1200)
    await db_session.flush()
    await queue.requeue_stale(db_session, stale_seconds=600)

    assert await queue.heartbeat(db_session, job.id, "tts", 50, worker_id="worker-dead") is False


async def test_touch_only_refreshes_heartbeat(db_session: AsyncSession) -> None:
    """保活只刷心跳，不能把 stage/progress 写回退。"""
    project = await _make_project(db_session)
    job = await queue.enqueue(db_session, project.id)
    await queue.claim(db_session, "worker-1")
    await queue.heartbeat(db_session, job.id, "tts", 60, worker_id="worker-1")
    before = job.heartbeat_at

    assert await queue.touch(db_session, job.id, "worker-1") is True

    await db_session.refresh(job)
    assert job.stage == "tts"
    assert job.progress == 60
    assert job.heartbeat_at is not None and before is not None and job.heartbeat_at >= before


async def test_touch_returns_false_for_other_worker(db_session: AsyncSession) -> None:
    project = await _make_project(db_session)
    job = await queue.enqueue(db_session, project.id)
    await queue.claim(db_session, "worker-1")

    assert await queue.touch(db_session, job.id, "worker-2") is False
