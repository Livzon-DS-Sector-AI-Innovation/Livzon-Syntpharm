"""add ocr_extraction_tasks table

Revision ID: 0057_add_ocr_extraction_tasks
Revises: 0056_recreate_qms_reagent_reminder_config
Create Date: 2026-09-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0060_add_ocr_extraction_tasks'
down_revision: Union[str, None] = '0059_recreate_qms_reagent_reminder_config'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('ocr_extraction_tasks',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=False, comment='素材ID'),
    sa.Column('chapter_id', postgresql.UUID(as_uuid=True), nullable=True, comment='章节ID（可选，用于上下文）'),
    sa.Column('task_type', sa.String(length=50), nullable=False, comment='任务类型: preview_extraction/split_preview/field_fill'),
    sa.Column('status', sa.String(length=30), server_default=sa.text("'pending'::character varying"), nullable=False, comment='状态: pending/processing/completed/failed'),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True, comment='开始时间'),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True, comment='完成时间'),
    sa.Column('result_data', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='OCR提取结果JSON'),
    sa.Column('error_message', sa.Text(), nullable=True, comment='错误信息'),
    sa.Column('total_pages', sa.Integer(), nullable=True, comment='总页数'),
    sa.Column('processed_pages', sa.Integer(), server_default=sa.text('0'), nullable=False, comment='已处理页数'),
    sa.ForeignKeyConstraint(['asset_id'], ['dossier_writer.chapter_assets.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['chapter_id'], ['dossier_writer.dossier_chapters.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['created_by'], ['identity.users.id'], name='ocr_extraction_tasks_created_by_fkey', ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['updated_by'], ['identity.users.id'], name='ocr_extraction_tasks_updated_by_fkey', ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    schema='dossier_writer',
    comment='OCR提取任务表'
    )
    op.create_index('ix_ocr_extraction_tasks_asset_id', 'ocr_extraction_tasks', ['asset_id'], schema='dossier_writer')
    op.create_index('ix_ocr_extraction_tasks_created_at', 'ocr_extraction_tasks', ['created_at'], schema='dossier_writer')
    op.create_index('ix_ocr_extraction_tasks_status', 'ocr_extraction_tasks', ['status'], schema='dossier_writer')


def downgrade() -> None:
    op.drop_index('ix_ocr_extraction_tasks_status', table_name='ocr_extraction_tasks', schema='dossier_writer')
    op.drop_index('ix_ocr_extraction_tasks_created_at', table_name='ocr_extraction_tasks', schema='dossier_writer')
    op.drop_index('ix_ocr_extraction_tasks_asset_id', table_name='ocr_extraction_tasks', schema='dossier_writer')
    op.drop_table('ocr_extraction_tasks', schema='dossier_writer')
