"""registration project ↔ drug link

Revision ID: 0117_registration_project_drug_link
Revises: 0116_registration_drug_node_skipped
Create Date: 2026-11-12

注册项目关联审评品种（drugs）：项目表新增可空外键 drug_id，删除品种时置空，
使注册项目（全周期状态）与申报进度（节点推算）可以双向展示与跳转。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0117_registration_project_drug_link"
down_revision: str = "0116_registration_drug_node_skipped"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "registration"
_TABLE = "registration_projects"


def upgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column("drug_id", sa.Uuid(), nullable=True, comment="关联审评品种ID"),
        schema=_SCHEMA,
    )
    op.create_foreign_key(
        "fk_registration_projects_drug_id",
        _TABLE,
        "drugs",
        ["drug_id"],
        ["id"],
        source_schema=_SCHEMA,
        referent_schema=_SCHEMA,
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_registration_projects_drug_id",
        _TABLE,
        ["drug_id"],
        schema=_SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_registration_projects_drug_id", table_name=_TABLE, schema=_SCHEMA)
    op.drop_constraint(
        "fk_registration_projects_drug_id",
        _TABLE,
        type_="foreignkey",
        schema=_SCHEMA,
    )
    op.drop_column(_TABLE, "drug_id", schema=_SCHEMA)
