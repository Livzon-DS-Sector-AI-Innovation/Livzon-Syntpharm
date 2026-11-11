"""add deviation ledger detail fields

Revision ID: 0102_add_deviation_ledger_detail_fields
Revises: 0101_add_quality_deviation_ledger
Create Date: 2026-11-10

为《偏差台账》补齐详情所需字段：调查报告正文与版本、AI 分析、调查记录、审核意见、
附件元数据。JSONB 列统一 NOT NULL + 默认空数组，存量行自动获得默认值。

`quality.department_contacts` 与 `quality.department_weekly_confirmations` 在基线迁移中已存在，
本次只补 ORM 映射，不产生 DDL。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0102_add_deviation_ledger_detail_fields"
down_revision: str = "0101_add_quality_deviation_ledger"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "deviation_ledger"
_SCHEMA = "quality"

_JSON_COLUMNS: tuple[tuple[str, str], ...] = (
    ("attachments", "附件元数据"),
    ("investigation_records", "调查记录"),
    ("review_opinions", "审核意见"),
    ("report_versions", "报告版本"),
)


def upgrade() -> None:
    for name, comment in _JSON_COLUMNS:
        op.add_column(
            _TABLE,
            sa.Column(name, JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb"), comment=comment),
            schema=_SCHEMA,
        )
    op.add_column(
        _TABLE,
        sa.Column("ai_analysis", JSONB(), nullable=True, comment="AI 结构化分析"),
        schema=_SCHEMA,
    )
    op.add_column(
        _TABLE,
        sa.Column("report_content", sa.Text(), nullable=True, comment="调查报告正文"),
        schema=_SCHEMA,
    )


def downgrade() -> None:
    op.drop_column(_TABLE, "report_content", schema=_SCHEMA)
    op.drop_column(_TABLE, "ai_analysis", schema=_SCHEMA)
    for name, _comment in reversed(_JSON_COLUMNS):
        op.drop_column(_TABLE, name, schema=_SCHEMA)
