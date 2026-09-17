"""强制终止链路测试（cancellation.py + worker.py 的执行外壳）。

这里不接数据库：只验证「卡住的任务能被停下来」这条机制本身——
抢占、超时、重复领取、关停四类场景各自的终态与信号传递。
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import pytest

from app.modules.research.doc_gen import cancellation
from app.modules.research.doc_gen import worker as worker_module
from app.modules.research.doc_gen.runtime_config import RuntimeConfig


def _job_id() -> uuid.UUID:
    return uuid.uuid4()


# ─────────────────── 进程内注册表 ───────────────────


def test_unknown_job_probe_is_false() -> None:
    assert cancellation.should_cancel_for(_job_id())() is False
    assert cancellation.request_abort(_job_id()) is False


def test_register_and_unregister_track_running_jobs() -> None:
    job_id = _job_id()
    handle = cancellation.register(job_id)
    assert job_id in [uuid.UUID(item) for item in cancellation.running_job_ids()]
    cancellation.unregister(job_id)
    assert job_id not in [uuid.UUID(item) for item in cancellation.running_job_ids()]
    assert handle.should_cancel() is False


def test_duplicate_claim_supersedes_previous_execution() -> None:
    """租约过期后同一任务被重复领取：旧执行体必须先被终止，避免双跑互相覆写。"""
    job_id = _job_id()
    first = cancellation.register(job_id)
    cancellation.register(job_id)
    assert first.reason == "superseded"
    assert first.should_cancel() is True
    cancellation.unregister(job_id)


async def test_abort_all_cancels_the_attached_task() -> None:
    job_id = _job_id()
    handle = cancellation.register(job_id)

    async def _body() -> None:
        await asyncio.sleep(30)

    task = asyncio.create_task(_body())
    cancellation.attach_task(handle, task)
    await asyncio.sleep(0)
    cancellation.abort_all("shutdown")
    with pytest.raises(asyncio.CancelledError):
        await task
    cancellation.unregister(job_id)


# ─────────────────── worker 执行外壳 ───────────────────


@pytest.fixture
def finalize_recorder(monkeypatch: Any) -> list[tuple[str, str]]:
    """替换 _finalize（避免依赖真实数据库），记录落终态调用。"""
    records: list[tuple[str, str]] = []

    async def _record(_job_id: uuid.UUID, target: str, code: str, _message: str) -> None:
        records.append((target, code))

    monkeypatch.setattr(worker_module, "_finalize", _record)
    return records


async def test_user_abort_preempts_a_stuck_execution(monkeypatch: Any, finalize_recorder: Any) -> None:
    job_id = _job_id()

    async def _stuck(_job_id: uuid.UUID, _handle: Any) -> str:
        await asyncio.sleep(30)  # 模拟模型调用或解析卡死
        return "ready"

    monkeypatch.setattr(worker_module.pipeline, "execute_job", _stuck)
    result = await asyncio.gather(
        worker_module._execute_guarded(job_id, RuntimeConfig(job_timeout_seconds=30)),
        _abort_after(job_id),
    )
    assert result[0] == "cancelled"
    assert finalize_recorder == [("cancelled", "cancelled")]


async def test_job_timeout_forces_failure(monkeypatch: Any, finalize_recorder: Any) -> None:
    job_id = _job_id()

    async def _stuck(_job_id: uuid.UUID, _handle: Any) -> str:
        await asyncio.sleep(30)
        return "ready"

    monkeypatch.setattr(worker_module.pipeline, "execute_job", _stuck)
    result = await worker_module._execute_guarded(job_id, RuntimeConfig(job_timeout_seconds=0.05))
    assert result == "failed"
    assert finalize_recorder == [("failed", "timeout")]


async def test_process_shutdown_signal_is_not_swallowed(monkeypatch: Any, finalize_recorder: Any) -> None:
    """关停取消必须原样抛回，不能被当成「用户终止」落一个 cancelled 终态。"""
    job_id = _job_id()

    async def _long(_job_id: uuid.UUID, _handle: Any) -> str:
        await asyncio.sleep(30)
        return "ready"

    monkeypatch.setattr(worker_module.pipeline, "execute_job", _long)
    guarded = asyncio.create_task(worker_module._execute_guarded(job_id, RuntimeConfig(job_timeout_seconds=30)))
    await asyncio.sleep(0.05)
    guarded.cancel()
    with pytest.raises(asyncio.CancelledError):
        await guarded
    assert finalize_recorder == []
    assert cancellation.get(job_id) is None, "外壳退出后必须清理注册表"


async def _abort_after(job_id: uuid.UUID) -> str:
    """等执行体登记好句柄后再发出终止请求，模拟用户在任务卡住时点「终止」。"""
    for _ in range(50):
        await asyncio.sleep(0.01)
        if cancellation.request_abort(job_id, "cancelled"):
            return "aborted"
    raise AssertionError("任务未登记到取消注册表")
