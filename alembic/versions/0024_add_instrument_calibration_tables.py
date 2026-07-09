"""add instrument calibration tables

Revision ID: 0024_add_instrument_calibration_tables
Revises: 0024_add_quality_module_tables
Create Date: 2026-07-09 08:34:59.207350
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


# revision identifiers, used by Alembic.
revision: str = '0024_add_instrument_calibration_tables'
down_revision: Union[str, None] = '0023_add_quality_module_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create schema if not exists
    op.execute("CREATE SCHEMA IF NOT EXISTS quality")
    
    # 1. instrument_calibrations - 仪器设备台账
    op.create_table(
        'instrument_calibrations',
        sa.Column('instrument_no', sa.String(64), nullable=False, comment='仪器编号'),
        sa.Column('instrument_name', sa.String(255), nullable=False, comment='仪器名称'),
        sa.Column('model', sa.String(255), nullable=True, comment='型号'),
        sa.Column('serial_no', sa.String(128), nullable=True, comment='出厂编号'),
        sa.Column('manufacturer', sa.String(255), nullable=True, comment='制造商'),
        sa.Column('location', sa.String(255), nullable=True, comment='存放地点'),
        sa.Column('category', sa.String(32), nullable=True, comment='仪器分类'),
        sa.Column('manufacture_date', sa.DateTime(timezone=True), nullable=True, comment='出厂日期'),
        sa.Column('iq_status', sa.String(32), nullable=True, comment='IQ确认状态'),
        sa.Column('oq_status', sa.String(32), nullable=True, comment='OQ确认状态'),
        sa.Column('iq_confirm_date', sa.DateTime(timezone=True), nullable=True, comment='IQ确认日期'),
        sa.Column('oq_confirm_date', sa.DateTime(timezone=True), nullable=True, comment='OQ确认日期'),
        sa.Column('responsible_id', PG_UUID(as_uuid=True), nullable=True, comment='使用负责人ID'),
        sa.Column('responsible_name', sa.String(100), nullable=True, comment='使用负责人'),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False, comment='是否启用'),
        sa.Column('deactivate_date', sa.DateTime(timezone=True), nullable=True, comment='停用日期'),
        sa.Column('deactivate_reason', sa.Text(), nullable=True, comment='停用原因'),
        sa.Column('status', sa.String(32), server_default='draft', nullable=False, comment='状态'),
        sa.Column('remark', sa.Text(), nullable=True, comment='备注'),
        sa.Column('id', PG_UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', PG_UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', PG_UUID(as_uuid=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('instrument_no'),
        schema='quality'
    )
    op.create_index('idx_instrument_no', 'instrument_calibrations', ['instrument_no'], schema='quality')
    op.create_index('idx_instrument_name', 'instrument_calibrations', ['instrument_name'], schema='quality')
    op.create_index('idx_instrument_category', 'instrument_calibrations', ['category'], schema='quality')
    op.create_index('idx_instrument_status', 'instrument_calibrations', ['status'], schema='quality')
    op.create_index('idx_instrument_active', 'instrument_calibrations', ['is_active'], schema='quality')
    
    # 2. instrument_calibration_rules - 校准规则配置
    op.create_table(
        'instrument_calibration_rules',
        sa.Column('instrument_id', PG_UUID(as_uuid=True), nullable=False, comment='仪器ID'),
        sa.Column('rule_name', sa.String(255), nullable=False, comment='规则名称'),
        sa.Column('calibration_method', sa.String(32), nullable=False, comment='校准方式'),
        sa.Column('cycle_value', sa.Integer(), nullable=False, comment='校准周期值'),
        sa.Column('cycle_unit', sa.String(20), nullable=False, comment='校准周期单位'),
        sa.Column('last_calibration_date', sa.DateTime(timezone=True), nullable=True, comment='上次校准日期'),
        sa.Column('next_calibration_date', sa.DateTime(timezone=True), nullable=True, comment='下次校准日期'),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False, comment='是否启用'),
        sa.Column('remark', sa.Text(), nullable=True, comment='备注'),
        sa.Column('id', PG_UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', PG_UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', PG_UUID(as_uuid=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema='quality'
    )
    op.create_index('idx_rule_instrument', 'instrument_calibration_rules', ['instrument_id'], schema='quality')
    op.create_index('idx_rule_next_date', 'instrument_calibration_rules', ['next_calibration_date'], schema='quality')
    
    # 3. instrument_calibration_records - 校准记录
    op.create_table(
        'instrument_calibration_records',
        sa.Column('instrument_id', PG_UUID(as_uuid=True), nullable=False, comment='仪器ID'),
        sa.Column('calibration_no', sa.String(64), nullable=False, comment='校准记录编号'),
        sa.Column('calibration_date', sa.DateTime(timezone=True), nullable=False, comment='校准日期'),
        sa.Column('calibration_method', sa.String(32), nullable=False, comment='校准方式'),
        sa.Column('calibration_institution', sa.String(255), nullable=True, comment='校准机构'),
        sa.Column('certificate_no', sa.String(128), nullable=True, comment='证书编号'),
        sa.Column('calibration_result', sa.String(32), nullable=False, comment='校准结论'),
        sa.Column('result_description', sa.Text(), nullable=True, comment='结论说明'),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=True, comment='有效期起'),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True, comment='有效期至'),
        sa.Column('is_scheduled', sa.Boolean(), server_default='false', nullable=False, comment='是否计划校准'),
        sa.Column('scheduled_date', sa.DateTime(timezone=True), nullable=True, comment='计划校准日期'),
        sa.Column('status', sa.String(32), server_default='draft', nullable=False, comment='状态'),
        sa.Column('remark', sa.Text(), nullable=True, comment='备注'),
        sa.Column('id', PG_UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', PG_UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', PG_UUID(as_uuid=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema='quality'
    )
    op.create_index('idx_calibration_instrument', 'instrument_calibration_records', ['instrument_id'], schema='quality')
    op.create_index('idx_calibration_no', 'instrument_calibration_records', ['calibration_no'], schema='quality')
    op.create_index('idx_calibration_date', 'instrument_calibration_records', ['calibration_date'], schema='quality')
    op.create_index('idx_calibration_result', 'instrument_calibration_records', ['calibration_result'], schema='quality')
    op.create_index('idx_calibration_status', 'instrument_calibration_records', ['status'], schema='quality')
    
    # 4. instrument_calibration_approvals - 审批记录
    op.create_table(
        'instrument_calibration_approvals',
        sa.Column('related_type', sa.String(32), nullable=False, comment='关联类型'),
        sa.Column('related_id', PG_UUID(as_uuid=True), nullable=False, comment='关联ID'),
        sa.Column('approval_type', sa.String(32), nullable=False, comment='审批类型'),
        sa.Column('sequence', sa.Integer(), server_default='1', nullable=False, comment='审批顺序'),
        sa.Column('status', sa.String(32), server_default='pending', nullable=False, comment='审批状态'),
        sa.Column('approval_date', sa.DateTime(timezone=True), nullable=True, comment='审批日期'),
        sa.Column('comments', sa.Text(), nullable=True, comment='审批意见'),
        sa.Column('approver_id', PG_UUID(as_uuid=True), nullable=True, comment='审批人ID'),
        sa.Column('approver_name', sa.String(100), nullable=True, comment='审批人'),
        sa.Column('id', PG_UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', PG_UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', PG_UUID(as_uuid=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema='quality'
    )
    op.create_index('idx_approval_related', 'instrument_calibration_approvals', ['related_type', 'related_id'], schema='quality')
    op.create_index('idx_approval_status', 'instrument_calibration_approvals', ['status'], schema='quality')
    
    # 5. calibration_reminder_config - 校准到期提醒配置
    op.create_table(
        'calibration_reminder_config',
        sa.Column('name', sa.String(100), nullable=False, comment='配置名称'),
        sa.Column('feishu_app_id', sa.String(100), nullable=True, comment='飞书应用AppID'),
        sa.Column('feishu_app_secret', sa.String(255), nullable=True, comment='飞书应用AppSecret'),
        sa.Column('chat_id', sa.String(255), nullable=True, comment='飞书群ID或用户ID'),
        sa.Column('receive_id_type', sa.String(20), server_default='chat_id', nullable=False, comment='接收类型'),
        sa.Column('remind_30_days', sa.Boolean(), server_default='true', nullable=False, comment='是否在30天前提醒'),
        sa.Column('remind_14_days', sa.Boolean(), server_default='true', nullable=False, comment='是否在14天前提醒'),
        sa.Column('remind_7_days', sa.Boolean(), server_default='true', nullable=False, comment='是否在7天前提醒'),
        sa.Column('remind_overdue', sa.Boolean(), server_default='true', nullable=False, comment='是否在超期后提醒'),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False, comment='是否启用'),
        sa.Column('last_remind_30_days', sa.DateTime(timezone=True), nullable=True, comment='上次30天提醒时间'),
        sa.Column('last_remind_14_days', sa.DateTime(timezone=True), nullable=True, comment='上次14天提醒时间'),
        sa.Column('last_remind_7_days', sa.DateTime(timezone=True), nullable=True, comment='上次7天提醒时间'),
        sa.Column('last_remind_overdue', sa.DateTime(timezone=True), nullable=True, comment='上次超期提醒时间'),
        sa.Column('id', PG_UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', PG_UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', PG_UUID(as_uuid=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema='quality'
    )
    op.create_index('idx_reminder_config_is_active', 'calibration_reminder_config', ['is_active'], schema='quality')


def downgrade() -> None:
    op.drop_table('calibration_reminder_config', schema='quality')
    op.drop_table('instrument_calibration_approvals', schema='quality')
    op.drop_table('instrument_calibration_records', schema='quality')
    op.drop_table('instrument_calibration_rules', schema='quality')
    op.drop_table('instrument_calibrations', schema='quality')
