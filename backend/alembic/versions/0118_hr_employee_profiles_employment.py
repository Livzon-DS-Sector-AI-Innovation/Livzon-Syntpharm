"""hr employee profiles: current-employment flag and soft removal

Revision ID: 0118_hr_employee_profiles_employment
Revises: 0117_hr_org_sync_running_unique
Create Date: 2026-11-17

Ticket #219 makes ``hr.employee_profiles`` the single people master. A person
who leaves the Feishu directory must disappear from pickers while historical
ledgers keep their ``employee_profiles.id`` reference, so removal becomes a
flag instead of a delete:

* ``is_current`` marks the active employment row of an ``open_id``;
* ``removed_at`` records when the row stopped being current;
* the old single-column unique constraint is replaced by a partial unique index
  scoped to current rows, which lets a rejoining employee own a new row while
  the previous employment stays auditable.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0118_hr_employee_profiles_employment"
down_revision: str | None = "0117_hr_org_sync_running_unique"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "hr"
_TABLE = "employee_profiles"
_OLD_UNIQUE = "uq_hr_employee_profiles_open_id"
_CURRENT_UNIQUE = "uq_hr_employee_profiles_open_id_current"


def upgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column(
            "is_current",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="是否当前在任记录；离职/跌出目录置 false，历史行保留",
        ),
        schema=_SCHEMA,
    )
    op.add_column(
        _TABLE,
        sa.Column(
            "removed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="跌出目录/离职时标记时间",
        ),
        schema=_SCHEMA,
    )
    op.drop_constraint(_OLD_UNIQUE, _TABLE, type_="unique", schema=_SCHEMA)
    op.create_index(
        _CURRENT_UNIQUE,
        _TABLE,
        ["open_id"],
        unique=True,
        schema=_SCHEMA,
        postgresql_where=sa.text("is_current"),
    )


def downgrade() -> None:
    op.drop_index(_CURRENT_UNIQUE, table_name=_TABLE, schema=_SCHEMA)
    # Rejoining employees own more than one row per open_id; keep the current one
    # and drop the historical duplicates so the original unique constraint holds.
    op.execute(
        sa.text(
            """
            DELETE FROM hr.employee_profiles AS stale
            USING hr.employee_profiles AS keep
            WHERE stale.open_id = keep.open_id
              AND stale.id <> keep.id
              AND (keep.is_current OR keep.created_at > stale.created_at)
            """
        )
    )
    op.create_unique_constraint(_OLD_UNIQUE, _TABLE, ["open_id"], schema=_SCHEMA)
    op.drop_column(_TABLE, "removed_at", schema=_SCHEMA)
    op.drop_column(_TABLE, "is_current", schema=_SCHEMA)
