"""add equipment department scoping and safety enhancements

Revision ID: 0007_equipment_safety
Revises: 0006_quality_qms_sop_ai
Create Date: 2026-07-07 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0007_equipment_safety'
down_revision: Union[str, None] = '0006_quality_qms_sop_ai'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Recreate permission schema and tables
    op.execute('CREATE SCHEMA IF NOT EXISTS permission')
    
    op.create_table(
        'permissions',
        sa.Column('code', sa.String(length=100), nullable=False, comment='权限编码'),
        sa.Column('name', sa.String(length=200), nullable=False, comment='显示名称'),
        sa.Column('module', sa.String(length=50), nullable=False, comment='所属模块编码'),
        sa.Column('resource', sa.String(length=50), nullable=False, comment='资源类型'),
        sa.Column('action', sa.String(length=50), nullable=False, comment='操作类型'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_system', sa.Boolean(), server_default='false', nullable=False, comment='系统内置权限'),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.UniqueConstraint('code', name='uq_permission_permissions_code'),
        sa.PrimaryKeyConstraint('id'),
        schema='permission'
    )
    
    op.create_table(
        'roles',
        sa.Column('code', sa.String(length=50), nullable=False, comment='角色编码'),
        sa.Column('name', sa.String(length=100), nullable=False, comment='显示名称'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('data_scope', sa.String(length=30), server_default='department', nullable=False, comment='默认数据范围'),
        sa.Column('is_system', sa.Boolean(), server_default='false', nullable=False, comment='系统内置角色'),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.UniqueConstraint('code', name='uq_permission_roles_code'),
        sa.PrimaryKeyConstraint('id'),
        schema='permission'
    )
    
    op.create_table(
        'role_permissions',
        sa.Column('role_id', sa.Uuid(), nullable=False, comment='角色 ID'),
        sa.Column('permission_id', sa.Uuid(), nullable=False, comment='权限 ID'),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.UniqueConstraint('role_id', 'permission_id', name='uq_role_permissions_pair'),
        sa.PrimaryKeyConstraint('id'),
        schema='permission'
    )
    
    op.create_table(
        'user_roles',
        sa.Column('user_id', sa.Uuid(), nullable=False, comment='用户 ID'),
        sa.Column('role_id', sa.Uuid(), nullable=False, comment='角色 ID'),
        sa.Column('department_id', sa.Uuid(), nullable=True, comment='部门 ID'),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.UniqueConstraint('user_id', 'role_id', 'department_id', name='uq_user_roles_triple'),
        sa.PrimaryKeyConstraint('id'),
        schema='permission'
    )
    
    op.create_table(
        'role_data_scope_overrides',
        sa.Column('role_id', sa.Uuid(), nullable=False, comment='角色 ID'),
        sa.Column('module', sa.String(length=50), nullable=False, comment='模块编码'),
        sa.Column('data_scope', sa.String(length=30), nullable=False, comment='覆盖后的数据范围'),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.UniqueConstraint('role_id', 'module', name='uq_role_data_scope_module'),
        sa.PrimaryKeyConstraint('id'),
        schema='permission'
    )
    
    # Add equipment department scoping
    op.add_column('equipment_categories', sa.Column('department_id', sa.Uuid(), nullable=True), schema='equipment')
    op.add_column('locations', sa.Column('department_id', sa.Uuid(), nullable=True), schema='equipment')
    
    # Add safety enhancements
    op.add_column('hazard_reports', sa.Column('defect_substance', sa.Text(), nullable=True), schema='safety')
    op.add_column('hazard_reports', sa.Column('defect_substance_reasoning', sa.Text(), nullable=True), schema='safety')


def downgrade() -> None:
    # Remove safety enhancements
    op.drop_column('hazard_reports', 'defect_substance_reasoning', schema='safety')
    op.drop_column('hazard_reports', 'defect_substance', schema='safety')
    
    # Remove equipment department scoping
    op.drop_column('locations', 'department_id', schema='equipment')
    op.drop_column('equipment_categories', 'department_id', schema='equipment')
    
    # Drop permission tables
    op.drop_table('role_data_scope_overrides', schema='permission')
    op.drop_table('user_roles', schema='permission')
    op.drop_table('role_permissions', schema='permission')
    op.drop_table('roles', schema='permission')
    op.drop_table('permissions', schema='permission')
