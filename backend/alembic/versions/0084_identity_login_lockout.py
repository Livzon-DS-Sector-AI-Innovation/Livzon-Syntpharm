"""identity_login_lockout

Revision ID: 0084_identity_login_lockout
Revises: 0083_identity_user_credentials_fields
Create Date: 2026-10-14

登录防暴力破解：
- `identity.users.failed_login_attempts`：连续登录失败次数（成功登录清零）。
- `identity.users.locked_until`：账号锁定截止时间（失败超限后锁定，期间拒绝登录）。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0084_identity_login_lockout"
down_revision: str | None = "0083_identity_user_credentials_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "failed_login_attempts",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
            comment="连续登录失败次数",
        ),
        schema="identity",
    )
    op.add_column(
        "users",
        sa.Column(
            "locked_until",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="账号锁定截止时间（失败次数超限后锁定）",
        ),
        schema="identity",
    )


def downgrade() -> None:
    op.drop_column("users", "locked_until", schema="identity")
    op.drop_column("users", "failed_login_attempts", schema="identity")
