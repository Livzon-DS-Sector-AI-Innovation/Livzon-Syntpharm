"""identity revoked sessions column comments and audit fks

Revision ID: 0092_identity_revoked_sessions_comments_fks
Revises: 0091_identity_revoked_sessions
Create Date: 2026-10-27

补齐 0091 建表时漏掉的两处「模型有、库里没有」的差异，使 `alembic check` 归零：

1. 三列的 comment（模型 mapped_column(comment=...) 带了，迁移没写）
2. `created_by` / `updated_by` 指向 `identity.users.id` 的外键（BaseModel 定义，迁移没加）

只动 identity schema，单模块迁移。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0092_identity_revoked_sessions_comments_fks"
down_revision: str = "0091_identity_revoked_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "revoked_sessions",
        "jti",
        schema="identity",
        existing_type=sa.String(64),
        existing_nullable=False,
        comment="JWT jti",
    )
    op.alter_column(
        "revoked_sessions",
        "user_id",
        schema="identity",
        existing_type=UUID(as_uuid=True),
        existing_nullable=True,
        comment="所属用户（旧 token 可能缺失）",
    )
    op.alter_column(
        "revoked_sessions",
        "expires_at",
        schema="identity",
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        comment="token 过期时间（过期后本记录可清理）",
    )
    op.create_foreign_key(
        "revoked_sessions_created_by_fkey",
        "revoked_sessions",
        "users",
        ["created_by"],
        ["id"],
        source_schema="identity",
        referent_schema="identity",
    )
    op.create_foreign_key(
        "revoked_sessions_updated_by_fkey",
        "revoked_sessions",
        "users",
        ["updated_by"],
        ["id"],
        source_schema="identity",
        referent_schema="identity",
    )


def downgrade() -> None:
    op.drop_constraint("revoked_sessions_updated_by_fkey", "revoked_sessions", schema="identity", type_="foreignkey")
    op.drop_constraint("revoked_sessions_created_by_fkey", "revoked_sessions", schema="identity", type_="foreignkey")
    op.alter_column(
        "revoked_sessions",
        "expires_at",
        schema="identity",
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        comment=None,
    )
    op.alter_column(
        "revoked_sessions",
        "user_id",
        schema="identity",
        existing_type=UUID(as_uuid=True),
        existing_nullable=True,
        comment=None,
    )
    op.alter_column(
        "revoked_sessions",
        "jti",
        schema="identity",
        existing_type=sa.String(64),
        existing_nullable=False,
        comment=None,
    )