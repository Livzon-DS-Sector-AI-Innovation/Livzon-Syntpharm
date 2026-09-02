"""Add sync_logs table for equipment audit trail

Revision ID: 0046
Revises: fcb768b8df78
Create Date: 2026-09-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '0046'
down_revision = 'fcb768b8df78'
branch_labels = None
depends_on = None


def upgrade() -> None:
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
        sa.ForeignKeyConstraint(['operator_id'], ['identity.users.id'], name='fk_sync_logs_operator_id'),
        sa.PrimaryKeyConstraint('id'),
        schema='equipment'
    )


def downgrade() -> None:
    op.drop_table('sync_logs', schema='equipment')
