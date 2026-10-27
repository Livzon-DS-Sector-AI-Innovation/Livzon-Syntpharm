"""identity revoked sessions table

Revision ID: 0091_identity_revoked_sessions
Revises: 0090_merge_0073_0089_heads
Create Date: 2026-10-26

新增 `identity.revoked_sessions`：被吊销会话（jti）的持久化记录。

主存储仍是 Redis 吊销黑名单；本表用于 Redis 故障时认证依赖降级查库
（fail-closed，替代此前「按未吊销放行」的 fail-open 残留风险，
PR #121 审计 Cat 4 条目）。

仅涉及 identity 模块 `identity` schema。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0091_identity_revoked_sessions"
down_revision: str = "0090_merge_0073_0089_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "revoked_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("jti", sa.String(64), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        schema="identity",
    )
    op.create_index(
        "ix_identity_revoked_sessions_jti",
        "revoked_sessions",
        ["jti"],
        unique=True,
        schema="identity",
    )
    op.create_index(
        "ix_identity_revoked_sessions_user_id",
        "revoked_sessions",
        ["user_id"],
        schema="identity",
    )
    op.create_index(
        "ix_identity_revoked_sessions_expires_at",
        "revoked_sessions",
        ["expires_at"],
        schema="identity",
    )


def downgrade() -> None:
    op.drop_index("ix_identity_revoked_sessions_expires_at", table_name="revoked_sessions", schema="identity")
    op.drop_index("ix_identity_revoked_sessions_user_id", table_name="revoked_sessions", schema="identity")
    op.drop_index("ix_identity_revoked_sessions_jti", table_name="revoked_sessions", schema="identity")
    op.drop_table("revoked_sessions", schema="identity")
