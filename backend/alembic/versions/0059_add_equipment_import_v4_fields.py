"""add equipment import v4 fields: is_fixed_asset, unique equipment_tag index, audit logs

Revision ID: 0059
Revises: 0058
Create Date: 2026-09-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '0059'
down_revision = '0058_add_sync_logs_table'
branch_labels = None
depends_on = None


def upgrade():
    # 1. 添加 is_fixed_asset 字段
    op.add_column(
        'equipments',
        sa.Column('is_fixed_asset', sa.Boolean(), 
                  server_default='true', 
                  nullable=False,
                  comment='是否为固定资产'),
        schema='equipment'
    )
    
    # 2. 为现有 asset_no 为 NULL 的记录设置 is_fixed_asset = false
    op.execute(
        "UPDATE equipment.equipments SET is_fixed_asset = false WHERE asset_no IS NULL AND is_deleted = false"
    )
    
    # 3. 为 equipment_tag 添加部分唯一索引
    op.create_index(
        'uq_equipments_equipment_tag',
        'equipments',
        ['equipment_tag'],
        unique=True,
        schema='equipment',
        postgresql_where=sa.text("equipment_tag IS NOT NULL AND is_deleted = false")
    )
    
    # 4. 创建导入审计日志表
    op.create_table(
        'import_audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('batch_id', sa.String(50), nullable=False, comment='导入批次ID'),
        sa.Column('operation_type', sa.String(20), nullable=False, comment='操作类型'),
        sa.Column('match_strategy', sa.String(20), nullable=True, comment='匹配策略'),
        sa.Column('asset_no', sa.String(50), nullable=True, comment='资产编号'),
        sa.Column('equipment_tag', sa.String(100), nullable=True, comment='设备位号'),
        sa.Column('department_id', postgresql.UUID(as_uuid=True), nullable=True, comment='部门ID'),
        sa.Column('location_text', sa.String(200), nullable=True, comment='位置文本'),
        sa.Column('changes', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='变更详情'),
        sa.Column('warnings', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='警告信息'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='错误信息'),
        sa.Column('row_index', sa.Integer(), nullable=True, comment='Excel行号'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True, comment='操作用户ID'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), comment='创建时间'),
        schema='equipment'
    )
    
    # 5. 为 batch_id 和 created_at 添加索引
    op.create_index('idx_import_audit_batch_id', 'import_audit_logs', ['batch_id'], schema='equipment')
    op.create_index('idx_import_audit_created_at', 'import_audit_logs', ['created_at'], schema='equipment')


def downgrade():
    op.drop_index('idx_import_audit_created_at', schema='equipment', table_name='import_audit_logs')
    op.drop_index('idx_import_audit_batch_id', schema='equipment', table_name='import_audit_logs')
    op.drop_table('import_audit_logs', schema='equipment')
    op.drop_index('uq_equipments_equipment_tag', schema='equipment', table_name='equipments')
    op.drop_column('equipments', 'is_fixed_asset', schema='equipment')
