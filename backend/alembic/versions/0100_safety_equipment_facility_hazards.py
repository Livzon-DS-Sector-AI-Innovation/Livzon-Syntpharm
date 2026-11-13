"""safety equipment facility hazard ledger

Revision ID: 0100_safety_equipment_facility_hazards
Revises: 0099_safety_work_activity_hazards
Create Date: 2026-11-09

新增《设备设施危险源台账》空表：
L/S 为单选值，R 由安全风险矩阵查表得出并由服务端写入；措施以稳定 key 数组存储。
只动 safety schema，单模块迁移。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0100_safety_equipment_facility_hazards"
down_revision: str = "0099_safety_work_activity_hazards"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "equipment_facility_hazards"


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("equipment_facility_tag", sa.String(255), nullable=False, comment="设备设施/位号"),
        sa.Column("inspection_item", sa.Text(), nullable=False, comment="检查项目"),
        sa.Column("inspection_standard", sa.Text(), nullable=False, comment="检查标准"),
        sa.Column("nonconformity_consequence", sa.Text(), nullable=False, comment="不符合标准情况及后果"),
        sa.Column("likelihood_l", sa.Integer(), nullable=False, comment="可能性 L（1–5）"),
        sa.Column("severity_s", sa.String(1), nullable=False, comment="严重性 S（A–E）"),
        sa.Column(
            "risk_evaluation_r",
            sa.Integer(),
            nullable=False,
            comment="危险评价 R（安全风险矩阵查表，服务端计算，只读）",
        ),
        sa.Column("current_control_measures", sa.JSON(), nullable=False, comment="现有管控措施（有序的稳定 key 数组）"),
        sa.Column(
            "improvement_measures",
            sa.JSON(),
            nullable=False,
            comment="建议改进（新增）措施（有序的稳定 key 数组）",
        ),
        sa.Column("residual_risk", sa.String(20), nullable=False, comment="残余风险 key"),
        sa.Column("residual_risk_label", sa.String(50), nullable=False, comment="残余风险中文标签"),
        sa.Column("control_level", sa.String(100), nullable=False, comment="管控层级（部门单选）"),
        sa.Column("execution_level", sa.String(20), nullable=False, comment="执行层级 key（车间/班组长）"),
        sa.Column("remarks", sa.Text(), nullable=False, comment="备注"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("identity.users.id"), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), sa.ForeignKey("identity.users.id"), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        schema="safety",
    )
    op.create_index(
        "ix_equipment_facility_hazards_control_level",
        _TABLE,
        ["control_level"],
        schema="safety",
    )
    op.create_index(
        "ix_equipment_facility_hazards_residual_risk",
        _TABLE,
        ["residual_risk"],
        schema="safety",
    )


def downgrade() -> None:
    op.drop_index("ix_equipment_facility_hazards_residual_risk", table_name=_TABLE, schema="safety")
    op.drop_index("ix_equipment_facility_hazards_control_level", table_name=_TABLE, schema="safety")
    op.drop_table(_TABLE, schema="safety")
