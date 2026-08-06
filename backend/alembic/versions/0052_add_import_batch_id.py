"""0052_add_import_batch_id

Revision ID: 0052_add_import_batch_id
Revises: 0051_add_scheduled_task_tables
Create Date: 2026-08-06 10:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0052_add_import_batch_id'
down_revision: Union[str, None] = '0051_add_scheduled_task_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "product_outputs",
        sa.Column("import_batch_id", sa.String(64), nullable=True, comment="导入批次ID"),
        schema="production",
    )
    op.create_index(
        "ix_product_outputs_import_batch_id",
        "product_outputs",
        ["import_batch_id"],
        schema="production",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_product_outputs_import_batch_id",
        table_name="product_outputs",
        schema="production",
    )
    op.drop_column("product_outputs", "import_batch_id", schema="production")
