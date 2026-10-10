"""Durable record of a user-triggered background job.

`AGENTS.md:308` prohibits `asyncio.create_task()` for business logic precisely
because it cannot be retried, monitored, or **survived** — 无法重试、无法监控、
**重启后丢失**. `app/core/jobs.py` exports `spawn_task`, which *is*
`asyncio.create_task` re-exported, so the prohibition applies to it too. That file
carries a standing TODO to migrate to a real queue.

This table is the durable half of that migration. A job's state is a row, so:

- a client can poll **after** a restart and still get an answer
- a second worker sees the same jobs
- a crashed job is discoverable — it is left `running`, which is a fact worth seeing
- a retry can be reasoned about, because its outcome is recorded

It does **not** make a job re-runnable. Retry safety still has to come from the data
being written (an idempotent write, or a unique constraint) — see `AGENTS.md:314`,
所有重试操作必须是幂等的. This table records what happened; it does not decide whether
repeating it is safe.

Placement: `core`, the shared platform schema (`AGENTS.md:172`), because the job
primitive is cross-module — quality, energy and safety all schedule work.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel

# The only states. `running` is where a job is left if the process dies — that is
# the point of the table: an unfinished row is visible, not lost.
JOB_RUNNING = "running"
JOB_DONE = "done"
JOB_FAILED = "failed"


class BackgroundJob(BaseModel):
    """One background job's lifecycle."""

    __tablename__ = "background_jobs"
    # The indexes are declared here, not only in the migration: alembic compares the
    # model to the database, and an index that exists in one but not the other reads
    # as a difference to remove. `alembic check` caught exactly that.
    __table_args__ = (
        Index("ix_background_jobs_state", "state"),
        Index("ix_background_jobs_name_created", "name", "created_at"),
        {"schema": "core", "comment": "用户触发的后台任务"},
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Task name, e.g. static-data-hplc-import",
    )
    state: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=JOB_RUNNING,
        comment="running/done/failed",
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Populated when state=done",
    )
    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Populated when state=failed",
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def is_finished(self) -> bool:
        return self.state in (JOB_DONE, JOB_FAILED)


__all__ = ["JOB_DONE", "JOB_FAILED", "JOB_RUNNING", "BackgroundJob"]
