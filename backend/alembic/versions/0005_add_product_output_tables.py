"""add product and product_outputs tables in production schema

Revision ID: 0005_product_output
Revises: 0004_reg_tracker
Create Date: 2026-07-06 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0005_product_output'
down_revision: Union[str, None] = '0004_reg_tracker'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'products',
        sa.Column('workshop', sa.String(length=64), nullable=False, comment='车间名称'),
        sa.Column('name', sa.String(length=255), nullable=False, comment='产品名称'),
        sa.Column('description', sa.Text(), nullable=True, comment='产品描述'),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['identity.users.id']),
        sa.ForeignKeyConstraint(['updated_by'], ['identity.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workshop', 'name', name='uq_product_workshop_name'),
        schema='production',
    )
    op.create_index('ix_products_workshop', 'products', ['workshop'], unique=False, schema='production')

    op.create_table(
        'product_outputs',
        sa.Column('product_id', sa.Uuid(), nullable=False, comment='关联产品ID'),
        sa.Column('workshop', sa.String(length=64), nullable=False, comment='车间名称'),
        sa.Column('product_name', sa.String(length=255), nullable=False, comment='产品名称（冗余字段）'),
        sa.Column('batch_no', sa.String(length=64), nullable=False, comment='批号'),
        sa.Column('production_date', sa.Date(), nullable=False, comment='生产日期'),
        sa.Column('end_date', sa.Date(), nullable=True, comment='结束日期'),
        sa.Column('weight', sa.Float(), nullable=False, server_default='0', comment='重量(kg)'),
        sa.Column('unit', sa.String(length=20), nullable=False, server_default='kg', comment='单位'),
        sa.Column('notes', sa.Text(), nullable=True, comment='备注'),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['identity.users.id']),
        sa.ForeignKeyConstraint(['updated_by'], ['identity.users.id']),
        sa.ForeignKeyConstraint(['product_id'], ['production.products.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='production',
    )
    op.create_index('ix_product_outputs_product_id', 'product_outputs', ['product_id'], unique=False, schema='production')
    op.create_index('ix_product_outputs_workshop', 'product_outputs', ['workshop'], unique=False, schema='production')
    op.create_index('ix_product_outputs_production_date', 'product_outputs', ['production_date'], unique=False, schema='production')


def downgrade() -> None:
    op.drop_index('ix_product_outputs_production_date', table_name='product_outputs', schema='production')
    op.drop_index('ix_product_outputs_workshop', table_name='product_outputs', schema='production')
    op.drop_index('ix_product_outputs_product_id', table_name='product_outputs', schema='production')
    op.drop_table('product_outputs', schema='production')
    op.drop_index('ix_products_workshop', table_name='products', schema='production')
    op.drop_table('products', schema='production')
