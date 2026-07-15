"""add chapter_asset_usages table

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建 chapter_asset_usages 表
    op.create_table(
        'chapter_asset_usages',
        sa.Column('product_dossier_id', UUID(as_uuid=True), nullable=False),
        sa.Column('chapter_id', UUID(as_uuid=True), nullable=False),
        sa.Column('asset_id', UUID(as_uuid=True), nullable=False),
        sa.Column('usage_type', sa.String(50), nullable=False, comment='使用类型: own/inherited'),
        sa.Column('is_selected', sa.Boolean(), nullable=False, server_default='true', comment='是否实际用于本章节'),
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', UUID(as_uuid=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.ForeignKeyConstraint(['product_dossier_id'], ['dossier_writer.product_dossiers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['chapter_id'], ['dossier_writer.dossier_chapters.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['asset_id'], ['dossier_writer.chapter_assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['identity.users.id']),
        sa.ForeignKeyConstraint(['updated_by'], ['identity.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('product_dossier_id', 'chapter_id', 'asset_id', name='uq_chapter_asset_usage'),
        schema='dossier_writer'
    )
    
    # 为已有的 chapter_assets 补录 usage 记录
    op.execute("""
        INSERT INTO dossier_writer.chapter_asset_usages
            (id, product_dossier_id, chapter_id, asset_id, usage_type, is_selected, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            dc.product_dossier_id,
            ca.chapter_id,
            ca.id,
            'own',
            true,
            NOW(),
            NOW()
        FROM dossier_writer.chapter_assets ca
        JOIN dossier_writer.dossier_chapters dc ON dc.id = ca.chapter_id
        WHERE ca.is_deleted = false
    """)


def downgrade() -> None:
    op.drop_table('chapter_asset_usages', schema='dossier_writer')
