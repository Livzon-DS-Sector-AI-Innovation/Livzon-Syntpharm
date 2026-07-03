"""add products table and product_id to product_outputs

Revision ID: add_products_001
Revises: 7f62bb585f8f
Create Date: 2026-06-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_products_001"
down_revision: str | None = "7f62bb585f8f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 创建 products 表
    op.create_table(
        "products",
        sa.Column("workshop", sa.String(length=64), nullable=False, comment="车间名称"),
        sa.Column("name", sa.String(length=255), nullable=False, comment="产品名称"),
        sa.Column("description", sa.Text(), nullable=True, comment="产品描述"),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workshop", "name", name="uq_product_workshop_name"),
        schema="production",
    )
    op.create_index(
        "ix_products_workshop", "products", ["workshop"], schema="production"
    )

    # 给 product_outputs 表添加 product_id 字段
    op.add_column(
        "product_outputs",
        sa.Column("product_id", sa.Uuid(), nullable=True, comment="关联产品ID"),
        schema="production",
    )
    op.create_index(
        "ix_product_outputs_product_id",
        "product_outputs",
        ["product_id"],
        schema="production",
    )
    op.create_foreign_key(
        "fk_product_outputs_product_id",
        "product_outputs",
        "products",
        ["product_id"],
        ["id"],
        source_schema="production",
        referent_schema="production",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_product_outputs_product_id",
        "product_outputs",
        schema="production",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_product_outputs_product_id",
        table_name="product_outputs",
        schema="production",
    )
    op.drop_column("product_outputs", "product_id", schema="production")
    op.drop_index("ix_products_workshop", table_name="products", schema="production")
    op.drop_table("products", schema="production")
