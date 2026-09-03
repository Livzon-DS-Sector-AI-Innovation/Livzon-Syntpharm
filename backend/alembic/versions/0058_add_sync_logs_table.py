"""Add sync_logs table for equipment audit trail

Revision ID: 0058_add_sync_logs_table
Revises: 0057_merge_migration_heads
Create Date: 2026-09-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '0058_add_sync_logs_table'
down_revision = '0057_merge_migration_heads'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create equipment schema if not exists
    op.execute("CREATE SCHEMA IF NOT EXISTS equipment")
    
    # Create sync_logs table in equipment schema
    op.create_table(
        'sync_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('operator_id', sa.UUID(), nullable=True, comment='操作人ID'),
        sa.Column('file_name', sa.String(length=255), nullable=False, comment='上传的文件名'),
        sa.Column('summary', postgresql.JSON(astext_type=sa.Text()), nullable=False, comment='同步统计摘要 {updated, inserted, migrated, deleted}'),
        sa.Column('changes_detail', postgresql.JSON(astext_type=sa.Text()), nullable=False, comment='详细变更列表 [{asset_no, field, old_val, new_val}]'),
        sa.Column('is_dry_run', sa.Boolean(), server_default='false', nullable=False, comment='是否为预演模式'),
        sa.Column('created_by', sa.UUID(), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.UUID(), nullable=True, comment='更新人ID'),
        sa.ForeignKeyConstraint(['operator_id'], ['identity.users.id'], name='fk_sync_logs_operator_id'),
        sa.ForeignKeyConstraint(['created_by'], ['identity.users.id'], name='fk_sync_logs_created_by'),
        sa.ForeignKeyConstraint(['updated_by'], ['identity.users.id'], name='fk_sync_logs_updated_by'),
        sa.PrimaryKeyConstraint('id'),
        schema='equipment'
    )


def downgrade() -> None:
    op.drop_table('sync_logs', schema='equipment')
