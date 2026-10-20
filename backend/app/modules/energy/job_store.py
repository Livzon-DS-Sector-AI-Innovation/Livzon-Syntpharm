from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import uuid4

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

    def complete(self, job_id: str, result: dict[str, Any]) -> None:
        job = self._jobs.get(job_id)
        if job:
            job.status = "done"
            job.result = result

    def fail(self, job_id: str, error: str) -> None:
        job = self._jobs.get(job_id)
        if job:
            job.status = "failed"
            job.error = error


sync_job_store = JobStore()
