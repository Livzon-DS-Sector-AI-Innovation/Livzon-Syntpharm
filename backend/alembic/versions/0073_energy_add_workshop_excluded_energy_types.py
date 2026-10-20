"""energy: add workshop excluded_energy_types and mark rollup workshops

Revision ID: 0073_energy_add_workshop_excluded_energy_types
Revises: 0072_add_equipment_quantity
Create Date: 2026-10-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0073_energy_add_workshop_excluded_energy_types"
down_revision: Union[str, None] = "0072_add_equipment_quantity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 合计行车间标记：其电耗与其构成项重复上报，全厂汇总时必须剔除
# 动力运行 = 201盐水/103冷水/4号楼冷水/500T冷水/500T盐水/空压氮气 用电之和
# RTO 用电已含在「环保中心（含RTO）」内
# 名称在车间主数据统一（WORKSHOP_ALIASES）后固定，见 docs/energy-workshop-unification.md


def _mark_rollup_workshops() -> None:
    op.execute(
        """
        UPDATE energy.energy_workshops
           SET excluded_energy_types = ARRAY['electricity']::character varying[]
         WHERE name = ANY(ARRAY['动力运行', 'RTO']::character varying[])
        """
    )


def upgrade() -> None:
    op.add_column(
        "energy_workshops",
        sa.Column(
            "excluded_energy_types",
            sa.ARRAY(sa.String(length=20)),
            server_default=sa.text("'{}'::character varying[]"),
            nullable=False,
            comment="不计入全厂汇总的能源类型（合计行与其构成项重复上报时标记）",
        ),
        schema="energy",
    )
    _mark_rollup_workshops()


def downgrade() -> None:
    op.drop_column("energy_workshops", "excluded_energy_types", schema="energy")
