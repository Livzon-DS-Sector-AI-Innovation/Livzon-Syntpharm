"""identity_user_credentials_fields

Revision ID: 0083_identity_user_credentials_fields
Revises: 0082_create_permission_schema
Create Date: 2026-10-14

本地账号凭据相关字段与序列：
- `identity.users.must_change_password`：强制改密标记。管理员重置密码（含随机生成）
  后置 true，用户自助改密成功后置 false；前端据此把用户挡在改密页。
- `identity.users.password_updated_at`：密码最后修改时间（供用户管理展示与审计）。
- `identity.user_username_seq`：默认用户名自增号序列（`YTH000001`）。

飞书首次登录自动建号时，用户名为「前缀 + 序列号」，密码不自动生成（由管理员按需
随机生成并一次性展示），因此本迁移不涉及密码明文/密文列。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0083_identity_user_credentials_fields"
down_revision: str | None = "0082_create_permission_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment="是否强制修改密码（管理员重置后为 true）",
        ),
        schema="identity",
    )
    op.add_column(
        "users",
        sa.Column(
            "password_updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="密码最后修改时间",
        ),
        schema="identity",
    )
    # 默认用户名自增号：并发建号时用 nextval 保证唯一，避免 max(username)+1 竞态。
    # 已存在的同前缀账号（如历史 YTH000123）由应用层在分配时检测并跳过。
    op.execute("CREATE SEQUENCE IF NOT EXISTS identity.user_username_seq START WITH 1")


def downgrade() -> None:
    op.execute("DROP SEQUENCE IF EXISTS identity.user_username_seq")
    op.drop_column("users", "password_updated_at", schema="identity")
    op.drop_column("users", "must_change_password", schema="identity")
