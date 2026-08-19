"""add rd_report_templates table and filing_content fields

Revision ID: 2026_08_19_report_templates
Revises: a97e963a4ad3
Create Date: 2026-08-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '2026_08_19_report_templates'
down_revision = 'a97e963a4ad3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建 research schema（如果不存在）
    op.execute('CREATE SCHEMA IF NOT EXISTS research')
    
    # 创建 rd_report_templates 表
    op.create_table(
        'rd_report_templates',
        sa.Column('id', sa.UUID(), primary_key=True, nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False, comment='模板名称'),
        sa.Column('description', sa.Text(), comment='模板描述'),
        sa.Column('content_md', sa.Text(), nullable=False, comment='模板内容(Markdown)'),
        sa.Column('meta_info', postgresql.JSON(astext_type=sa.Text()), comment='模板元数据(info)'),
        sa.Column('category', sa.String(length=50), nullable=False, server_default='general', comment='分类：process_optimization, validation, etc.'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', comment='是否启用'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', sa.UUID(), sa.ForeignKey('identity.users.id')),
        sa.Column('updated_by', sa.UUID(), sa.ForeignKey('identity.users.id')),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false', default=False),
        schema='research'
    )
    
    # 在 rd_initiations 表中添加 filing_content 字段
    op.add_column('rd_initiations',
        sa.Column('filing_content', sa.Text(), comment='国内申报信息'),
        schema='research'
    )
    
    # 在 rd_research_findings 表中添加 filing_content 字段
    op.add_column('rd_research_findings',
        sa.Column('filing_content', sa.Text(), comment='国内申报信息'),
        schema='research'
    )


def downgrade() -> None:
    # 删除 filing_content 字段
    op.drop_column('rd_research_findings', 'filing_content', schema='research')
    op.drop_column('rd_initiations', 'filing_content', schema='research')
    
    # 删除 rd_report_templates 表
    op.drop_table('rd_report_templates', schema='research')
