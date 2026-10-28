"""一次性异步任务（提交 + 进程内状态 + 轮询）的通用基建。

模式（源自 energy 模块的 D-11 实践）：
- 提交端点：`job_id = start_job(store, name, runner)`，立即返回 `AsyncJobAcceptedResponse`；
- 后台执行：`runner(job_id)` 由 `spawn_task` 拉起，成功 `complete` / 失败 `fail`；
- 状态查询端点：`GET /api/v1/<module>/jobs/{job_id}` 返回 `AsyncJobStateResponse`；
- 前端：`usePollingJob`（`frontend/src/hooks/usePollingJob.ts`）轮询。

状态存**进程内**（重启即丢、多副本互不可见）：404 只代表「查不到状态」，
不能当成「任务失败」——副作用可能已经发生。
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import uuid4

from app.core.exceptions import NotFoundException
from app.core.tasks import spawn_task
from app.shared.schemas import AsyncJobState

logger = logging.getLogger(__name__)

JobStatus = Literal["running", "done", "failed"]


@dataclass(slots=True)
class SyncJob:
    job_id: str
    status: JobStatus = "running"
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)


class JobStore:
    """进程内任务状态表：重启即丢、多副本不可见（`D-11`），轮询方必须能处理 job 查不到。"""

    def __init__(self) -> None:
        self._jobs: dict[str, SyncJob] = {}

    def create(self) -> str:
        job_id = str(uuid4())
        self._jobs[job_id] = SyncJob(job_id=job_id)
        return job_id

    def get(self, job_id: str) -> SyncJob | None:
        return self._jobs.get(job_id)

    def complete(self, job_id: str, result: dict[str, Any] | None = None) -> None:
        job = self._jobs.get(job_id)
        if job:
            job.status = "done"
            job.result = result

    def fail(self, job_id: str, error: str) -> None:
        job = self._jobs.get(job_id)
        if job:
            job.status = "failed"
            job.error = error


def start_job(
    store: JobStore,
    name: str,
    runner: Callable[[str], Awaitable[dict[str, Any] | None]],
) -> str:
    """创建任务并交给后台执行，返回 job_id。

    `runner(job_id)` 在后台协程里跑；正常返回值（dict）写入 `state.result`，
    抛异常则记日志并置 `failed`。
    """
    job_id = store.create()

    async def _run() -> None:
        try:
            result = await runner(job_id)
            store.complete(job_id, result)
        except Exception as e:
            logger.exception("async job %s failed", name)
            store.fail(job_id, str(e))

    spawn_task(_run(), name=f"{name}-{job_id[:8]}")
    return job_id


def get_job_state_or_404(store: JobStore, job_id: str) -> AsyncJobState:
    """按 job_id 取状态供轮询端点返回；查不到抛 404（前端按「查不到状态」兜底处理）。"""
    job = store.get(job_id)
    if job is None:
        raise NotFoundException(f"任务 {job_id} 不存在或服务已重启")
    return AsyncJobState(job_id=job.job_id, status=job.status, result=job.result, error=job.error)
