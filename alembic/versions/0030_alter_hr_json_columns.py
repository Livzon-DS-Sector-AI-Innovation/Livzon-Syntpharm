"""alter_hr_json_columns

Revision ID: 0030_alter_hr_json_columns
Revises: 0029_add_agent_core_tables
Create Date: 2026-07-12 11:33:33.282156
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0030_alter_hr_json_columns'
down_revision: Union[str, None] = '0029_add_agent_core_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute('CREATE SCHEMA IF NOT EXISTS hr')
    op.alter_column('candidates', 'resume_attachments',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               type_=postgresql.JSONB(astext_type=sa.Text()),
               existing_comment='简历附件元数据',
               existing_nullable=True,
               schema='hr')
    op.alter_column('departure_records', 'offboarding_reason',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               type_=postgresql.JSONB(astext_type=sa.Text()),
               existing_comment='离职原因（多选）',
               existing_nullable=True,
               schema='hr')
    op.alter_column('departure_records', 'offboarding_reason_2',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               type_=postgresql.JSONB(astext_type=sa.Text()),
               existing_comment='离职原因2（多选）',
               existing_nullable=True,
               schema='hr')
    op.alter_column('departure_records', 'offboarding_remarks',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               type_=postgresql.JSONB(astext_type=sa.Text()),
               existing_comment='离职备注（多选）',
               existing_nullable=True,
               schema='hr')
    op.alter_column('employees', 'qualifications',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               type_=postgresql.JSONB(astext_type=sa.Text()),
               existing_comment='职称／职业资格（多选）',
               existing_nullable=True,
               schema='hr')
    op.alter_column('employees', 'remarks',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               type_=postgresql.JSONB(astext_type=sa.Text()),
               existing_comment='备注（多选）',
               existing_nullable=True,
               schema='hr')
    op.alter_column('onboarding_records', 'remarks',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               type_=postgresql.JSONB(astext_type=sa.Text()),
               existing_comment='备注（多选）',
               existing_nullable=True,
               schema='hr')
    op.alter_column('prejob_training_plan_templates', 'items',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               type_=postgresql.JSONB(astext_type=sa.Text()),
               existing_comment='培训计划条目列表 [{seq, content, deadline, trainer}]',
               existing_nullable=False,
               existing_server_default=sa.text("'[]'::json"),
               schema='hr')
    op.alter_column('training_sessions', 'trainee_departments',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               type_=postgresql.JSONB(astext_type=sa.Text()),
               existing_comment='受训部门列表',
               existing_nullable=True,
               schema='hr')
    op.alter_column('training_sessions', 'employee_names',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               type_=postgresql.JSONB(astext_type=sa.Text()),
               existing_comment='应出席受训人员姓名列表',
               existing_nullable=True,
               schema='hr')
    op.alter_column('training_sessions', 'employee_numbers',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               type_=postgresql.JSONB(astext_type=sa.Text()),
               existing_comment='应出席受训人员工号列表',
               existing_nullable=True,
               schema='hr')
    op.alter_column('training_sessions', 'select_tasks',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               type_=postgresql.JSONB(astext_type=sa.Text()),
               existing_comment='多部门选择任务列表[{department, token, status, employee_names, employee_numbers}]',
               existing_nullable=True,
               schema='hr')
    op.alter_column('training_teams', 'employee_names',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               type_=postgresql.JSONB(astext_type=sa.Text()),
               existing_comment='受训人员姓名列表',
               existing_nullable=True,
               schema='hr')
    op.alter_column('training_teams', 'employee_numbers',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               type_=postgresql.JSONB(astext_type=sa.Text()),
               existing_comment='受训人员工号列表',
               existing_nullable=True,
               schema='hr')


def downgrade() -> None:
    op.alter_column('training_teams', 'employee_numbers',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               type_=postgresql.JSON(astext_type=sa.Text()),
               existing_comment='受训人员工号列表',
               existing_nullable=True,
               schema='hr')
    op.alter_column('training_teams', 'employee_names',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               type_=postgresql.JSON(astext_type=sa.Text()),
               existing_comment='受训人员姓名列表',
               existing_nullable=True,
               schema='hr')
    op.alter_column('training_sessions', 'select_tasks',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               type_=postgresql.JSON(astext_type=sa.Text()),
               existing_comment='多部门选择任务列表[{department, token, status, employee_names, employee_numbers}]',
               existing_nullable=True,
               schema='hr')
    op.alter_column('training_sessions', 'employee_numbers',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               type_=postgresql.JSON(astext_type=sa.Text()),
               existing_comment='应出席受训人员工号列表',
               existing_nullable=True,
               schema='hr')
    op.alter_column('training_sessions', 'employee_names',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               type_=postgresql.JSON(astext_type=sa.Text()),
               existing_comment='应出席受训人员姓名列表',
               existing_nullable=True,
               schema='hr')
    op.alter_column('training_sessions', 'trainee_departments',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               type_=postgresql.JSON(astext_type=sa.Text()),
               existing_comment='受训部门列表',
               existing_nullable=True,
               schema='hr')
    op.alter_column('prejob_training_plan_templates', 'items',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               type_=postgresql.JSON(astext_type=sa.Text()),
               existing_comment='培训计划条目列表 [{seq, content, deadline, trainer}]',
               existing_nullable=False,
               existing_server_default=sa.text("'[]'::json"),
               schema='hr')
    op.alter_column('onboarding_records', 'remarks',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               type_=postgresql.JSON(astext_type=sa.Text()),
               existing_comment='备注（多选）',
               existing_nullable=True,
               schema='hr')
    op.alter_column('employees', 'remarks',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               type_=postgresql.JSON(astext_type=sa.Text()),
               existing_comment='备注（多选）',
               existing_nullable=True,
               schema='hr')
    op.alter_column('employees', 'qualifications',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               type_=postgresql.JSON(astext_type=sa.Text()),
               existing_comment='职称／职业资格（多选）',
               existing_nullable=True,
               schema='hr')
    op.alter_column('departure_records', 'offboarding_remarks',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               type_=postgresql.JSON(astext_type=sa.Text()),
               existing_comment='离职备注（多选）',
               existing_nullable=True,
               schema='hr')
    op.alter_column('departure_records', 'offboarding_reason_2',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               type_=postgresql.JSON(astext_type=sa.Text()),
               existing_comment='离职原因2（多选）',
               existing_nullable=True,
               schema='hr')
    op.alter_column('departure_records', 'offboarding_reason',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               type_=postgresql.JSON(astext_type=sa.Text()),
               existing_comment='离职原因（多选）',
               existing_nullable=True,
               schema='hr')
    op.alter_column('candidates', 'resume_attachments',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               type_=postgresql.JSON(astext_type=sa.Text()),
               existing_comment='简历附件元数据',
               existing_nullable=True,
               schema='hr')

