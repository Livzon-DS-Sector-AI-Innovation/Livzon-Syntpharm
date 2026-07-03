"""equipment_sync_20260702

Revision ID: 003_equipment
Revises: 002_production
Create Date: 2026-07-02 08:41:56.112106
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_equipment'
down_revision: Union[str, None] = '002_production'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE SCHEMA IF NOT EXISTS equipment')
    op.alter_column('equipment_role', 'scope',
               existing_type=sa.VARCHAR(length=50),
               server_default='global',
               existing_comment='作用域',
               existing_nullable=False,
               schema='equipment')


def downgrade() -> None:
    op.alter_column('equipment_role', 'scope',
               existing_type=sa.VARCHAR(length=50),
               server_default=sa.text("'''global'''::character varying"),
               existing_comment='作用域',
               existing_nullable=False,
               schema='equipment')
