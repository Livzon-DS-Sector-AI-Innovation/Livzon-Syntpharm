"""drug node skipped flag

Revision ID: 0116_registration_drug_node_skipped
Revises: 0100_safety_equipment_facility_hazards
Create Date: 2026-11-10

审评节点支持「跳过」状态：核查豁免、一次通过无发补等场景下，
节点不发生，skipped=true 时不计入进度分母、不参与工作日推算。
与 actual_date 互斥（service 层校验）。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0116_registration_drug_node_skipped"
down_revision: str = "0100_safety_equipment_facility_hazards"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "drug_nodes"
_SCHEMA = "registration"


def upgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column(
            "skipped",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="是否跳过（节点不发生，如核查豁免/无发补）",
        ),
        schema=_SCHEMA,
    )


def downgrade() -> None:
    op.drop_column(_TABLE, "skipped", schema=_SCHEMA)
