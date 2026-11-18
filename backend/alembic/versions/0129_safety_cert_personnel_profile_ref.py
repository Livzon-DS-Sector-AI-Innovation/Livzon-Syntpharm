"""safety special operation personnel: HR profile reference

Revision ID: 0129_safety_cert_personnel_profile_ref
Revises: 0128_quality_contacts_department_ref
Create Date: 2026-11-17

Ticket #219: the certificate ledger keeps its module-specific data
(``personnel_no`` / ``name`` / certificate fields) and gains ``profile_id`` so
the holder can be tied to the HR people master. Name / department snapshots stay
because certificates are historical records.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0129_safety_cert_personnel_profile_ref"
down_revision: str | None = "0128_quality_contacts_department_ref"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "safety"
_TABLE = "special_operation_personnel"
_INDEX = "ix_safety_special_op_personnel_profile_id"


def upgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column(
            "profile_id",
            sa.Uuid(),
            nullable=True,
            comment="人员主数据 hr.employee_profiles.id（逻辑引用）",
        ),
        schema=_SCHEMA,
    )
    op.create_index(_INDEX, _TABLE, ["profile_id"], schema=_SCHEMA)


def downgrade() -> None:
    op.drop_index(_INDEX, table_name=_TABLE, schema=_SCHEMA)
    op.drop_column(_TABLE, "profile_id", schema=_SCHEMA)
