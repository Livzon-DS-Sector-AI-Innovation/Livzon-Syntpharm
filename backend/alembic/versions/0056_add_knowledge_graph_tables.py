"""0056_add_knowledge_graph_tables

Revision ID: 0056_add_knowledge_graph_tables
Revises: d89b9d01b93a
Create Date: 2026-09-02 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = '0056_add_knowledge_graph_tables'
down_revision: Union[str, None] = 'd89b9d01b93a'
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names(schema='safety')
    
    # 知识图谱节点表
    if 'graph_knowledge_nodes' not in existing_tables:
        op.create_table(
            'graph_knowledge_nodes',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('name', sa.String(255), nullable=False, comment='节点名称'),
            sa.Column('node_type', sa.String(32), nullable=False, comment='节点类型: document/clause/entity/category/concept'),
            sa.Column('aliases', postgresql.JSON, nullable=True, comment='别名列表'),
            sa.Column('article_id', postgresql.UUID(as_uuid=True), nullable=True, comment='关联知识库文章ID'),
            sa.Column('entity_type', sa.String(32), nullable=True, comment='实体子类型'),
            sa.Column('ai_summary', sa.Text, nullable=True, comment='AI 摘要'),
            sa.Column('confidence', sa.Float, nullable=True, comment='AI 置信度 0-1'),
            sa.Column('status', sa.String(32), server_default='ai_generated', nullable=False, comment='状态'),
            sa.Column('merged_into_id', postgresql.UUID(as_uuid=True), nullable=True, comment='合并目标节点ID'),
            sa.Column('extra_metadata', postgresql.JSON, nullable=True, comment='扩展元数据'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('is_deleted', sa.Boolean, server_default='false', nullable=False),
            schema='safety',
        )

    # 知识图谱边表
    if 'graph_knowledge_edges' not in existing_tables:
        op.create_table(
            'graph_knowledge_edges',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('source_node_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('safety.graph_knowledge_nodes.id'), nullable=False, comment='源节点ID'),
            sa.Column('target_node_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('safety.graph_knowledge_nodes.id'), nullable=False, comment='目标节点ID'),
            sa.Column('relation_type', sa.String(32), nullable=False, comment='关系类型'),
            sa.Column('description', sa.Text, nullable=True, comment='关系说明'),
            sa.Column('evidence_text', sa.Text, nullable=True, comment='原文证据'),
            sa.Column('confidence', sa.Float, nullable=True, comment='AI 置信度 0-1'),
            sa.Column('status', sa.String(32), server_default='ai_generated', nullable=False, comment='状态'),
            sa.Column('extra_metadata', postgresql.JSON, nullable=True, comment='扩展元数据'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('is_deleted', sa.Boolean, server_default='false', nullable=False),
            schema='safety',
        )

    # 索引 - 检查是否已存在
    existing_indexes = set()
    if 'graph_knowledge_nodes' in existing_tables:
        for idx in inspector.get_indexes('graph_knowledge_nodes', schema='safety'):
            existing_indexes.add(idx['name'])
    if 'graph_knowledge_edges' in existing_tables:
        for idx in inspector.get_indexes('graph_knowledge_edges', schema='safety'):
            existing_indexes.add(idx['name'])
    
    if 'ix_graph_knowledge_nodes_node_type' not in existing_indexes:
        op.create_index('ix_graph_knowledge_nodes_node_type', 'graph_knowledge_nodes', ['node_type'], schema='safety')
    if 'ix_graph_knowledge_nodes_status' not in existing_indexes:
        op.create_index('ix_graph_knowledge_nodes_status', 'graph_knowledge_nodes', ['status'], schema='safety')
    if 'ix_graph_knowledge_nodes_article_id' not in existing_indexes:
        op.create_index('ix_graph_knowledge_nodes_article_id', 'graph_knowledge_nodes', ['article_id'], schema='safety')
    if 'ix_graph_knowledge_edges_source' not in existing_indexes:
        op.create_index('ix_graph_knowledge_edges_source', 'graph_knowledge_edges', ['source_node_id'], schema='safety')
    if 'ix_graph_knowledge_edges_target' not in existing_indexes:
        op.create_index('ix_graph_knowledge_edges_target', 'graph_knowledge_edges', ['target_node_id'], schema='safety')
    if 'ix_graph_knowledge_edges_relation' not in existing_indexes:
        op.create_index('ix_graph_knowledge_edges_relation', 'graph_knowledge_edges', ['relation_type'], schema='safety')


def downgrade() -> None:
    op.drop_index('ix_graph_knowledge_edges_relation', table_name='graph_knowledge_edges', schema='safety')
    op.drop_index('ix_graph_knowledge_edges_target', table_name='graph_knowledge_edges', schema='safety')
    op.drop_index('ix_graph_knowledge_edges_source', table_name='graph_knowledge_edges', schema='safety')
    op.drop_index('ix_graph_knowledge_nodes_article_id', table_name='graph_knowledge_nodes', schema='safety')
    op.drop_index('ix_graph_knowledge_nodes_status', table_name='graph_knowledge_nodes', schema='safety')
    op.drop_index('ix_graph_knowledge_nodes_node_type', table_name='graph_knowledge_nodes', schema='safety')
    op.drop_table('graph_knowledge_edges', schema='safety')
    op.drop_table('graph_knowledge_nodes', schema='safety')
