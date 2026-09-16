"""add_ppt_generation_records

Revision ID: 0059_add_ppt_generation_records
Revises: 0058_add_ppt_content_fields
Create Date: 2026-09-04 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = '0059_add_ppt_generation_records'
down_revision: Union[str, None] = '0058_add_ppt_content_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect as sa_inspect

    conn = op.get_bind()
    inspector = sa_inspect(conn)
    existing_tables = inspector.get_table_names(schema="safety")

    if "ppt_generation_records" not in existing_tables:
        op.create_table(
        'ppt_generation_records',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('article_id', UUID(as_uuid=True), sa.ForeignKey('safety.knowledge_articles.id'), nullable=False, comment='关联知识库文章ID'),
        sa.Column('file_name', sa.String(255), nullable=False, comment='文件名'),
        sa.Column('template', sa.String(32), nullable=False, comment='模板类型: training/briefing/audit'),
        sa.Column('style', sa.String(32), nullable=False, comment='配色风格: professional/modern/minimal'),
        sa.Column('page_count', sa.Integer, nullable=False, server_default='0', comment='幻灯片页数'),
        sa.Column('object_key', sa.String(500), nullable=False, comment='MinIO 对象路径'),
        sa.Column('error_message', sa.Text, nullable=True, comment='失败时的错误信息'),
        sa.Column('status', sa.String(32), nullable=False, server_default='success', comment='状态: success/failed'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', UUID(as_uuid=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean, nullable=False, server_default='false'),
        schema='safety',
        )
    # Index creation (only if table was just created or already exists)
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("ppt_generation_records", schema="safety")} if "ppt_generation_records" in existing_tables else set()
    if "ix_ppt_gen_records_article_id" not in existing_indexes:
        op.create_index(
            'ix_ppt_gen_records_article_id',
            'ppt_generation_records',
            ['article_id'],
            schema='safety',
            postgresql_where=sa.text('is_deleted = false'),
        )


def downgrade() -> None:
    op.drop_index('ix_ppt_gen_records_article_id', table_name='ppt_generation_records', schema='safety')
    op.drop_table('ppt_generation_records', schema='safety')
