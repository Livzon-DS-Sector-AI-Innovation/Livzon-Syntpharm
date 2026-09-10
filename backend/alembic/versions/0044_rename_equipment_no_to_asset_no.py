"""0044_rename_equipment_no_to_asset_no

Revision ID: 0044_rename_equipment_no_to_asset_no
Revises: fcb768b8df78
Create Date: 2026-07-15 18:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0044_rename_equipment_no_to_asset_no'
down_revision: Union[str, None] = '0043_fix_production_index_names'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("uq_equipments_equipment_no", table_name="equipments", schema="equipment")
    op.alter_column("equipments", "equipment_no", new_column_name="asset_no", comment="资产编号", schema="equipment")
    op.create_index("uq_equipments_asset_no", "equipments", ["asset_no"], unique=True, schema="equipment", postgresql_where=sa.text("is_deleted = false"))


def downgrade() -> None:
    op.drop_index("uq_equipments_asset_no", table_name="equipments", schema="equipment")
    op.alter_column("equipments", "asset_no", new_column_name="equipment_no", comment="设备编号", schema="equipment")
    op.create_index("uq_equipments_equipment_no", "equipments", ["equipment_no"], unique=True, schema="equipment", postgresql_where=sa.text("is_deleted = false"))