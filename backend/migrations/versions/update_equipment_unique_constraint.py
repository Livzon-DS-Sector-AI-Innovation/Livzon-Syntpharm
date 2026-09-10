"""update equipment unique constraint to include department and location

Revision ID: update_equip_uq_20260909
Revises: 
Create Date: 2026-09-09

"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    # 删除旧的唯一约束
    op.drop_constraint('uq_equipments_asset_no', 'equipments', schema='equipment', type_='unique')
    
    # 创建新的复合唯一约束
    op.create_unique_constraint(
        'uq_equipments_asset_dept_loc',
        'equipments',
        ['asset_no', 'department_id', 'location_text', 'is_deleted'],
        schema='equipment'
    )


def downgrade():
    # 删除新的复合唯一约束
    op.drop_constraint('uq_equipments_asset_dept_loc', 'equipments', schema='equipment', type_='unique')
    
    # 恢复旧的唯一约束
    op.create_unique_constraint(
        'uq_equipments_asset_no',
        'equipments',
        ['asset_no', 'is_deleted'],
        schema='equipment'
    )
