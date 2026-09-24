"""Job primitive for user-triggered long-running operations.

A job is a unit of background work with an observable record: status, progress, start time,
timeout and outcome. It sits on top of `app.core.tasks.spawn_task` and keeps the created
task on the record, so the job cannot be garbage collected before it finishes.

The store sits behind `JobStoreProtocol`, so a durable backing (database or cache) can
replace the in-memory implementation without changing callers.

**Known limitation:** job state is process-local. With more than one worker, a status poll
can miss a job another worker is running, and every job is lost on restart. Callers get one
process's view.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import uuid4

from app.core.tasks import spawn_task

logger = logging.getLogger(__name__)

JOB_STATUS_RUNNING = "running"
JOB_STATUS_DONE = "done"
JOB_STATUS_FAILED = "failed"

DEFAULT_JOB_TIMEOUT_SECONDS: float = 600.0


@dataclass
class JobRecord:
    """The observable state of one background job."""

    job_id: str
    status: str = JOB_STATUS_RUNNING
    progress: float = 0.0
    result: Any = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    timeout_seconds: float | None = DEFAULT_JOB_TIMEOUT_SECONDS
    task: asyncio.Task[None] | None = None


class JobStoreProtocol(Protocol):
    """What the job primitive needs from a store, so the backing can be swapped."""

    def create(self, *, timeout_seconds: float | None = DEFAULT_JOB_TIMEOUT_SECONDS) -> JobRecord: ...

    def get(self, job_id: str) -> JobRecord | None: ...

    def complete(self, job_id: str, result: Any = None) -> None: ...

    def fail(self, job_id: str, error: str) -> None: ...

    def set_progress(self, job_id: str, progress: float) -> None: ...


class InMemoryJobStore:
    """Process-local job store. See the module docstring for the limitation."""

    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}

    def create(self, *, timeout_seconds: float | None = DEFAULT_JOB_TIMEOUT_SECONDS) -> JobRecord:
        record = JobRecord(
            job_id=str(uuid4()),
            started_at=time.time(),
            timeout_seconds=timeout_seconds,
        )
        self._jobs[record.job_id] = record
        return record

    def get(self, job_id: str) -> JobRecord | None:
        return self._jobs.get(job_id)

    def complete(self, job_id: str, result: Any = None) -> None:
        record = self._jobs.get(job_id)
        if record is None:
            return
        record.status = JOB_STATUS_DONE
        record.result = result
        record.progress = 1.0
        record.finished_at = time.time()

    def fail(self, job_id: str, error: str) -> None:
        record = self._jobs.get(job_id)
        if record is None:
            return
        record.status = JOB_STATUS_FAILED
        record.error = error
        record.finished_at = time.time()

    def set_progress(self, job_id: str, progress: float) -> None:
        record = self._jobs.get(job_id)
        if record is None:
            return
        record.progress = min(1.0, max(0.0, progress))

    def is_expired(self, job_id: str) -> bool:
        """True when a running job has passed the timeout it was created with."""
        record = self._jobs.get(job_id)
        if record is None or record.status != JOB_STATUS_RUNNING:
            return False
        if record.timeout_seconds is None or record.started_at is None:
            return False
        return (time.time() - record.started_at) > record.timeout_seconds

    def fail_if_expired(self, job_id: str) -> bool:
        """Mark a running job failed if it has passed its timeout; True when it did."""
        if not self.is_expired(job_id):
            return False
        record = self._jobs[job_id]
        self.fail(job_id, f"job timed out after {record.timeout_seconds}s")
        return True


job_store = InMemoryJobStore()


def spawn_job(
    store: JobStoreProtocol,
    work: Callable[[JobRecord], Awaitable[Any]],
    *,
    name: str | None = None,
    timeout_seconds: float | None = DEFAULT_JOB_TIMEOUT_SECONDS,
) -> JobRecord:
    """Run `work` in the background and keep the outcome on its job record.

    The created task is retained on the record, so the job cannot be garbage collected
    before it finishes. A timeout marks the job failed and cancels the work; any other
    exception is recorded rather than raised, because nothing is awaiting the task.

    The **store owns the job's state** — this function only reports the outcome to it. With
    the in-memory store the returned record is the live object; with a durable backing, read
    the authoritative snapshot from the store.

    Args:
        store: where the job record lives.
        work: the coroutine to run; it receives the record so it can report progress.
        name: background task name. Defaults to the job id.
        timeout_seconds: cancel and fail the job after this long. None means no limit.
    """
    record = store.create(timeout_seconds=timeout_seconds)

    async def run() -> None:
        try:
            result = await asyncio.wait_for(work(record), timeout=record.timeout_seconds)
        except TimeoutError:
            logger.warning("Job %s timed out after %ss", record.job_id, record.timeout_seconds)
            store.fail(record.job_id, f"job timed out after {record.timeout_seconds}s")
        except Exception as error:
            logger.exception("Job %s failed", record.job_id)
            store.fail(record.job_id, str(error))
        else:
            store.complete(record.job_id, result)

    record.task = spawn_task(run(), name=name or f"job-{record.job_id[:8]}")
    return record


__all__ = [
    "DEFAULT_JOB_TIMEOUT_SECONDS",
    "JOB_STATUS_DONE",
    "JOB_STATUS_FAILED",
    "JOB_STATUS_RUNNING",
    "InMemoryJobStore",
    "JobRecord",
    "JobStoreProtocol",
    "job_store",
    "spawn_job",
    "spawn_task",
]
