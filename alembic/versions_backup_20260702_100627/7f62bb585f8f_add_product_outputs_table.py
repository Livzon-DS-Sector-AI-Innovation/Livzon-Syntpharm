"""add product_outputs table

Revision ID: 7f62bb585f8f
Revises: 9a01e2d58ecb
Create Date: 2026-06-25 22:15:42.168130
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7f62bb585f8f"
down_revision: str | None = "9a01e2d58ecb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_outputs",
        sa.Column("workshop", sa.String(length=64), nullable=False, comment="车间名称"),
        sa.Column(
            "product_name", sa.String(length=255), nullable=False, comment="产品名称"
        ),
        sa.Column("batch_no", sa.String(length=64), nullable=False, comment="批号"),
        sa.Column("production_date", sa.Date(), nullable=False, comment="生产日期"),
        sa.Column("end_date", sa.Date(), nullable=True, comment="结束日期"),
        sa.Column("weight", sa.Float(), nullable=False, comment="重量(kg)"),
        sa.Column("unit", sa.String(length=20), nullable=False, comment="单位"),
        sa.Column("notes", sa.Text(), nullable=True, comment="备注"),
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
        schema="production",
    )
    op.create_index(
        "ix_product_outputs_workshop",
        "product_outputs",
        ["workshop"],
        schema="production",
    )
    op.create_index(
        "ix_product_outputs_production_date",
        "product_outputs",
        ["production_date"],
        schema="production",
    )
    op.create_index(
        "ix_product_outputs_product_name",
        "product_outputs",
        ["product_name"],
        schema="production",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_product_outputs_product_name",
        table_name="product_outputs",
        schema="production",
    )
    op.drop_index(
        "ix_product_outputs_production_date",
        table_name="product_outputs",
        schema="production",
    )
    op.drop_index(
        "ix_product_outputs_workshop", table_name="product_outputs", schema="production"
    )
    op.drop_table("product_outputs", schema="production")
