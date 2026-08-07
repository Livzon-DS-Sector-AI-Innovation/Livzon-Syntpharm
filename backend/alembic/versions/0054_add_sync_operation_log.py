"""0054_add_sync_operation_log

Revision ID: 0054_add_sync_operation_log
Revises: 0053_add_import_batch_id
Create Date: 2026-08-06 11:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '0054_add_sync_operation_log'
down_revision: Union[str, None] = '0053_add_import_batch_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sync_operation_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, comment="日志 ID"),
        sa.Column("product_id", sa.String(36), nullable=False, comment="产品 ID"),
        sa.Column("operation_type", sa.String(20), nullable=False, comment="操作类型：push/pull"),
        sa.Column("records", sa.JSON, nullable=False, comment="操作记录"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False, comment="更新时间"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("identity.users.id"), nullable=True, comment="创建人"),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("identity.users.id"), nullable=True, comment="更新人"),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false", comment="是否删除"),
        schema="production",
    )
    op.create_index(
        "ix_production_sync_operation_logs_product_id",
        "sync_operation_logs",
        ["product_id"],
        schema="production",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_production_sync_operation_logs_product_id",
        table_name="sync_operation_logs",
        schema="production",
    )
    op.drop_table("sync_operation_logs", schema="production")
