"""0064_add_kb_chunks_and_facts

Revision ID: 0064_add_kb_chunks_and_facts
Revises: 0063_add_doc_gen_corpus_documents
Create Date: 2026-09-28 09:40:00.000000

知识库切片索引（``research.rd_kb_chunks``）与知识库事实库（``research.rd_kb_facts``）。

- 切片索引：把 RAGFlow 的切片镜像到本地，按 ``content_hash`` 做增量判断，
  为事实抽取提供稳定底座（检索的「真相」仍在 RAGFlow）。
- 事实库：与模板解耦的结构化事实，跨任务复用；``locked`` 标记人工确认过的事实，
  自动流程不得覆盖或删除。

两张表都属于 research 模块的知识库能力增强，单迁移内一并创建。
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '0064_add_kb_chunks_and_facts'
down_revision: str | Sequence[str] | None = '0063_add_doc_gen_corpus_documents'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = 'research'
_CHUNK_TABLE = 'rd_kb_chunks'
_FACT_TABLE = 'rd_kb_facts'


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
    """审计列外键（命名与其它迁移保持一致）。"""
    return [
        sa.ForeignKeyConstraint(['created_by'], ['identity.users.id'], name=f'fk_{_SCHEMA}_{table}_created_by'),
        sa.ForeignKeyConstraint(['updated_by'], ['identity.users.id'], name=f'fk_{_SCHEMA}_{table}_updated_by'),
    ]


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names(schema=_SCHEMA))

    if _CHUNK_TABLE not in tables:
        op.create_table(
            _CHUNK_TABLE,
            sa.Column(
                'kb_id', sa.Uuid(), sa.ForeignKey('research.rd_knowledge_bases.id'), nullable=False, comment='所属知识库'
            ),
            sa.Column(
                'document_id',
                sa.Uuid(),
                sa.ForeignKey('research.rd_kb_documents.id'),
                nullable=True,
                comment='本地文档行（可空）',
            ),
            sa.Column('ragflow_document_id', sa.String(length=64), nullable=False, comment='RAGFlow 文档 ID'),
            sa.Column('ragflow_chunk_id', sa.String(length=64), nullable=False, comment='RAGFlow 切片 ID'),
            sa.Column('file_name', sa.String(length=500), nullable=False, comment='文档名（证据展示用）'),
            sa.Column('content', sa.Text(), nullable=False, comment='切片原文'),
            sa.Column('content_hash', sa.String(length=64), nullable=False, comment='内容哈希（增量判断）'),
            sa.Column('char_count', sa.Integer(), nullable=False, comment='字符数'),
            sa.Column(
                'facts_extracted_at',
                sa.DateTime(timezone=True),
                nullable=True,
                comment='事实抽取完成时间（空=未抽或内容已变）',
            ),
            sa.Column('facts_count', sa.Integer(), nullable=False, comment='本切片抽出的事实数'),
            *_base_columns(),
            *_audit_fks(_CHUNK_TABLE),
            sa.PrimaryKeyConstraint('id'),
            schema=_SCHEMA,
        )
        op.create_index(f'ix_{_SCHEMA}_{_CHUNK_TABLE}_kb', _CHUNK_TABLE, ['kb_id'], schema=_SCHEMA)
        op.create_index(
            f'ix_{_SCHEMA}_{_CHUNK_TABLE}_document', _CHUNK_TABLE, ['ragflow_document_id'], schema=_SCHEMA
        )

    if _FACT_TABLE not in tables:
        op.create_table(
            _FACT_TABLE,
            sa.Column(
                'kb_id', sa.Uuid(), sa.ForeignKey('research.rd_knowledge_bases.id'), nullable=False, comment='所属知识库'
            ),
            sa.Column(
                'chunk_id',
                sa.Uuid(),
                sa.ForeignKey('research.rd_kb_chunks.id'),
                nullable=True,
                comment='来源切片',
            ),
            sa.Column('document_name', sa.String(length=500), nullable=False, comment='来源文档名'),
            sa.Column('subject', sa.String(length=300), nullable=False, comment='主体（对象）'),
            sa.Column('predicate', sa.String(length=300), nullable=False, comment='谓词（属性/关系）'),
            sa.Column('value', sa.Text(), nullable=False, comment='值'),
            sa.Column('unit', sa.String(length=50), nullable=True, comment='单位'),
            sa.Column('quote', sa.Text(), nullable=False, comment='原文引用（证据）'),
            sa.Column('confidence', sa.Float(), nullable=False, comment='抽取置信度 0~1'),
            sa.Column('source', sa.String(length=16), nullable=False, comment='auto/human'),
            sa.Column('locked', sa.Boolean(), nullable=False, comment='人工确认后锁定，自动流程不得覆盖'),
            *_base_columns(),
            *_audit_fks(_FACT_TABLE),
            sa.PrimaryKeyConstraint('id'),
            schema=_SCHEMA,
        )
        op.create_index(f'ix_{_SCHEMA}_{_FACT_TABLE}_kb', _FACT_TABLE, ['kb_id'], schema=_SCHEMA)
        op.create_index(f'ix_{_SCHEMA}_{_FACT_TABLE}_chunk', _FACT_TABLE, ['chunk_id'], schema=_SCHEMA)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names(schema=_SCHEMA))
    for table, indexes in (
        (_FACT_TABLE, (f'ix_{_SCHEMA}_{_FACT_TABLE}_kb', f'ix_{_SCHEMA}_{_FACT_TABLE}_chunk')),
        (_CHUNK_TABLE, (f'ix_{_SCHEMA}_{_CHUNK_TABLE}_kb', f'ix_{_SCHEMA}_{_CHUNK_TABLE}_document')),
    ):
        if table not in tables:
            continue
        existing = {idx['name'] for idx in inspector.get_indexes(table, schema=_SCHEMA)}
        for index_name in indexes:
            if index_name in existing:
                op.drop_index(index_name, table_name=table, schema=_SCHEMA)
        op.drop_table(table, schema=_SCHEMA)
