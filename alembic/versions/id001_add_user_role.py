"""add user role field

Revision ID: id001
Revises: rd004
Create Date: 2026-06-29
"""

import sqlalchemy as sa

from alembic import op

revision = "id001"
down_revision = "rd004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(50),
            server_default="member",
            comment="角色: admin/manager/member/viewer",
            nullable=False,
        ),
        schema="identity",
    )


def downgrade() -> None:
    op.drop_column("users", "role", schema="identity")
