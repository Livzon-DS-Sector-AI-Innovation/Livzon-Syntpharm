"""drop legacy offboarding ledger

Revision ID: 0121_hr_drop_offboarding_records
Revises: 0120_hr_departure_person_optional
Create Date: 2026-11-13

离职管理页面改用 2026 离职台账（`hr.departure_records`），旧的
`hr.offboarding_records` 不再使用，删除以避免两套离职台账。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0121_hr_drop_offboarding_records"
down_revision: str = "0120_hr_departure_person_optional"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "offboarding_records"
_SCHEMA = "hr"


def upgrade() -> None:
    op.drop_table(_TABLE, schema=_SCHEMA)


def downgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("employee_id", sa.UUID(), sa.ForeignKey("hr.employees.id"), nullable=False),
        sa.Column("offboarding_date", sa.Date(), nullable=False),
        sa.Column("offboarding_type", sa.String(16), nullable=False, server_default="辞职"),
        sa.Column("reason", sa.String(512), nullable=True),
        sa.Column("handover_status", sa.String(16), nullable=False, server_default="待交接"),
        sa.Column("notes", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        schema=_SCHEMA,
    )
    op.create_index("ix_offboarding_employee_id", _TABLE, ["employee_id"], schema=_SCHEMA)
    op.create_index("ix_offboarding_date", _TABLE, ["offboarding_date"], schema=_SCHEMA)
