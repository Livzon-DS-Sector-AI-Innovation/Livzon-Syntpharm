"""update departure person_id comment

Revision ID: 0134_hr_departure_person_comment
Revises: 0133_add_deviation_investigation_drafts
Create Date: 2026-11-13

`person_id` 改为可空后，列注释需与模型保持一致（允许不在员工档案中的人员）。
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0134_hr_departure_person_comment"
down_revision: str = "0133_add_deviation_investigation_drafts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "departure_records"
_SCHEMA = "hr"


def upgrade() -> None:
    op.alter_column(
        _TABLE,
        "person_id",
        existing_type=None,
        existing_nullable=True,
        comment="员工档案 id（可选；不在档案中的人员可手工录入）",
        schema=_SCHEMA,
    )


def downgrade() -> None:
    op.alter_column(
        _TABLE,
        "person_id",
        existing_type=None,
        existing_nullable=True,
        comment="员工档案 id（人员来源）",
        schema=_SCHEMA,
    )
