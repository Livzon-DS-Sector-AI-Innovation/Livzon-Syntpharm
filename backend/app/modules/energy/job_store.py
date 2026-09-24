"""Energy's dict-shaped view of the shared job primitive.

The module's job state lives in `app.core.jobs`, so this file keeps the API the energy
endpoints already use — `create()` returns a job id and `get()` returns a mapping with
exactly `status`/`result`/`error`/`created_at` — and adds `spawn()`, which runs work through
the primitive's background helper.

Behaviour is unchanged: the status strings and the record shape are the same as before.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.core.jobs import JobRecord, JobStoreProtocol, job_store, spawn_job

_LEGACY_KEYS = ("status", "result", "error", "created_at")


class JobStore:
    """Adapter over the shared job primitive, preserving the original module API."""

    def __init__(self, store: JobStoreProtocol | None = None) -> None:
        self._store: JobStoreProtocol = store if store is not None else job_store

    def create(self) -> str:
        return self._store.create().job_id

    def get(self, job_id: str) -> dict[str, Any] | None:
        record = self._store.get(job_id)
        if record is None:
            return None
        return {key: getattr(record, key) for key in _LEGACY_KEYS}

    def complete(self, job_id: str, result: Any = None) -> None:
        self._store.complete(job_id, result)

    def fail(self, job_id: str, error: str) -> None:
        self._store.fail(job_id, error)

    def spawn(
        self,
        work: Callable[[JobRecord], Awaitable[Any]],
        *,
        name: str | None = None,
        timeout_seconds: float | None = None,
    ) -> str:
        """Run `work` in the background through the primitive; return its job id."""
        return spawn_job(self._store, work, name=name, timeout_seconds=timeout_seconds).job_id


sync_job_store = JobStore()
