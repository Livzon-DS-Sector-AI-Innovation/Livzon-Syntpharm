"""safety hazard report safety officer

Revision ID: 0102_safety_hazard_safety_officer
Revises: 0101_safety_equipment_facility_evaluation_grade
Create Date: 2026-11-11

隐患台账（safety.hazard_reports）新增「分管安全员」：
- 之前该值只能按责任部门从 DEPARTMENT_CONFIG 推导，详情页无法按单条隐患调整；
- 现在落库 UUID + 姓名快照，为空时仍由读时回退部门配置安全员，不做存量回填。
只动 safety schema。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0102_safety_hazard_safety_officer"
down_revision: str = "0101_safety_equipment_facility_evaluation_grade"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "hazard_reports"
_SCHEMA = "safety"
_FK_NAME = "fk_hazard_reports_safety_officer_id_users"


def upgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column(
            "safety_officer_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="分管安全员（FK → identity.users）；为空时读时回退责任部门配置的安全员",
        ),
        schema=_SCHEMA,
    )
    op.add_column(
        _TABLE,
        sa.Column("safety_officer_name", sa.String(100), nullable=True, comment="分管安全员姓名快照"),
        schema=_SCHEMA,
    )
    op.create_foreign_key(
        _FK_NAME,
        _TABLE,
        "users",
        ["safety_officer_id"],
        ["id"],
        source_schema=_SCHEMA,
        referent_schema="identity",
    )


def downgrade() -> None:
    op.drop_constraint(_FK_NAME, _TABLE, schema=_SCHEMA, type_="foreignkey")
    op.drop_column(_TABLE, "safety_officer_name", schema=_SCHEMA)
    op.drop_column(_TABLE, "safety_officer_id", schema=_SCHEMA)
