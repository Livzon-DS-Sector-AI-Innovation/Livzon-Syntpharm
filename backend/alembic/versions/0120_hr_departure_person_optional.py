"""allow departure records without an employee profile

Revision ID: 0120_hr_departure_person_optional
Revises: 0119_hr_departure_records_2026
Create Date: 2026-11-13

离职人员不一定存在于员工档案镜像中，因此 `hr.departure_records.person_id`
改为可空；手工录入时人员快照字段由表单直接提供。
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0120_hr_departure_person_optional"
down_revision: str = "0119_hr_departure_records_2026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "departure_records"
_SCHEMA = "hr"


def upgrade() -> None:
    op.alter_column(
        _TABLE,
        "person_id",
        nullable=True,
        schema=_SCHEMA,
        existing_comment="员工档案 id（人员来源）",
    )


def downgrade() -> None:
    op.alter_column(
        _TABLE,
        "person_id",
        nullable=False,
        schema=_SCHEMA,
        existing_comment="员工档案 id（可选；不在档案中的人员可手工录入）",
    )
