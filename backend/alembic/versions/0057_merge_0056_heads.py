"""merge_0056_heads

Revision ID: 0057_merge_0056_heads
Revises: 0056_add_knowledge_graph_tables, 0056_fix_daily_risk_report_and_special_op_index
Create Date: 2026-09-03 11:17:22.530832
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0057_merge_0056_heads'
down_revision: Union[str, Sequence[str], None] = ('0056_add_knowledge_graph_tables', '0056_fix_daily_risk_report_and_special_op_index', '0057_merge_migration_heads')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
