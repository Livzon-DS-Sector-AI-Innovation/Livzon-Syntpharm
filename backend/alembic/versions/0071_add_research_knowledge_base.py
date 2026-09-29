"""0062_add_research_knowledge_base

Revision ID: 0062_add_research_knowledge_base
Revises: 0061_merge_0060_heads
Create Date: 2026-09-24 11:05:00.000000

研发管理「项目知识库」：
- rd_knowledge_bases: 研发项目 ↔ RAGFlow 数据集映射（一个项目至多一个有效知识库）
- rd_kb_documents: 知识库文档与解析进度镜像（资料本体与解析结果在 RAGFlow 侧）
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '0062_add_research_knowledge_base'
down_revision: str | Sequence[str] | None = '0061_merge_0060_heads'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _base_columns() -> list[sa.Column]:
    """公共审计列（与 app/shared/base_model.py 对齐）。"""
    return [
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
    ]


def _audit_fks(table: str) -> list[sa.ForeignKeyConstraint]:
    """审计列外键。"""
    return [
        sa.ForeignKeyConstraint(['created_by'], ['identity.users.id']),
        sa.ForeignKeyConstraint(['updated_by'], ['identity.users.id']),
    ]


def upgrade() -> None:
    # ── rd_knowledge_bases ──
    op.create_table(
        'rd_knowledge_bases',
        sa.Column('project_id', sa.Uuid(), nullable=False, comment='关联研发项目'),
        sa.Column('name', sa.String(length=200), nullable=False, comment='知识库名称'),
        sa.Column('description', sa.Text(), nullable=True, comment='用途说明'),
        sa.Column('provider', sa.String(length=32), nullable=False, comment='知识库提供方'),
        sa.Column('ragflow_dataset_id', sa.String(length=64), nullable=False, comment='RAGFlow 数据集 ID'),
        sa.Column('embedding_model', sa.String(length=200), nullable=True, comment='向量模型标识'),
        sa.Column('chunk_method', sa.String(length=32), nullable=False, comment='切片方式'),
        sa.Column('parser_config', sa.JSON(), nullable=True, comment='解析参数快照'),
        sa.Column('status', sa.String(length=32), nullable=False, comment='creating/active/failed'),
        sa.Column('last_error', sa.Text(), nullable=True, comment='最近一次失败原因'),
        sa.Column('document_count', sa.Integer(), nullable=False, comment='文档数'),
        sa.Column('chunk_count', sa.Integer(), nullable=False, comment='切片数'),
        sa.Column('token_count', sa.Integer(), nullable=False, comment='token 数'),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True, comment='最近一次与 RAGFlow 对账时间'),
        *_base_columns(),
        sa.ForeignKeyConstraint(['project_id'], ['research.rd_projects.id']),
        *_audit_fks('rd_knowledge_bases'),
        sa.PrimaryKeyConstraint('id'),
        schema='research',
    )
    op.create_index(
        'ix_research_rd_knowledge_bases_project', 'rd_knowledge_bases', ['project_id'], schema='research'
    )
    op.create_index(
        'ix_research_rd_knowledge_bases_dataset', 'rd_knowledge_bases', ['ragflow_dataset_id'], schema='research'
    )

    # ── rd_kb_documents ──
    op.create_table(
        'rd_kb_documents',
        sa.Column('kb_id', sa.Uuid(), nullable=False, comment='所属知识库'),
        sa.Column('ragflow_document_id', sa.String(length=64), nullable=False, comment='RAGFlow 文档 ID'),
        sa.Column('file_name', sa.String(length=500), nullable=False, comment='原始文件名'),
        sa.Column('file_ext', sa.String(length=32), nullable=False, comment='扩展名'),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False, comment='字节数'),
        sa.Column('sha256', sa.String(length=64), nullable=False, comment='内容哈希'),
        sa.Column('run_status', sa.String(length=16), nullable=False, comment='UNSTART/RUNNING/DONE/FAIL/CANCEL'),
        sa.Column('progress', sa.Float(), nullable=False, comment='解析进度 0~1'),
        sa.Column('progress_msg', sa.Text(), nullable=True, comment='解析日志'),
        sa.Column('chunk_count', sa.Integer(), nullable=False, comment='切片数'),
        sa.Column('token_count', sa.Integer(), nullable=False, comment='token 数'),
        sa.Column('last_error', sa.Text(), nullable=True, comment='解析失败原因'),
        sa.Column('parse_started_at', sa.DateTime(timezone=True), nullable=True, comment='提交解析时间'),
        sa.Column('parsed_at', sa.DateTime(timezone=True), nullable=True, comment='解析完成时间'),
        *_base_columns(),
        sa.ForeignKeyConstraint(['kb_id'], ['research.rd_knowledge_bases.id']),
        *_audit_fks('rd_kb_documents'),
        sa.PrimaryKeyConstraint('id'),
        schema='research',
    )
    op.create_index('ix_research_rd_kb_documents_kb', 'rd_kb_documents', ['kb_id'], schema='research')
    op.create_index(
        'ix_research_rd_kb_documents_ragflow', 'rd_kb_documents', ['ragflow_document_id'], schema='research'
    )


def downgrade() -> None:
    op.drop_index('ix_research_rd_kb_documents_ragflow', table_name='rd_kb_documents', schema='research')
    op.drop_index('ix_research_rd_kb_documents_kb', table_name='rd_kb_documents', schema='research')
    op.drop_table('rd_kb_documents', schema='research')
    op.drop_index('ix_research_rd_knowledge_bases_dataset', table_name='rd_knowledge_bases', schema='research')
    op.drop_index('ix_research_rd_knowledge_bases_project', table_name='rd_knowledge_bases', schema='research')
    op.drop_table('rd_knowledge_bases', schema='research')
