"""0059_add_deliverable_template_fields

Revision ID: 0059_add_deliverable_template_fields
Revises: 0058_add_doc_gen_core_tables
Create Date: 2026-09-10 11:00:00.000000

交付物模板管理支持上传 docx/dotx/doc 文档（合并版）：
- file_object_key: 模板文件存储键
- template_code: 关联内置模板的槽位定义 code
- file_name: 模板母本原始文件名
- file_ext: 模板母本扩展名（docx/dotx/doc）
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '0059_add_deliverable_template_fields'
down_revision: str | Sequence[str] | None = '0058_add_doc_gen_core_tables'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'rd_deliverable_templates',
        sa.Column('file_object_key', sa.String(length=500), nullable=True, comment='模板文件存储键'),
        schema='research',
    )
    op.add_column(
        'rd_deliverable_templates',
        sa.Column('template_code', sa.String(length=100), nullable=True, comment='关联内置模板的槽位定义 code'),
        schema='research',
    )
    op.add_column(
        'rd_deliverable_templates',
        sa.Column('file_name', sa.String(length=500), nullable=True, comment='模板母本原始文件名'),
        schema='research',
    )
    op.add_column(
        'rd_deliverable_templates',
        sa.Column('file_ext', sa.String(length=16), nullable=True, comment='模板母本扩展名（docx/dotx/doc）'),
        schema='research',
    )
    op.create_index(
        'ix_research_rd_deliverable_templates_template_code',
        'rd_deliverable_templates',
        ['template_code'],
        schema='research',
    )


def downgrade() -> None:
    op.drop_index('ix_research_rd_deliverable_templates_template_code', table_name='rd_deliverable_templates', schema='research')
    op.drop_column('rd_deliverable_templates', 'file_ext', schema='research')
    op.drop_column('rd_deliverable_templates', 'file_name', schema='research')
    op.drop_column('rd_deliverable_templates', 'template_code', schema='research')
    op.drop_column('rd_deliverable_templates', 'file_object_key', schema='research')
