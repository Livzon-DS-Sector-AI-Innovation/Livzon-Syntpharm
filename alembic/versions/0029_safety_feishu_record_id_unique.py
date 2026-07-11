"""Add partial unique index on feishu_record_id to prevent duplicate hazard creation.

当飞书 WebSocket 事件竞态导致并发 INSERT 时，此索引在数据库层面兜底。
Migration moved from safety/migrations/versions/ to standard alembic/versions/.

Revision ID: 0029_safety_feishu_record_id_unique
Revises: 0028_add_regulatory_tracker_tables
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0029_safety_feishu_record_id_unique"
down_revision: str | tuple[str, ...] | None = "0028_add_regulatory_tracker_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        WITH duplicates AS (
            SELECT feishu_record_id
            FROM safety.hazard_reports
            WHERE is_deleted = false
              AND feishu_record_id IS NOT NULL
            GROUP BY feishu_record_id
            HAVING COUNT(*) > 1
        ),
        keep AS (
            SELECT DISTINCT ON (feishu_record_id) id
            FROM safety.hazard_reports
            WHERE feishu_record_id IN (SELECT feishu_record_id FROM duplicates)
              AND is_deleted = false
            ORDER BY feishu_record_id, created_at ASC
        )
        UPDATE safety.hazard_reports
        SET is_deleted = true, updated_at = now()
        WHERE feishu_record_id IN (SELECT feishu_record_id FROM duplicates)
          AND is_deleted = false
          AND id NOT IN (SELECT id FROM keep)
    """)

    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_hazard_reports_feishu_record_id
        ON safety.hazard_reports (feishu_record_id)
        WHERE is_deleted = false AND feishu_record_id IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS safety.uq_hazard_reports_feishu_record_id")