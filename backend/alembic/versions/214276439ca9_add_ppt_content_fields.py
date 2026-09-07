"""add_ppt_content_fields

Revision ID: 214276439ca9
Revises: 230e4133f731
Create Date: 2026-09-03 08:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '214276439ca9'
down_revision: Union[str, None] = '230e4133f731'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'knowledge_articles',
        sa.Column('ppt_content', sa.JSON(), nullable=True, comment='AI 生成的 PPT 内容 JSON'),
        schema='safety',
    )
    op.add_column(
        'knowledge_articles',
        sa.Column('ppt_generated_at', sa.DateTime(timezone=True), nullable=True, comment='PPT 生成时间'),
        schema='safety',
    )


def downgrade() -> None:
    op.drop_column('knowledge_articles', 'ppt_generated_at', schema='safety')
    op.drop_column('knowledge_articles', 'ppt_content', schema='safety')
