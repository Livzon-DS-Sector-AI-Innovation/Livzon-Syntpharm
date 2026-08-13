"""0053_add_report_type_to_daily_risk_report

Revision ID: 0053_add_report_type_to_daily_risk_report
Revises: 0052_fix_special_op_personnel_unique_index
Create Date: 2026-08-13 11:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0053_add_report_type_to_daily_risk_report'
down_revision: Union[str, None] = '0052_fix_special_op_personnel_unique_index'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'daily_risk_reports',
        sa.Column(
            'report_type',
            sa.String(20),
            nullable=False,
            server_default='regular',
            comment="报备类型: regular(常规作业) / non_regular(非常规作业)",
        ),
        schema='safety',
    )


def downgrade() -> None:
    op.drop_column('daily_risk_reports', 'report_type', schema='safety')
