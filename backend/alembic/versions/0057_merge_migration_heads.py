"""0057_merge_migration_heads

Revision ID: 0057_merge_migration_heads
Revises: 0055_add_sync_operation_log, 0056_add_energy_product_conversion_table
Create Date: 2026-08-31 12:11:08.860636
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0057_merge_migration_heads'
down_revision: Union[str, Sequence[str], None] = ('0055_add_sync_operation_log', '0056_add_energy_product_conversion_table')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
