"""0042_add_chapter_asset_usages

Revision ID: 2eb6d687679e
Revises: 6379b65e0052
Create Date: 2026-07-15 17:59:53.152467
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2eb6d687679e'
down_revision: Union[str, None] = '6379b65e0052'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('chapter_asset_usages',
    sa.Column('product_dossier_id', sa.UUID(), nullable=False, comment='品种资料ID'),
    sa.Column('chapter_id', sa.UUID(), nullable=False, comment='章节ID'),
    sa.Column('asset_id', sa.UUID(), nullable=False, comment='素材ID'),
    sa.Column('usage_type', sa.String(length=50), nullable=False, comment='使用类型: own/inherited'),
    sa.Column('is_selected', sa.Boolean(), server_default='true', nullable=False, comment='是否实际用于本章节'),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
    sa.ForeignKeyConstraint(['asset_id'], ['dossier_writer.chapter_assets.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['chapter_id'], ['dossier_writer.dossier_chapters.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['created_by'], ['identity.users.id'], ),
    sa.ForeignKeyConstraint(['product_dossier_id'], ['dossier_writer.product_dossiers.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['updated_by'], ['identity.users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    schema='dossier_writer'
    )

    # Fix production index names to match model (schema-qualified names)
    op.drop_index('ix_product_outputs_product_id', table_name='product_outputs', schema='production')
    op.drop_index('ix_product_outputs_production_date', table_name='product_outputs', schema='production')
    op.drop_index('ix_product_outputs_workshop', table_name='product_outputs', schema='production')
    op.create_index('ix_production_product_outputs_product_id', 'product_outputs', ['product_id'], unique=False, schema='production')
    op.create_index('ix_production_product_outputs_workshop', 'product_outputs', ['workshop'], unique=False, schema='production')
    op.drop_index('ix_products_workshop', table_name='products', schema='production')
    op.create_index('ix_production_products_workshop', 'products', ['workshop'], unique=False, schema='production')


def downgrade() -> None:
    op.drop_table('chapter_asset_usages', schema='dossier_writer')