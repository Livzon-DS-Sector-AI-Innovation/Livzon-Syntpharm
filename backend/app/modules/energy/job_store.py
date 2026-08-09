from __future__ import annotations

import time
from uuid import uuid4


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, object]] = {}

    def create(self) -> str:
        job_id = str(uuid4())
        self._jobs[job_id] = {"status": "running", "result": None, "error": None, "created_at": time.time()}
        return job_id

    def get(self, job_id: str) -> dict[str, object] | None:
        return self._jobs.get(job_id)

    def complete(self, job_id: str, result: object) -> None:
        if job_id in self._jobs:
            self._jobs[job_id].update(status="done", result=result)

    def fail(self, job_id: str, error: str) -> None:
        if job_id in self._jobs:
            self._jobs[job_id].update(status="failed", error=error)


sync_job_store = JobStore()
