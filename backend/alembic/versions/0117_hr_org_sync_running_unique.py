"""one running HR org sync

Revision ID: 0117_hr_org_sync_running_unique
Revises: 0116_hr_org_records
Create Date: 2026-11-15

A partial unique index makes the check-then-insert 409 race impossible: at most
one `hr.org_sync_runs` row may be `running`. Existing duplicate/stale running
rows are normalized first.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0117_hr_org_sync_running_unique"
down_revision: str | None = "0116_hr_org_records"
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
    # 双轨合并守卫：索引可能已由其他路径创建，IF NOT EXISTS 保证幂等
    op.execute(
        sa.text(
            f"CREATE UNIQUE INDEX IF NOT EXISTS {_INDEX} "
            f"ON {_SCHEMA}.{_RUNS} (status) WHERE status = 'running'"
        )
    )


def downgrade() -> None:
    op.drop_index(_INDEX, table_name=_RUNS, schema=_SCHEMA)
