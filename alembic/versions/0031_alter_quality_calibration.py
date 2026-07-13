"""alter_quality_calibration

Revision ID: 0031_alter_quality_calibration
Revises: 0030_alter_hr_json_columns
Create Date: 2026-07-12 11:33:33.282156
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0031_alter_quality_calibration'
down_revision: Union[str, None] = '0030_alter_hr_json_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute('CREATE SCHEMA IF NOT EXISTS quality')
    op.alter_column('calibration_reminder_config', 'receive_id_type',
               existing_type=sa.VARCHAR(length=20),
               comment='接收类型: chat_id/user_id',
               existing_comment='接收类型',
               existing_nullable=False,
               existing_server_default=sa.text("'chat_id'::character varying"),
               schema='quality')
    op.create_foreign_key(None, 'calibration_reminder_config', 'users', ['updated_by'], ['id'], source_schema='quality', referent_schema='identity')
    op.create_foreign_key(None, 'calibration_reminder_config', 'users', ['created_by'], ['id'], source_schema='quality', referent_schema='identity')
    op.create_foreign_key(None, 'instrument_calibration_approvals', 'users', ['created_by'], ['id'], source_schema='quality', referent_schema='identity')
    op.create_foreign_key(None, 'instrument_calibration_approvals', 'users', ['updated_by'], ['id'], source_schema='quality', referent_schema='identity')
    op.add_column('instrument_calibration_records', sa.Column('rule_id', sa.UUID(), nullable=True, comment='关联校准规则ID'), schema='quality')
    op.add_column('instrument_calibration_records', sa.Column('calibration_end_date', sa.DateTime(timezone=True), nullable=True, comment='校准完成日期'), schema='quality')
    op.add_column('instrument_calibration_records', sa.Column('calibration_agency', sa.String(length=255), nullable=True, comment='校准机构'), schema='quality')
    op.add_column('instrument_calibration_records', sa.Column('calibrator_id', sa.UUID(), nullable=True, comment='校准人员ID'), schema='quality')
    op.add_column('instrument_calibration_records', sa.Column('calibrator_name', sa.String(length=100), nullable=True, comment='校准人员'), schema='quality')
    op.add_column('instrument_calibration_records', sa.Column('certificate_url', sa.String(length=512), nullable=True, comment='校准证书附件URL'), schema='quality')
    op.add_column('instrument_calibration_records', sa.Column('result_reason', sa.Text(), nullable=True, comment='结论说明'), schema='quality')
    op.alter_column('instrument_calibration_records', 'instrument_id',
               existing_type=sa.UUID(),
               comment='关联仪器ID',
               existing_comment='仪器ID',
               existing_nullable=False,
               schema='quality')
    op.alter_column('instrument_calibration_records', 'calibration_no',
               existing_type=sa.VARCHAR(length=64),
               comment='校准单据编号',
               existing_comment='校准记录编号',
               existing_nullable=False,
               schema='quality')
    op.alter_column('instrument_calibration_records', 'certificate_no',
               existing_type=sa.VARCHAR(length=128),
               comment='校准证书编号',
               existing_comment='证书编号',
               existing_nullable=True,
               schema='quality')
    op.drop_index(op.f('idx_calibration_no'), table_name='instrument_calibration_records', schema='quality')
    op.create_index('idx_calibration_no', 'instrument_calibration_records', ['calibration_no'], unique=True, schema='quality')
    op.create_unique_constraint(None, 'instrument_calibration_records', ['calibration_no'], schema='quality')
    op.create_foreign_key(None, 'instrument_calibration_records', 'users', ['created_by'], ['id'], source_schema='quality', referent_schema='identity')
    op.create_foreign_key(None, 'instrument_calibration_records', 'users', ['updated_by'], ['id'], source_schema='quality', referent_schema='identity')
    op.create_foreign_key(None, 'instrument_calibration_records', 'instrument_calibrations', ['instrument_id'], ['id'], source_schema='quality', referent_schema='quality')
    op.drop_column('instrument_calibration_records', 'calibration_institution', schema='quality')
    op.drop_column('instrument_calibration_records', 'result_description', schema='quality')
    op.add_column('instrument_calibration_rules', sa.Column('calibration_cycle', sa.Integer(), nullable=True, comment='校准周期'), schema='quality')
    op.add_column('instrument_calibration_rules', sa.Column('calibration_unit', sa.String(length=32), nullable=True, comment='周期单位'), schema='quality')
    op.add_column('instrument_calibration_rules', sa.Column('calibration_agency', sa.String(length=255), nullable=True, comment='校准机构名称'), schema='quality')
    op.add_column('instrument_calibration_rules', sa.Column('agency_contact', sa.String(length=255), nullable=True, comment='机构联系方式'), schema='quality')
    op.add_column('instrument_calibration_rules', sa.Column('internal_calibrator_id', sa.UUID(), nullable=True, comment='内校人员ID'), schema='quality')
    op.add_column('instrument_calibration_rules', sa.Column('internal_calibrator_name', sa.String(length=100), nullable=True, comment='内校人员'), schema='quality')
    op.add_column('instrument_calibration_rules', sa.Column('warning_days', sa.Integer(), server_default='7', nullable=True, comment='提前预警天数'), schema='quality')
    op.alter_column('instrument_calibration_rules', 'instrument_id',
               existing_type=sa.UUID(),
               comment='关联仪器ID',
               existing_comment='仪器ID',
               existing_nullable=False,
               schema='quality')
    op.alter_column('instrument_calibration_rules', 'last_calibration_date',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment='最近校准日期',
               existing_comment='上次校准日期',
               existing_nullable=True,
               schema='quality')
    op.create_foreign_key(None, 'instrument_calibration_rules', 'users', ['created_by'], ['id'], source_schema='quality', referent_schema='identity')
    op.create_foreign_key(None, 'instrument_calibration_rules', 'users', ['updated_by'], ['id'], source_schema='quality', referent_schema='identity')
    op.create_foreign_key(None, 'instrument_calibration_rules', 'instrument_calibrations', ['instrument_id'], ['id'], source_schema='quality', referent_schema='quality')
    op.drop_column('instrument_calibration_rules', 'remark', schema='quality')
    op.drop_column('instrument_calibration_rules', 'rule_name', schema='quality')
    op.drop_column('instrument_calibration_rules', 'cycle_unit', schema='quality')
    op.drop_column('instrument_calibration_rules', 'cycle_value', schema='quality')
    op.drop_index(op.f('idx_instrument_no'), table_name='instrument_calibrations', schema='quality')
    op.create_index('idx_instrument_no', 'instrument_calibrations', ['instrument_no'], unique=True, schema='quality')
    op.create_foreign_key(None, 'instrument_calibrations', 'users', ['created_by'], ['id'], source_schema='quality', referent_schema='identity')
    op.create_foreign_key(None, 'instrument_calibrations', 'users', ['updated_by'], ['id'], source_schema='quality', referent_schema='identity')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'instrument_calibrations', schema='quality', type_='foreignkey')
    op.drop_constraint(None, 'instrument_calibrations', schema='quality', type_='foreignkey')
    op.drop_index('idx_instrument_no', table_name='instrument_calibrations', schema='quality')
    op.create_index(op.f('idx_instrument_no'), 'instrument_calibrations', ['instrument_no'], unique=False, schema='quality')
    op.add_column('instrument_calibration_rules', sa.Column('cycle_value', sa.INTEGER(), autoincrement=False, nullable=False, comment='校准周期值'), schema='quality')
    op.add_column('instrument_calibration_rules', sa.Column('cycle_unit', sa.VARCHAR(length=20), autoincrement=False, nullable=False, comment='校准周期单位'), schema='quality')
    op.add_column('instrument_calibration_rules', sa.Column('rule_name', sa.VARCHAR(length=255), autoincrement=False, nullable=False, comment='规则名称'), schema='quality')
    op.add_column('instrument_calibration_rules', sa.Column('remark', sa.TEXT(), autoincrement=False, nullable=True, comment='备注'), schema='quality')
    op.drop_constraint(None, 'instrument_calibration_rules', schema='quality', type_='foreignkey')
    op.drop_constraint(None, 'instrument_calibration_rules', schema='quality', type_='foreignkey')
    op.drop_constraint(None, 'instrument_calibration_rules', schema='quality', type_='foreignkey')
    op.alter_column('instrument_calibration_rules', 'last_calibration_date',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               comment='上次校准日期',
               existing_comment='最近校准日期',
               existing_nullable=True,
               schema='quality')
    op.alter_column('instrument_calibration_rules', 'instrument_id',
               existing_type=sa.UUID(),
               comment='仪器ID',
               existing_comment='关联仪器ID',
               existing_nullable=False,
               schema='quality')
    op.drop_column('instrument_calibration_rules', 'warning_days', schema='quality')
    op.drop_column('instrument_calibration_rules', 'internal_calibrator_name', schema='quality')
    op.drop_column('instrument_calibration_rules', 'internal_calibrator_id', schema='quality')
    op.drop_column('instrument_calibration_rules', 'agency_contact', schema='quality')
    op.drop_column('instrument_calibration_rules', 'calibration_agency', schema='quality')
    op.drop_column('instrument_calibration_rules', 'calibration_unit', schema='quality')
    op.drop_column('instrument_calibration_rules', 'calibration_cycle', schema='quality')
    op.add_column('instrument_calibration_records', sa.Column('result_description', sa.TEXT(), autoincrement=False, nullable=True, comment='结论说明'), schema='quality')
    op.add_column('instrument_calibration_records', sa.Column('calibration_institution', sa.VARCHAR(length=255), autoincrement=False, nullable=True, comment='校准机构'), schema='quality')
    op.drop_constraint(None, 'instrument_calibration_records', schema='quality', type_='foreignkey')
    op.drop_constraint(None, 'instrument_calibration_records', schema='quality', type_='foreignkey')
    op.drop_constraint(None, 'instrument_calibration_records', schema='quality', type_='foreignkey')
    op.drop_constraint(None, 'instrument_calibration_records', schema='quality', type_='unique')
    op.drop_index('idx_calibration_no', table_name='instrument_calibration_records', schema='quality')
    op.create_index(op.f('idx_calibration_no'), 'instrument_calibration_records', ['calibration_no'], unique=False, schema='quality')
    op.alter_column('instrument_calibration_records', 'certificate_no',
               existing_type=sa.VARCHAR(length=128),
               comment='证书编号',
               existing_comment='校准证书编号',
               existing_nullable=True,
               schema='quality')
    op.alter_column('instrument_calibration_records', 'calibration_no',
               existing_type=sa.VARCHAR(length=64),
               comment='校准记录编号',
               existing_comment='校准单据编号',
               existing_nullable=False,
               schema='quality')
    op.alter_column('instrument_calibration_records', 'instrument_id',
               existing_type=sa.UUID(),
               comment='仪器ID',
               existing_comment='关联仪器ID',
               existing_nullable=False,
               schema='quality')
    op.drop_column('instrument_calibration_records', 'result_reason', schema='quality')
    op.drop_column('instrument_calibration_records', 'certificate_url', schema='quality')
    op.drop_column('instrument_calibration_records', 'calibrator_name', schema='quality')
    op.drop_column('instrument_calibration_records', 'calibrator_id', schema='quality')
    op.drop_column('instrument_calibration_records', 'calibration_agency', schema='quality')
    op.drop_column('instrument_calibration_records', 'calibration_end_date', schema='quality')
    op.drop_column('instrument_calibration_records', 'rule_id', schema='quality')
    op.drop_constraint(None, 'instrument_calibration_approvals', schema='quality', type_='foreignkey')
    op.drop_constraint(None, 'instrument_calibration_approvals', schema='quality', type_='foreignkey')
    op.drop_constraint(None, 'calibration_reminder_config', schema='quality', type_='foreignkey')
    op.drop_constraint(None, 'calibration_reminder_config', schema='quality', type_='foreignkey')
    op.alter_column('calibration_reminder_config', 'receive_id_type',
               existing_type=sa.VARCHAR(length=20),
               comment='接收类型',
               existing_comment='接收类型: chat_id/user_id',
               existing_nullable=False,
               existing_server_default=sa.text("'chat_id'::character varying"),
               schema='quality')

