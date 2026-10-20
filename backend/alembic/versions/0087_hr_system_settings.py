"""hr system settings table

Revision ID: 0087_hr_system_settings
Revises: 0086_quality_reminder_tables
Create Date: 2026-10-20

补齐 HR 系统设置表。`hr/api.py` 的 GET/PUT /hr/system-settings 已直接读写
`hr.system_settings`，但历史迁移从未创建，导致接口 500。

仅涉及 HR 模块 `hr` schema。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0087_hr_system_settings"
down_revision: str = "0086_quality_reminder_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(128), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="hr",
    )


def downgrade() -> None:
    op.drop_table("system_settings", schema="hr")
