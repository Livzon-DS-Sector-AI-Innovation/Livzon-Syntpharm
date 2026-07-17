"""0038_add_product_sync_config

Revision ID: 1f550ec06f66
Revises: 0037_drop_user_role
Create Date: 2026-07-15 11:04:16.286770
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '1f550ec06f66'
down_revision: Union[str, None] = '0037_drop_user_role'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "product_outputs",
        sa.Column("feishu_record_id", sa.String(128), nullable=True, comment="飞书多维表格记录ID"),
        schema="production",
    )
    op.add_column(
        "product_outputs",
        sa.Column(
            "sync_status",
            sa.String(20),
            nullable=False,
            server_default="local_only",
            comment="同步状态: local_only/synced/conflict",
        ),
        schema="production",
    )

    op.create_table(
        "product_sync_configs",
        sa.Column("product_id", sa.Uuid(), nullable=False, comment="关联产品ID"),
        sa.Column("app_token", sa.String(128), nullable=False, comment="飞书多维表格 app_token"),
        sa.Column("table_id", sa.String(128), nullable=False, comment="飞书表格 table_id"),
        sa.Column("field_mapping", sa.Text(), nullable=True, comment="字段映射配置 JSON"),
        sa.Column("auto_sync", sa.Boolean(), nullable=False, comment="是否自动同步"),
        sa.Column("last_sync_at", sa.String(64), nullable=True, comment="最后同步时间"),
        sa.Column("sync_direction", sa.String(20), nullable=False, comment="同步方向: push/pull/bidirectional"),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["identity.users.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["production.products.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["identity.users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", name="uq_product_sync_config_product"),
        schema="production",
    )
    op.create_index(
        op.f("ix_production_product_sync_configs_product_id"),
        "product_sync_configs",
        ["product_id"],
        unique=False,
        schema="production",
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_production_product_sync_configs_product_id"),
        table_name="product_sync_configs",
        schema="production",
    )
    op.drop_table("product_sync_configs", schema="production")
    op.drop_column("product_outputs", "sync_status", schema="production")
    op.drop_column("product_outputs", "feishu_record_id", schema="production")