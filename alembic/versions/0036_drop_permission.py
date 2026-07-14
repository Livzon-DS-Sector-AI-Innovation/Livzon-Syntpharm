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
    op.drop_table("role_data_scope_overrides", schema="permission")
    op.drop_table("user_roles", schema="permission")
    op.drop_table("role_permissions", schema="permission")
    op.drop_table("permissions", schema="permission")
    op.drop_table("roles", schema="permission")
    op.execute("DROP SCHEMA IF EXISTS permission CASCADE")


def downgrade() -> None:
    pass