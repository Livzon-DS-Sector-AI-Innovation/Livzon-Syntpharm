"""add_background_jobs

A durable record of user-triggered background jobs. `AGENTS.md:308` prohibits
`asyncio.create_task()` for business logic because it cannot be retried,
monitored, or survived across a restart — 无法重试、无法监控、重启后丢失. The in-memory
`JobStore` has exactly those limits, so job state moves into a table.

Placed in `core`, the shared platform schema (`AGENTS.md:172`), because the job
primitive is cross-module: quality, energy and safety all schedule work. One
migration, one module — and `core` is the module that owns it.

Revision ID: 0068_add_background_jobs
Revises: 0067_recreate_quality_legacy_tables
Create Date: 2026-10-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0068_add_background_jobs"
down_revision: Union[str, None] = "0067_recreate_quality_legacy_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The `core` schema already exists on every environment this has run on, but
    # stating it explicitly is what the sibling core migrations do (0015, 0003) and
    # it is what `alembic check` compares against — without it, autogenerate reports
    # "CREATE SCHEMA IF NOT EXISTS core" as a pending difference forever.
    op.execute("CREATE SCHEMA IF NOT EXISTS core")

    op.create_table(
        "background_jobs",
        sa.Column("name", sa.String(length=200), nullable=False, comment="Task name, e.g. static-data-hplc-import"),
        sa.Column(
            "state",
            sa.String(length=20),
            nullable=False,
            server_default="running",
            comment="running/done/failed",
        ),
        sa.Column("result", postgresql.JSONB(), nullable=True, comment="Populated when state=done"),
        sa.Column("error", sa.Text(), nullable=True, comment="Populated when state=failed"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        # The standard contract every table on BaseModel carries.
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["identity.users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["identity.users.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="core",
        comment="用户触发的后台任务",
    )
    # The poll endpoint looks up one job by id, and a future sweeper will want the
    # unfinished ones. Both are cheap indexes on a small table.
    op.create_index(
        "ix_background_jobs_state",
        "background_jobs",
        ["state"],
        schema="core",
    )
    op.create_index(
        "ix_background_jobs_name_created",
        "background_jobs",
        ["name", "created_at"],
        schema="core",
    )


def downgrade() -> None:
    op.drop_index("ix_background_jobs_name_created", table_name="background_jobs", schema="core")
    op.drop_index("ix_background_jobs_state", table_name="background_jobs", schema="core")
    op.drop_table("background_jobs", schema="core")
