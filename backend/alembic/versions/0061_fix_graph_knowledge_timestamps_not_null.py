"""fix graph_knowledge timestamps to NOT NULL

Revision ID: 0061_fix_graph_knowledge_timestamps_not_null
Revises: 0060_add_foreign_keys_and_fix_nullable
Create Date: 2026-09-14 16:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0061_fix_graph_knowledge_timestamps_not_null'
down_revision: Union[str, None] = '0060_add_foreign_keys_and_fix_nullable'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Revert created_at/updated_at back to NOT NULL to match BaseModel definition
    op.alter_column('graph_knowledge_edges', 'created_at',
                    existing_type=sa.TIMESTAMP(timezone=True),
                    existing_server_default=sa.text('now()'),
                    nullable=False,
                    schema='safety')
    op.alter_column('graph_knowledge_edges', 'updated_at',
                    existing_type=sa.TIMESTAMP(timezone=True),
                    existing_server_default=sa.text('now()'),
                    nullable=False,
                    schema='safety')
    op.alter_column('graph_knowledge_nodes', 'created_at',
                    existing_type=sa.TIMESTAMP(timezone=True),
                    existing_server_default=sa.text('now()'),
                    nullable=False,
                    schema='safety')
    op.alter_column('graph_knowledge_nodes', 'updated_at',
                    existing_type=sa.TIMESTAMP(timezone=True),
                    existing_server_default=sa.text('now()'),
                    nullable=False,
                    schema='safety')


def downgrade() -> None:
    op.alter_column('graph_knowledge_nodes', 'updated_at',
                    existing_type=sa.TIMESTAMP(timezone=True),
                    existing_server_default=sa.text('now()'),
                    nullable=True,
                    schema='safety')
    op.alter_column('graph_knowledge_nodes', 'created_at',
                    existing_type=sa.TIMESTAMP(timezone=True),
                    existing_server_default=sa.text('now()'),
                    nullable=True,
                    schema='safety')
    op.alter_column('graph_knowledge_edges', 'updated_at',
                    existing_type=sa.TIMESTAMP(timezone=True),
                    existing_server_default=sa.text('now()'),
                    nullable=True,
                    schema='safety')
    op.alter_column('graph_knowledge_edges', 'created_at',
                    existing_type=sa.TIMESTAMP(timezone=True),
                    existing_server_default=sa.text('now()'),
                    nullable=True,
                    schema='safety')
