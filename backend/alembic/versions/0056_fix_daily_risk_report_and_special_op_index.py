"""0056_fix_daily_risk_report_and_special_op_index

Revision ID: 0056_fix_daily_risk_report_and_special_op_index
Revises: 0055_add_sync_operation_log
Create Date: 2026-08-25 17:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = '0056_fix_daily_risk_report_and_special_op_index'
down_revision: Union[str, None] = '0055_add_sync_operation_log'
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # 1. Add report_type column to safety.daily_risk_reports (if not exists)
    columns = [col['name'] for col in inspector.get_columns('daily_risk_reports', schema='safety')]
    if 'report_type' not in columns:
        op.add_column(
            'daily_risk_reports',
            sa.Column(
                'report_type',
                sa.String(length=20),
                nullable=False,
                server_default='regular',
                comment='报备类型: regular(常规作业) / non_regular(非常规作业)',
            ),
            schema='safety',
        )

    # 2. Remove old single-column unique index (if exists)
    indexes = inspector.get_indexes('special_operation_personnel', schema='safety')
    index_names = [idx['name'] for idx in indexes]
    if 'uq_special_op_personnel_no' in index_names:
        op.drop_index(
            'uq_special_op_personnel_no',
            table_name='special_operation_personnel',
            schema='safety',
        )

    # 3. Add new composite unique index (if not exists)
    if 'uq_special_op_personnel_duplicate' not in index_names:
        op.create_index(
            'uq_special_op_personnel_duplicate',
            'special_operation_personnel',
            ['personnel_no', 'department', 'certificate_type', 'certificate_number', 'expiry_date'],
            unique=True,
            schema='safety',
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    indexes = inspector.get_indexes('special_operation_personnel', schema='safety')
    index_names = [idx['name'] for idx in indexes]
    
    # 1. Drop composite unique index
    if 'uq_special_op_personnel_duplicate' in index_names:
        op.drop_index(
            'uq_special_op_personnel_duplicate',
            table_name='special_operation_personnel',
            schema='safety',
        )

    # 2. Restore old single-column unique index
    if 'uq_special_op_personnel_no' not in index_names:
        op.create_index(
            'uq_special_op_personnel_no',
            'special_operation_personnel',
            ['personnel_no'],
            unique=True,
            schema='safety',
        )

    # 3. Remove report_type column
    columns = [col['name'] for col in inspector.get_columns('daily_risk_reports', schema='safety')]
    if 'report_type' in columns:
        op.drop_column('daily_risk_reports', 'report_type', schema='safety')
