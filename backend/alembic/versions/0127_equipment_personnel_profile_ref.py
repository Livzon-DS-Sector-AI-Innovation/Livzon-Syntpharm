"""equipment personnel: HR profile reference

Revision ID: 0127_equipment_personnel_profile_ref
Revises: 0126_identity_users_preferences
Create Date: 2026-11-17

Ticket #219: equipment keeps its own personnel pool (role / category bindings)
but person references move to the HR people master. ``profile_id`` is the new
reference key (``hr.employee_profiles.id``); ``user_id`` stays as a legacy
column until the dual-track period ends.

``equipments.department_id`` now logically references ``hr.departments.id``.
Production data measured before this change held zero non-null department ids,
so no id remapping is required.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0127_equipment_personnel_profile_ref"
down_revision: str | None = "0126_identity_users_preferences"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "equipment"
_TABLE = "equipment_personnel"
_INDEX = "ix_equipment_personnel_profile_id"


def upgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column(
            "profile_id",
            sa.Uuid(),
            nullable=True,
            comment="人员主数据 hr.employee_profiles.id；user_id 为 legacy 兼容列",
        ),
        schema=_SCHEMA,
    )
    op.create_index(_INDEX, _TABLE, ["profile_id"], schema=_SCHEMA)
    op.execute(
        sa.text(
            "COMMENT ON COLUMN equipment.equipments.department_id IS "
            "'归属部门ID，逻辑引用 hr.departments.id（#219）'"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "COMMENT ON COLUMN equipment.equipments.department_id IS "
            "'归属部门ID，逻辑引用 identity.departments.id'"
        )
    )
    op.drop_index(_INDEX, table_name=_TABLE, schema=_SCHEMA)
    op.drop_column(_TABLE, "profile_id", schema=_SCHEMA)
