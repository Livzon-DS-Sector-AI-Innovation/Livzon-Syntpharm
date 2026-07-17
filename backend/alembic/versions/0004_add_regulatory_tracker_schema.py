"""add regulatory_tracker schema

Revision ID: 0004_reg_tracker
Revises: 0003_update_comment
Create Date: 2026-07-05 17:50:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0004_reg_tracker'
down_revision: Union[str, None] = '0003_update_comment'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create regulatory_tracker schema
    op.execute('CREATE SCHEMA IF NOT EXISTS regulatory_tracker')
    
    # Create data_sources table
    op.create_table(
        'data_sources',
        sa.Column('code', sa.String(50), nullable=False, comment='数据源编码，如 CDE, NMPA'),
        sa.Column('name', sa.String(200), nullable=False, comment='数据源名称'),
        sa.Column('base_url', sa.String(500), nullable=True, comment='基础URL'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true', comment='是否启用'),
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.UniqueConstraint('code'),
        schema='regulatory_tracker'
    )
    
    # Create data_channels table
    op.create_table(
        'data_channels',
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False, comment='所属数据源ID'),
        sa.Column('code', sa.String(100), nullable=False, comment='栏目编码，如 cde_domestic_guideline'),
        sa.Column('name', sa.String(200), nullable=False, comment='栏目名称'),
        sa.Column('list_url', sa.String(1000), nullable=True, comment='列表页URL'),
        sa.Column('adapter_name', sa.String(100), nullable=True, comment='适配器名称'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true', comment='是否启用'),
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['source_id'], ['regulatory_tracker.data_sources.id'], ondelete='CASCADE'),
        schema='regulatory_tracker'
    )
    
    # Create sync_jobs table
    op.create_table(
        'sync_jobs',
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_type', sa.String(50), nullable=False, comment='backfill/daily_sync/manual_sync/test'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, comment='pending/running/success/partial_failed/failed'),
        sa.Column('total_pages', sa.Integer(), nullable=True, comment='总页数'),
        sa.Column('checked_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('new_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('updated_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['source_id'], ['regulatory_tracker.data_sources.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['channel_id'], ['regulatory_tracker.data_channels.id'], ondelete='CASCADE'),
        schema='regulatory_tracker'
    )
    
    # Create sync_job_pages table
    op.create_table(
        'sync_job_pages',
        sa.Column('sync_job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False, comment='页码'),
        sa.Column('page_size', sa.Integer(), nullable=False, server_default='10', comment='每页条数'),
        sa.Column('total_records_on_page', sa.Integer(), nullable=False, server_default='0', comment='本页记录数'),
        sa.Column('new_records', sa.Integer(), nullable=False, server_default='0', comment='本页新增记录数'),
        sa.Column('status', sa.String(50), nullable=False, comment='pending/synced/failed'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['sync_job_id'], ['regulatory_tracker.sync_jobs.id'], ondelete='CASCADE'),
        schema='regulatory_tracker'
    )
    
    # Create regulatory_documents table
    op.create_table(
        'regulatory_documents',
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', sa.String(200), nullable=False, comment='文档唯一标识，如 zdyzIdCODE'),
        sa.Column('title', sa.String(1000), nullable=False),
        sa.Column('publish_date', sa.Date(), nullable=True),
        sa.Column('status_text', sa.String(100), nullable=True, comment='状态，如 颁布'),
        sa.Column('classification', sa.String(200), nullable=True, comment='分类，如 生物制品、化学药品'),
        sa.Column('original_url', sa.String(1000), nullable=True),
        sa.Column('is_new', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('first_found_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ai_summary', sa.Text(), nullable=True, comment='AI 生成的文档摘要'),
        sa.Column('ai_key_points', postgresql.JSONB(), nullable=True, comment='AI 提取的关键要点'),
        sa.Column('ai_relevance_score', sa.Float(), nullable=True, comment='AI 评估的相关性评分 (0-1)'),
        sa.Column('ai_analyzed_at', sa.DateTime(timezone=True), nullable=True, comment='AI 分析完成时间'),
        sa.Column('ai_analysis_status', sa.String(50), nullable=True, comment='AI 分析状态: pending/completed/failed'),
        sa.Column('document_category', sa.String(20), nullable=True, server_default='general', comment='系统分类: attention/general/archive/failed'),
        sa.Column('raw_data', postgresql.JSONB(), nullable=True),
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['source_id'], ['regulatory_tracker.data_sources.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['channel_id'], ['regulatory_tracker.data_channels.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('source_id', 'channel_id', 'document_id', name='uq_reg_docs_src_ch_doc'),
        schema='regulatory_tracker'
    )


def downgrade() -> None:
    op.drop_table('regulatory_documents', schema='regulatory_tracker')
    op.drop_table('sync_job_pages', schema='regulatory_tracker')
    op.drop_table('sync_jobs', schema='regulatory_tracker')
    op.drop_table('data_channels', schema='regulatory_tracker')
    op.drop_table('data_sources', schema='regulatory_tracker')
    op.execute('DROP SCHEMA IF EXISTS regulatory_tracker')
