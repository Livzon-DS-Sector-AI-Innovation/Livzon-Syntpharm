"""add_ppt_content_fields

Revision ID: 0058_add_ppt_content_fields
Revises: 0057_merge_0056_heads
Create Date: 2026-09-03 08:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0058_add_ppt_content_fields'
down_revision: Union[str, None] = '0057_merge_0056_heads'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    import sqlalchemy as sa_ext
    from sqlalchemy import inspect as sa_inspect, text

    # Idempotency: check if columns already exist
    conn = op.get_bind()
    inspector = sa_inspect(conn)
    existing_cols = {c["name"] for c in inspector.get_columns("knowledge_articles", schema="safety")}

    if "ppt_content" not in existing_cols:
        op.add_column(
            'knowledge_articles',
            sa.Column('ppt_content', sa.JSON(), nullable=True, comment='AI 生成的 PPT 内容 JSON'),
            schema='safety',
        )
    if "ppt_generated_at" not in existing_cols:
        op.add_column(
            'knowledge_articles',
            sa.Column('ppt_generated_at', sa.DateTime(timezone=True), nullable=True, comment='PPT 生成时间'),
            schema='safety',
        )


def downgrade() -> None:
    op.drop_column('knowledge_articles', 'ppt_generated_at', schema='safety')
    op.drop_column('knowledge_articles', 'ppt_content', schema='safety')
