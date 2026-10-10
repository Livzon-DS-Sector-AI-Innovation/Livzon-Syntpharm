"""In-memory status store for user-triggered background jobs.

Same shape as the store energy built for its sync endpoints, lifted into `app/core`
so a second module need not copy it. `AGENTS.md:303` names `app/core/jobs.py` as
where the task queue lives, so this sits beside it.

## What this is not

These records live in the process's memory. They are **not durable**: a restart
loses every job, and a second worker would not see another's jobs. `AGENTS.md:308`
lists exactly these limits as the reason `asyncio.create_task` is unfit for
business logic — "无法重试、无法监控、重启后丢失".

So this store makes a running job *visible*. It does not make it *retryable*.
Where a job must be safe to re-run, that has to come from the data itself — an
idempotent write, or a unique constraint — not from here.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import uuid4

JobState = Literal["running", "done", "failed"]


@dataclass
class JobRecord:
    """One job's status. `result` is populated only once `state` is `done`."""

    state: JobState = "running"
    result: Any = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}

    def create(self) -> str:
        job_id = str(uuid4())
        self._jobs[job_id] = JobRecord()
        return job_id

    def get(self, job_id: str) -> JobRecord | None:
        return self._jobs.get(job_id)

    def complete(self, job_id: str, result: Any) -> None:
        record = self._jobs.get(job_id)
        if record is not None:
            record.state = "done"
            record.result = result

    def fail(self, job_id: str, error: str) -> None:
        record = self._jobs.get(job_id)
        if record is not None:
            record.state = "failed"
            record.error = error


# One store per process. Each module that needs job status imports this instance
# rather than building its own, so the records are visible to every route.
job_store = JobStore()
