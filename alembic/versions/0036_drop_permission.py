"""drop_permission_schema

Revision ID: 0036_drop_permission
Revises: 0035_drop_agent_tables
Create Date: 2026-07-14

Remove permission system: drop all permission schema tables and schema.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0036_drop_permission"
down_revision: str | None = "0035_drop_agent_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS permission.role_data_scope_overrides CASCADE")
    op.execute("DROP TABLE IF EXISTS permission.user_roles CASCADE")
    op.execute("DROP TABLE IF EXISTS permission.role_permissions CASCADE")
    op.execute("DROP TABLE IF EXISTS permission.permissions CASCADE")
    op.execute("DROP TABLE IF EXISTS permission.roles CASCADE")
    op.execute("DROP SCHEMA IF EXISTS permission CASCADE")


def downgrade() -> None:
    pass