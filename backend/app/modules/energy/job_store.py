"""Energy's dict-shaped view of the shared job primitive.

The module's job state now lives in `app.core.jobs`, so this file only keeps the API the
energy endpoints already use: `create()` returns a job id, and `get()` returns a mapping
with exactly `status`/`result`/`error`/`created_at`. Behaviour is unchanged — the status
strings and the record shape are the same as before the move.
"""

from __future__ import annotations

from typing import Any

from app.core.jobs import InMemoryJobStore

_LEGACY_KEYS = ("status", "result", "error", "created_at")


class JobStore:
    """Thin adapter over the core job primitive, preserving the original module API."""

    def __init__(self, store: InMemoryJobStore | None = None) -> None:
        self._store = store if store is not None else InMemoryJobStore()

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


sync_job_store = JobStore()
