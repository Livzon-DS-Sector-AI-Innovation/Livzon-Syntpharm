"""add_foreign_keys_and_fix_nullable

Revision ID: 0060_add_foreign_keys_and_fix_nullable
Revises: 0059_add_ppt_generation_records
Create Date: 2026-09-14 13:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0060_add_foreign_keys_and_fix_nullable'
down_revision: Union[str, None] = '0059_add_ppt_generation_records'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE SCHEMA IF NOT EXISTS safety')
    op.alter_column('graph_knowledge_edges', 'relation_type',
                    existing_type=sa.String(length=32),
                    existing_nullable=False,
                    existing_server_default=False,
                    comment='关系类型: cites/supplements/replaces/belongs_to/related_to/conflicts_with',
                    schema='safety')
    op.alter_column('graph_knowledge_edges', 'status',
                    existing_type=sa.String(length=32),
                    existing_nullable=False,
                    existing_server_default=sa.text("'ai_generated'::character varying"),
                    comment='状态: ai_generated/human_confirmed/human_deleted/human_added',
                    schema='safety')
    op.alter_column('graph_knowledge_edges', 'created_at',
                    existing_type=sa.TIMESTAMP(timezone=True),
                    existing_server_default=sa.text('now()'),
                    nullable=True,
                    schema='safety')
    op.alter_column('graph_knowledge_edges', 'updated_at',
                    existing_type=sa.TIMESTAMP(timezone=True),
                    existing_server_default=sa.text('now()'),
                    nullable=True,
                    schema='safety')
    op.drop_index('ix_graph_knowledge_edges_relation', table_name='graph_knowledge_edges', schema='safety')
    op.drop_index('ix_graph_knowledge_edges_source', table_name='graph_knowledge_edges', schema='safety')
    op.drop_index('ix_graph_knowledge_edges_target', table_name='graph_knowledge_edges', schema='safety')
    op.create_foreign_key('fk_graph_knowledge_edges_created_by', 'graph_knowledge_edges', 'users',
                          ['created_by'], ['id'], source_schema='safety', referent_schema='identity')
    op.create_foreign_key('fk_graph_knowledge_edges_updated_by', 'graph_knowledge_edges', 'users',
                          ['updated_by'], ['id'], source_schema='safety', referent_schema='identity')
    op.alter_column('graph_knowledge_nodes', 'entity_type',
                    existing_type=sa.String(length=32),
                    existing_nullable=True,
                    existing_server_default=False,
                    comment='实体子类型: equipment/condition/location/operation/material/standard',
                    schema='safety')
    op.alter_column('graph_knowledge_nodes', 'status',
                    existing_type=sa.String(length=32),
                    existing_nullable=False,
                    existing_server_default=sa.text("'ai_generated'::character varying"),
                    comment='状态: ai_generated/human_confirmed/deprecated/merged',
                    schema='safety')
    op.alter_column('graph_knowledge_nodes', 'created_at',
                    existing_type=sa.TIMESTAMP(timezone=True),
                    existing_server_default=sa.text('now()'),
                    nullable=True,
                    schema='safety')
    op.alter_column('graph_knowledge_nodes', 'updated_at',
                    existing_type=sa.TIMESTAMP(timezone=True),
                    existing_server_default=sa.text('now()'),
                    nullable=True,
                    schema='safety')
    op.drop_index('ix_graph_knowledge_nodes_article_id', table_name='graph_knowledge_nodes', schema='safety')
    op.drop_index('ix_graph_knowledge_nodes_node_type', table_name='graph_knowledge_nodes', schema='safety')
    op.drop_index('ix_graph_knowledge_nodes_status', table_name='graph_knowledge_nodes', schema='safety')
    op.create_foreign_key('fk_graph_knowledge_nodes_created_by', 'graph_knowledge_nodes', 'users',
                          ['created_by'], ['id'], source_schema='safety', referent_schema='identity')
    op.create_foreign_key('fk_graph_knowledge_nodes_updated_by', 'graph_knowledge_nodes', 'users',
                          ['updated_by'], ['id'], source_schema='safety', referent_schema='identity')
    op.create_foreign_key('fk_ppt_generation_records_created_by', 'ppt_generation_records', 'users',
                          ['created_by'], ['id'], source_schema='safety', referent_schema='identity')
    op.create_foreign_key('fk_ppt_generation_records_updated_by', 'ppt_generation_records', 'users',
                          ['updated_by'], ['id'], source_schema='safety', referent_schema='identity')


def downgrade() -> None:
    op.drop_constraint('fk_ppt_generation_records_updated_by', 'ppt_generation_records', schema='safety', type_='foreignkey')
    op.drop_constraint('fk_ppt_generation_records_created_by', 'ppt_generation_records', schema='safety', type_='foreignkey')
    op.drop_constraint('fk_graph_knowledge_nodes_updated_by', 'graph_knowledge_nodes', schema='safety', type_='foreignkey')
    op.drop_constraint('fk_graph_knowledge_nodes_created_by', 'graph_knowledge_nodes', schema='safety', type_='foreignkey')
    op.create_index('ix_graph_knowledge_nodes_status', 'graph_knowledge_nodes', ['status'], schema='safety')
    op.create_index('ix_graph_knowledge_nodes_node_type', 'graph_knowledge_nodes', ['node_type'], schema='safety')
    op.create_index('ix_graph_knowledge_nodes_article_id', 'graph_knowledge_nodes', ['article_id'], schema='safety')
    op.alter_column('graph_knowledge_nodes', 'updated_at', existing_type=sa.TIMESTAMP(timezone=True), existing_server_default=sa.text('now()'), nullable=False, schema='safety')
    op.alter_column('graph_knowledge_nodes', 'created_at', existing_type=sa.TIMESTAMP(timezone=True), existing_server_default=sa.text('now()'), nullable=False, schema='safety')
    op.alter_column('graph_knowledge_nodes', 'status', existing_type=sa.String(length=32), existing_nullable=False, existing_server_default=sa.text("'ai_generated'::character varying"), comment='状态：ai_generated/human_confirmed/deprecated/merged', schema='safety')
    op.alter_column('graph_knowledge_nodes', 'entity_type', existing_type=sa.String(length=32), existing_nullable=True, comment='实体子类型', schema='safety')
    op.drop_constraint('fk_graph_knowledge_edges_updated_by', 'graph_knowledge_edges', schema='safety', type_='foreignkey')
    op.drop_constraint('fk_graph_knowledge_edges_created_by', 'graph_knowledge_edges', schema='safety', type_='foreignkey')
    op.create_index('ix_graph_knowledge_edges_target', 'graph_knowledge_edges', ['target_node_id'], schema='safety')
    op.create_index('ix_graph_knowledge_edges_source', 'graph_knowledge_edges', ['source_node_id'], schema='safety')
    op.create_index('ix_graph_knowledge_edges_relation', 'graph_knowledge_edges', ['relation_type'], schema='safety')
    op.alter_column('graph_knowledge_edges', 'updated_at', existing_type=sa.TIMESTAMP(timezone=True), existing_server_default=sa.text('now()'), nullable=False, schema='safety')
    op.alter_column('graph_knowledge_edges', 'created_at', existing_type=sa.TIMESTAMP(timezone=True), existing_server_default=sa.text('now()'), nullable=False, schema='safety')
    op.alter_column('graph_knowledge_edges', 'status', existing_type=sa.String(length=32), existing_nullable=False, existing_server_default=sa.text("'ai_generated'::character varying"), comment='状态', schema='safety')
    op.alter_column('graph_knowledge_edges', 'relation_type', existing_type=sa.String(length=32), existing_nullable=False, comment='关系类型', schema='safety')
