"""add_production_module_tables

Revision ID: 0018_add_production_module_tables
Revises: 0019_add_permission_module_tables
Create Date: 2026-07-07 17:01:58.884884
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0018_add_production_module_tables'
down_revision: Union[str, None] = '0017_add_hr_module_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tables already created by 0005 — this migration is a no-op.
    pass


def downgrade() -> None:
    pass
