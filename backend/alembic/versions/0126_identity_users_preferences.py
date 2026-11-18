"""identity users: per-user preferences

Revision ID: 0126_identity_users_preferences
Revises: 0125_hr_employee_profiles_employment
Create Date: 2026-11-17

Ticket #219 turns ``identity.users`` into an authentication + preferences store.
This migration only adds the preferences column; the department-related columns
are dropped later (after every consumer reads people from HR) so no intermediate
commit breaks on a missing attribute.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0126_identity_users_preferences"
down_revision: str | None = "0125_hr_employee_profiles_employment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "identity"
_TABLE = "users"


def upgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column(
            "preferences",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="个人偏好（主题/语言等）；人员属性一律从 HR 读取",
        ),
        schema=_SCHEMA,
    )


def downgrade() -> None:
    op.drop_column(_TABLE, "preferences", schema=_SCHEMA)
