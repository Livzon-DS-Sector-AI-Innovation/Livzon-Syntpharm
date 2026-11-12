"""safety equipment facility hazard evaluation grade

Revision ID: 0116_safety_equipment_facility_evaluation_grade
Revises: 0115_agent_ppt_video_highlight_project_default
Create Date: 2026-11-10

《设备设施危险源台账》新增评价级别：
按 R 分段落库（R < 10 → 1级，10 ≤ R < 20 → 2级，20 ≤ R < 40 → 3级，R ≥ 40 → 4级）。
先以可空列新增，回填全部存量行（含软删除）后再收紧为 NOT NULL。只动 safety schema。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0116_safety_equipment_facility_evaluation_grade"
down_revision: str = "0115_agent_ppt_video_highlight_project_default"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "equipment_facility_hazards"
_SCHEMA = "safety"
_INDEX = "ix_equipment_facility_hazards_evaluation_grade"


def upgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column(
            "evaluation_grade",
            sa.Integer(),
            nullable=True,
            comment="评价级别 1–4（按 R 分级，服务端计算，只读）",
        ),
        schema=_SCHEMA,
    )
    op.add_column(
        _TABLE,
        sa.Column("evaluation_grade_label", sa.String(20), nullable=True, comment="评价级别中文标签"),
        schema=_SCHEMA,
    )

    op.execute(
        sa.text(
            """
            UPDATE safety.equipment_facility_hazards
            SET evaluation_grade = CASE
                    WHEN risk_evaluation_r < 10 THEN 1
                    WHEN risk_evaluation_r < 20 THEN 2
                    WHEN risk_evaluation_r < 40 THEN 3
                    ELSE 4
                END,
                evaluation_grade_label = CASE
                    WHEN risk_evaluation_r < 10 THEN '1级'
                    WHEN risk_evaluation_r < 20 THEN '2级'
                    WHEN risk_evaluation_r < 40 THEN '3级'
                    ELSE '4级'
                END
            WHERE evaluation_grade IS NULL
            """
        )
    )

    op.alter_column(_TABLE, "evaluation_grade", nullable=False, schema=_SCHEMA)
    op.alter_column(_TABLE, "evaluation_grade_label", nullable=False, schema=_SCHEMA)

    op.create_index(_INDEX, _TABLE, ["evaluation_grade"], schema=_SCHEMA)


def downgrade() -> None:
    op.drop_index(_INDEX, table_name=_TABLE, schema=_SCHEMA)
    op.drop_column(_TABLE, "evaluation_grade_label", schema=_SCHEMA)
    op.drop_column(_TABLE, "evaluation_grade", schema=_SCHEMA)
