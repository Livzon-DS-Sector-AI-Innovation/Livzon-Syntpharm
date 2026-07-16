"""add local auth user fields

Revision ID: 0007_add_local_auth_user_fields
Revises: 0007_add_agent_gateway
Create Date: 2026-07-01 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_add_local_auth_user_fields"
down_revision: str | None = "0005_product_output"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Check if columns already exist before adding
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('users', schema='identity')]
    
    if 'username' not in columns:
        op.add_column(
            "users",
            sa.Column("username", sa.String(length=64), nullable=True),
            schema="identity",
        )
    if 'password_hash' not in columns:
        op.add_column(
            "users",
            sa.Column("password_hash", sa.Text(), nullable=True),
            schema="identity",
        )
    if 'role' not in columns:
        op.add_column(
            "users",
            sa.Column(
                "role",
                sa.String(length=20),
                server_default="user",
                nullable=False,
            ),
            schema="identity",
        )
    if 'status' not in columns:
        op.add_column(
            "users",
            sa.Column(
                "status",
                sa.String(length=20),
                server_default="active",
                nullable=False,
            ),
            schema="identity",
        )
    if 'auth_source' not in columns:
        op.add_column(
            "users",
            sa.Column(
                "auth_source",
                sa.String(length=20),
                server_default="feishu",
                nullable=False,
            ),
            schema="identity",
        )
    if 'last_login_at' not in columns:
        op.add_column(
            "users",
            sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
            schema="identity",
        )
    
    # Create unique constraint if it doesn't exist
    constraints = [c['name'] for c in inspector.get_unique_constraints('users', schema='identity')]
    if 'uq_identity_users_username' not in constraints:
        op.create_unique_constraint(
            "uq_identity_users_username", "users", ["username"], schema="identity"
        )


def downgrade() -> None:
    op.drop_constraint("uq_identity_users_username", "users", schema="identity")
    op.drop_column("users", "last_login_at", schema="identity")
    op.drop_column("users", "auth_source", schema="identity")
    op.drop_column("users", "status", schema="identity")
    op.drop_column("users", "role", schema="identity")
    op.drop_column("users", "password_hash", schema="identity")
    op.drop_column("users", "username", schema="identity")
