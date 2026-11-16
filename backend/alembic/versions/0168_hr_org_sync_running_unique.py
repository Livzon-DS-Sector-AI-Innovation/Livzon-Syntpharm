"""one running HR org sync

Revision ID: 0168_hr_org_sync_running_unique
Revises: 0167_agent_ppt_video_coverage_and_pronunciation
Create Date: 2026-11-16

A partial unique index makes the check-then-insert 409 race impossible: at most
one `hr.org_sync_runs` row may be `running`. Existing duplicate/stale running
rows are normalized first.

uat 的 hr schema 由 0126-0137 增量链建成，没有这个索引；main 的 HR 代码
（org_service 的 IntegrityError → 409 分支）依赖它，因此在这里补上。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0168_hr_org_sync_running_unique"
down_revision: str | None = "0167_agent_ppt_video_coverage_and_pronunciation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "hr"
_RUNS = "org_sync_runs"
_INDEX = "uq_hr_org_sync_runs_running"


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            WITH ranked AS (
                SELECT id,
                       row_number() OVER (ORDER BY started_at DESC, id DESC) AS rn
                FROM hr.org_sync_runs
                WHERE status = 'running'
            )
            UPDATE hr.org_sync_runs AS r
            SET status = 'failed',
                finished_at = now(),
                error_message = 'normalized before unique running index'
            FROM ranked
            WHERE r.id = ranked.id
              AND ranked.rn > 1
            """
        )
    )
    op.create_index(
        _INDEX,
        _RUNS,
        ["status"],
        unique=True,
        schema=_SCHEMA,
        postgresql_where=sa.text("status = 'running'"),
    )


def downgrade() -> None:
    op.drop_index(_INDEX, table_name=_RUNS, schema=_SCHEMA)