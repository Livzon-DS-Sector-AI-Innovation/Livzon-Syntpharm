"""update module_settings module column comment

Revision ID: 0003_update_comment
Revises: 0002_drop_product
Create Date: 2026-07-05 14:30:00.000000
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0003_update_comment'
down_revision: Union[str, None] = '0002_drop_product'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE SCHEMA IF NOT EXISTS core')
    op.alter_column(
        'module_settings',
        'module',
        schema='core',
        comment='Module name (safety, equipment, energy, hr, registration)',
    )


def downgrade() -> None:
    op.alter_column(
        'module_settings',
        'module',
        schema='core',
        comment='Module name (safety, equipment, energy, hr, regulatory_tracker)',
    )
