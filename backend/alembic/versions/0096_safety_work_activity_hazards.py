"""safety work activity hazard ledger

Revision ID: 0096_safety_work_activity_hazards
Revises: 0095_safety_hazard_identification_ledger_fields
Create Date: 2026-11-09

新增《作业活动危险源台账》空表：
L/E/C/D 使用精确小数；D 与评价级别由服务端计算；选项以稳定 key 存储。
只动 safety schema，单模块迁移。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0096_safety_work_activity_hazards"
down_revision: str = "0095_safety_hazard_identification_ledger_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "work_activity_hazards"
_SCHEMA = "safety"


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("position_location", sa.String(255), nullable=False, comment="岗位/地点"),
        sa.Column("area_activity", sa.String(255), nullable=False, comment="区域/活动"),
        sa.Column("hazard_name_or_event", sa.Text(), nullable=False, comment="危险源名称或潜在事件"),
        sa.Column("possible_harm", sa.Text(), nullable=False, comment="可能导致的危害"),
        sa.Column("hazard_type", sa.Text(), nullable=False, comment="危险源类型"),
        sa.Column("likelihood_l", sa.Numeric(18, 6), nullable=False, comment="可能性L（0.1–10）"),
        sa.Column("exposure_e", sa.Numeric(18, 6), nullable=False, comment="发生频次E（0.5–10）"),
        sa.Column("consequence_c", sa.Numeric(18, 6), nullable=False, comment="后果C（1–100）"),
        sa.Column(
            "risk_value_d",
            sa.Numeric(38, 18),
            nullable=False,
            comment="风险值D = L×E×C（服务端精确计算，只读）",
        ),
        sa.Column("evaluation_grade", sa.Integer(), nullable=False, comment="评价级别 1–4（4 最高，服务端计算）"),
        sa.Column("evaluation_grade_label", sa.String(20), nullable=False, comment="评价级别中文标签"),
        sa.Column("control_measures", sa.JSON(), nullable=False, comment="控制措施（有序的稳定 key 数组）"),
        sa.Column("residual_risk", sa.String(20), nullable=False, comment="残余风险 key"),
        sa.Column("residual_risk_label", sa.String(50), nullable=False, comment="残余风险中文标签"),
        sa.Column("control_level", sa.String(100), nullable=False, comment="管控层级（部门单选）"),
        sa.Column("execution_level", sa.String(20), nullable=False, comment="执行层级 key（车间/班组长）"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("identity.users.id"), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), sa.ForeignKey("identity.users.id"), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        schema="safety",
    )
    op.create_index(
        "ix_work_activity_hazards_control_level",
        _TABLE,
        ["control_level"],
        schema="safety",
    )
    op.create_index(
        "ix_work_activity_hazards_residual_risk",
        _TABLE,
        ["residual_risk"],
        schema="safety",
    )
    op.create_index(
        "ix_work_activity_hazards_evaluation_grade",
        _TABLE,
        ["evaluation_grade"],
        schema="safety",
    )


def downgrade() -> None:
    op.drop_index("ix_work_activity_hazards_evaluation_grade", table_name=_TABLE, schema="safety")
    op.drop_index("ix_work_activity_hazards_residual_risk", table_name=_TABLE, schema="safety")
    op.drop_index("ix_work_activity_hazards_control_level", table_name=_TABLE, schema="safety")
    op.drop_table(_TABLE, schema="safety")
