"""add deviation attachment comments

附件文档批注表：按 ``file_id`` 归集文档批注，与 ``review_opinions``（推进流程的审核意见）
严格分离。批注支持单条软删除、单条状态流转（open / resolved），因此独立建表而非塞进 JSONB。

Revision ID: 0113_add_deviation_attachment_comments
Revises: 0112_update_deviation_row_comments
Create Date: 2026-11-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0113_add_deviation_attachment_comments"
down_revision: str | None = "0112_update_deviation_row_comments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "quality"
_TABLE = "deviation_attachment_comment"


def _base_columns() -> list[sa.Column]:
    """与 app.shared.base_model.BaseModel 对齐的公共列。"""
    return [
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", PG_UUID(as_uuid=True), sa.ForeignKey("identity.users.id"), nullable=True),
        sa.Column("updated_by", PG_UUID(as_uuid=True), sa.ForeignKey("identity.users.id"), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        _TABLE,
        *_base_columns(),
        sa.Column(
            "ledger_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey(f"{_SCHEMA}.deviation_ledger.id"),
            nullable=False,
            comment="所属偏差台账",
        ),
        sa.Column("file_id", PG_UUID(as_uuid=True), nullable=False, comment="附件 file_id（稳定关联键，非 URL）"),
        sa.Column(
            "file_name",
            sa.String(length=255),
            nullable=False,
            comment="附件名快照（附件删除后仍可追溯）",
        ),
        sa.Column("page_no", sa.Integer(), nullable=True, comment="页码（1 起，文档级批注为空）"),
        sa.Column(
            "anchor_text",
            sa.String(length=500),
            nullable=True,
            comment="选中文本锚点（预留，Phase 2 高亮用）",
        ),
        sa.Column("content", sa.Text(), nullable=False, comment="批注正文"),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'open'"),
            nullable=False,
            comment="处理状态 open / resolved",
        ),
        sa.Column("author_name", sa.String(length=255), nullable=True, comment="作者姓名快照"),
        sa.Column("resolved_by", PG_UUID(as_uuid=True), nullable=True, comment="解决人"),
        sa.Column("resolved_by_name", sa.String(length=255), nullable=True, comment="解决人姓名快照"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True, comment="解决时间"),
        sa.CheckConstraint("status IN ('open', 'resolved')", name="ck_deviation_attachment_comment_status"),
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_deviation_attachment_comment_file",
        _TABLE,
        ["ledger_id", "file_id", "is_deleted"],
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_deviation_attachment_comment_ledger",
        _TABLE,
        ["ledger_id", "is_deleted"],
        schema=_SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_deviation_attachment_comment_ledger", table_name=_TABLE, schema=_SCHEMA)
    op.drop_index("ix_deviation_attachment_comment_file", table_name=_TABLE, schema=_SCHEMA)
    op.drop_table(_TABLE, schema=_SCHEMA)
