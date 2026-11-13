"""add deviation investigation drafts

调查记录草稿：调查人（含跨部门各行调查人）在提交前可暂存表单内容，按
``(author_id, department)`` 唯一存于台账 ``investigation_drafts`` JSONB 列。
选 JSONB 而非独立表：草稿与调查记录同生命周期、只按台账整体读取，无需独立查询。

Revision ID: 0133_add_deviation_investigation_drafts
Revises: 0132_hr_drop_offboarding_records
Create Date: 2026-11-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0133_add_deviation_investigation_drafts"
down_revision: str | None = "0132_hr_drop_offboarding_records"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "quality"
_TABLE = "deviation_ledger"
_COLUMN = "investigation_drafts"


def upgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column(
            _COLUMN,
            JSONB,
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
            comment="调查记录草稿 [{author_id, author_name, department, nonconformity_description,"
            " root_cause_analysis, risk_assessment, capa_proposals[], urgent_measures,"
            " attachment_file_ids[], updated_at}]，按 (author_id, department) 唯一",
        ),
        schema=_SCHEMA,
    )


def downgrade() -> None:
    op.drop_column(_TABLE, _COLUMN, schema=_SCHEMA)
