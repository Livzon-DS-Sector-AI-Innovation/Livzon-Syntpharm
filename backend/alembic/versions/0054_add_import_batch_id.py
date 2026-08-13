"""0054_add_import_batch_id

Revision ID: 0054_add_import_batch_id
Revises: 0053_add_dossier_unique_indexes_and_cleanup
Create Date: 2026-08-06 10:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0054_add_import_batch_id'
down_revision: Union[str, None] = '0053_add_dossier_unique_indexes_and_cleanup'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'product_outputs',
        sa.Column('import_batch_id', sa.String(), nullable=True),
        schema='production',
    )


def downgrade() -> None:
    op.drop_column('product_outputs', 'import_batch_id', schema='production')
