"""Durable job state, backed by `core.background_jobs`.

The replacement for `app/core/job_store.py`'s in-memory dict. Same verbs — create,
complete, fail, get — so migrating a call site is mechanical, but every one is now
`async` and takes the caller's session, because the state is a row.

## Why this exists

`AGENTS.md:308` prohibits `asyncio.create_task()` for business logic for three
stated reasons: 无法重试、无法监控、重启后丢失 — cannot retry, cannot monitor, lost on
restart. An in-memory store has all three. `app/core/jobs.py` exports exactly that
prohibited function, so the durable half of the fix is here, in the state.

## What it still does not do

It records outcomes; it does not make a job safe to repeat. Retry safety has to come
from the data being written — `AGENTS.md:314` requires every retried operation to be
idempotent. A `running` row left behind by a crash is visible and honest; it is not
automatically resumable.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.job_models import JOB_DONE, JOB_FAILED, JOB_RUNNING, BackgroundJob


class JobRepository:
    """Reads and writes job state. Construct with the caller's session."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, name: str) -> UUID:
        """Start a job and return its id.

        Committed immediately: the id must be readable by the poll endpoint even if
        the worker that follows never completes. A row that never leaves `running`
        is the signal that something died mid-job.
        """
        job = BackgroundJob(
            name=name,
            state=JOB_RUNNING,
            started_at=datetime.now(UTC),
        )
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job.id

    async def get(self, job_id: UUID) -> BackgroundJob | None:
        """The status a poller asks for. `None` means the id is unknown."""
        result = await self.session.execute(
            select(BackgroundJob).where(
                BackgroundJob.id == job_id,
                BackgroundJob.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def complete(self, job_id: UUID, result: dict[str, Any] | None = None) -> None:
        job = await self.get(job_id)
        if job is None:
            return
        job.state = JOB_DONE
        job.result = result
        job.finished_at = datetime.now(UTC)
        await self.session.commit()

    async def fail(self, job_id: UUID, error: str) -> None:
        job = await self.get(job_id)
        if job is None:
            return
        job.state = JOB_FAILED
        job.error = error
        job.finished_at = datetime.now(UTC)
        await self.session.commit()

    async def list_unfinished(self) -> list[BackgroundJob]:
        """Jobs still marked `running`.

        Nothing calls this yet. It is the reason the table exists rather than the
        dict: an interrupted job can be found after a restart instead of vanishing.
        """
        result = await self.session.execute(
            select(BackgroundJob).where(
                BackgroundJob.state == JOB_RUNNING,
                BackgroundJob.is_deleted.is_(False),
            )
        )
        return list(result.scalars().all())


__all__ = ["JobRepository"]
