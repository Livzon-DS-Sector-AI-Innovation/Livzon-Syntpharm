"""quality reminder tables

Revision ID: 0086_quality_reminder_tables
Revises: 0085_merge_0068_0084_heads
Create Date: 2026-10-20

补齐质量模块两张「提醒配置」表。代码中已有 SQL 直接读写这两张表，但历史迁移
从未创建，导致以下接口 500：
- GET /api/v1/quality/deviation-settings/rules
- GET /api/v1/quality/reagent-reminder/low-stock

仅涉及 quality 模块 `qms` schema，符合单模块迁移原则。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0086_quality_reminder_tables"
down_revision: str = "0085_merge_0068_0084_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "qms_deviation_reminder_rules",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("deviation_type", sa.String(64), nullable=True),
        sa.Column("urgency_level", sa.String(64), nullable=True),
        sa.Column("auto_reminder", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("reminder_time", sa.String(16), nullable=True),
        sa.Column("message_template", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="qms",
    )

    op.create_table(
        "qms_reagent_item_reminder_config",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("reagent_name", sa.String(255), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="qms",
    )
    op.create_index(
        "ix_qms_reagent_item_reminder_config_reagent_name",
        "qms_reagent_item_reminder_config",
        ["reagent_name"],
        unique=True,
        schema="qms",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_qms_reagent_item_reminder_config_reagent_name",
        table_name="qms_reagent_item_reminder_config",
        schema="qms",
    )
    op.drop_table("qms_reagent_item_reminder_config", schema="qms")
    op.drop_table("qms_deviation_reminder_rules", schema="qms")
