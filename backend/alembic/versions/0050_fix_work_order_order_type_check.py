"""fix_work_order_order_type_check

Add '巡检' to ck_work_orders_order_type check constraint.

Revision ID: 0050_fix_work_order_order_type_check
Revises: 0049_add_equipment_model_changes
Create Date: 2026-07-30 08:51:00.000000
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0050_fix_work_order_order_type_check'
down_revision: Union[str, None] = '0049_add_equipment_model_changes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_VALUES = "'故障维修', '计划维护', '校准', '异常处理', '日常维护'"
NEW_VALUES = "'故障维修', '计划维护', '巡检', '校准', '异常处理', '日常维护'"

CONSTRAINT = "ck_work_orders_order_type"
TABLE = "equipment.work_orders"


def upgrade() -> None:
    op.execute(f"ALTER TABLE {TABLE} DROP CONSTRAINT {CONSTRAINT}")
    op.execute(f"ALTER TABLE {TABLE} ADD CONSTRAINT {CONSTRAINT} CHECK (order_type IN ({NEW_VALUES}))")


def downgrade() -> None:
    op.execute(f"ALTER TABLE {TABLE} DROP CONSTRAINT {CONSTRAINT}")
    op.execute(f"ALTER TABLE {TABLE} ADD CONSTRAINT {CONSTRAINT} CHECK (order_type IN ({OLD_VALUES}))")
