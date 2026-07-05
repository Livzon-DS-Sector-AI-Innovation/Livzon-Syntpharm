"""drop product schema

Revision ID: 0002_drop_product
Revises: 0001_baseline
Create Date: 2026-07-05 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0002_drop_product'
down_revision: Union[str, None] = '0001_baseline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table('products', schema='product')
    op.execute('DROP SCHEMA IF EXISTS product')


def downgrade() -> None:
    op.execute('CREATE SCHEMA IF NOT EXISTS product')
    op.create_table(
        'products',
        sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False, comment='产品名称'),
        sa.Column('product_type', sa.String(length=32), nullable=True, comment='产品剂型: API, 制品, 包装'),
        sa.Column('major_category', sa.String(length=100), nullable=True, comment='产品大类'),
        sa.Column('specification', sa.String(length=200), nullable=True, comment='规格'),
        sa.Column('dosage_form', sa.String(length=100), nullable=True, comment='剂型'),
        sa.Column('feishu_record_id', sa.String(length=100), nullable=True, comment='飞书多维表格记录ID'),
        sa.Column('feishu_synced_at', sa.DateTime(timezone=True), nullable=True, comment='飞书同步时间'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('products_pkey')),
        schema='product',
    )
    op.create_index('ix_products_feishu_record_id', 'products', ['feishu_record_id'], unique=False, schema='product')
    op.create_index('ix_products_major_category', 'products', ['major_category'], unique=False, schema='product')
    op.create_index('ix_products_name', 'products', ['name'], unique=False, schema='product')
    op.create_index('ix_products_product_type', 'products', ['product_type'], unique=False, schema='product')
