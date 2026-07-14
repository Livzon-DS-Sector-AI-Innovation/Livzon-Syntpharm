"""drop_user_role_column

Revision ID: 0037_drop_user_role
Revises: 0036_drop_permission
Create Date: 2026-07-14

Remove user.role column from identity.users.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0037_drop_user_role"
down_revision: str | None = "0036_drop_permission"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("users", "role", schema="identity")


def downgrade() -> None:
    op.add_column("users", sa.Column("role", sa.String(20), server_default="user"), schema="identity")