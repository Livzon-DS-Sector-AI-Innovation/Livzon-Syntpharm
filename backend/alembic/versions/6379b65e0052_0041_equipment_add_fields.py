"""0041_equipment_add_fields

Revision ID: 6379b65e0052
Revises: 1f550ec06f66
Create Date: 2026-07-15 17:49:37.922995
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '6379b65e0052'
down_revision: Union[str, None] = '1f550ec06f66'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('equipments', sa.Column('equipment_tag', sa.String(length=100), nullable=True, comment='设备位号'), schema='equipment')
    op.add_column('equipments', sa.Column('equipment_class', sa.String(length=10), nullable=False, server_default='C', comment='设备分类：A/B/C'), schema='equipment')
    op.add_column('equipments', sa.Column('category_description', sa.String(length=200), nullable=True, comment='资产类别说明'), schema='equipment')
    op.add_column('equipments', sa.Column('location_text', sa.String(length=200), nullable=True, comment='设备位置（文本描述）'), schema='equipment')
    op.add_column('equipments', sa.Column('current_cost', sa.Float(), nullable=True, comment='当前成本（元）'), schema='equipment')
    op.add_column('equipments', sa.Column('book_value', sa.Float(), nullable=True, comment='账面净值（元）'), schema='equipment')
    op.add_column('equipments', sa.Column('label_no', sa.String(length=100), nullable=True, comment='标签号'), schema='equipment')
    op.add_column('equipments', sa.Column('scrap_status', sa.String(length=20), nullable=True, comment='报废状态'), schema='equipment')
    op.add_column('equipments', sa.Column('scrap_time', sa.Date(), nullable=True, comment='报废时间'), schema='equipment')
    op.alter_column('equipments', 'location_id',
               existing_type=sa.UUID(),
               nullable=True,
               comment='设备位置ID（可选）',
               existing_comment='设备位置',
               schema='equipment')
    op.drop_column('equipments', 'asset_value', schema='equipment')


def downgrade() -> None:
    op.add_column('equipments', sa.Column('asset_value', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True, comment='资产原值（元）'), schema='equipment')
    op.alter_column('equipments', 'location_id',
               existing_type=sa.UUID(),
               nullable=False,
               comment='设备位置',
               existing_comment='设备位置ID（可选）',
               schema='equipment')
    op.drop_column('equipments', 'scrap_time', schema='equipment')
    op.drop_column('equipments', 'scrap_status', schema='equipment')
    op.drop_column('equipments', 'label_no', schema='equipment')
    op.drop_column('equipments', 'book_value', schema='equipment')
    op.drop_column('equipments', 'current_cost', schema='equipment')
    op.drop_column('equipments', 'location_text', schema='equipment')
    op.drop_column('equipments', 'category_description', schema='equipment')
    op.drop_column('equipments', 'equipment_class', schema='equipment')
    op.drop_column('equipments', 'equipment_tag', schema='equipment')