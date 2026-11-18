"""quality department contacts: HR department reference

Revision ID: 0121_quality_contacts_department_ref
Revises: 0120_equipment_personnel_profile_ref
Create Date: 2026-11-17

Ticket #219: department references move to ``hr.departments.id``. The contact
configuration keeps the department *name* as its unique key (the deviation flow
resolves handlers by name), and gains ``hr_department_id`` so the row can be
tied to the department master.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0121_quality_contacts_department_ref"
down_revision: str | None = "0120_equipment_personnel_profile_ref"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "quality"
_TABLE = "department_contacts"
_INDEX = "ix_quality_department_contacts_hr_department_id"


def upgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column(
            "hr_department_id",
            sa.Uuid(),
            nullable=True,
            comment="部门主数据 hr.departments.id（逻辑引用）",
        ),
        schema=_SCHEMA,
    )
    op.create_index(_INDEX, _TABLE, ["hr_department_id"], schema=_SCHEMA)


def downgrade() -> None:
    op.drop_index(_INDEX, table_name=_TABLE, schema=_SCHEMA)
    op.drop_column(_TABLE, "hr_department_id", schema=_SCHEMA)