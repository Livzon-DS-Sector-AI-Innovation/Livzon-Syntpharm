"""Add EnergyDailyData table

Revision ID: 78dece9ae0a3
Revises: 49684887bf7e
Create Date: 2026-07-22 08:02:02.952294
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '78dece9ae0a3'
down_revision: Union[str, None] = '49684887bf7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE SCHEMA IF NOT EXISTS energy')
    op.create_table('energy_daily_data',
    sa.Column('date', sa.Date(), nullable=False, comment='数据日期'),
    sa.Column('energy_type', sa.String(length=20), nullable=False, comment='能源类型: water/electricity/steam/natural_gas'),
    sa.Column('category', sa.String(length=50), nullable=False, comment="类别（如'水（吨）'）"),
    sa.Column('total_value', sa.Numeric(precision=18, scale=4), nullable=False, comment='总数（实际用量）'),
    sa.Column('alert_threshold', sa.Numeric(precision=18, scale=4), nullable=False, comment='警戒线（预警阈值）'),
    sa.Column('cost', sa.Numeric(precision=18, scale=4), nullable=True, comment='费用'),
    sa.Column('municipal_meter', sa.Numeric(precision=18, scale=4), nullable=True, comment='市政总表'),
    sa.Column('error_value', sa.Numeric(precision=18, scale=4), nullable=True, comment='误差'),
    sa.Column('source_table', sa.String(length=50), nullable=False, comment='来源表（水表/电表等）'),
    sa.Column('is_alert', sa.Boolean(), nullable=False, comment='是否触发预警'),
    sa.Column('alert_record_id', sa.Uuid(), nullable=True, comment='关联预警记录ID'),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['identity.users.id'], ),
    sa.ForeignKeyConstraint(['updated_by'], ['identity.users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('date', 'energy_type', 'category', name='uq_energy_daily_data_date_type_category'),
    schema='energy'
    )


def downgrade() -> None:
    op.drop_table('energy_daily_data', schema='energy')
