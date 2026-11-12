"""drop hr teams and department production settings

Revision ID: 0126_hr_drop_teams_and_production_settings
Revises: 0125_add_deviation_attachment_comments
Create Date: 2026-11-12

HR 组织架构改为飞书镜像后的冗余下线：
- 删除未使用的 `hr.teams` 班组表及其索引；
- 删除 `hr.departments` 上的生产部门/班次字段。
只动 hr schema。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0126_hr_drop_teams_and_production_settings"
down_revision: str = "0125_add_deviation_attachment_comments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "hr"


def upgrade() -> None:
    op.drop_index("ix_teams_name", table_name="teams", schema=_SCHEMA)
    op.drop_index("ix_teams_department_id", table_name="teams", schema=_SCHEMA)
    op.drop_table("teams", schema=_SCHEMA)

    op.drop_column("departments", "production_end_time", schema=_SCHEMA)
    op.drop_column("departments", "production_start_time", schema=_SCHEMA)
    op.drop_column("departments", "is_production", schema=_SCHEMA)


def downgrade() -> None:
    op.add_column(
        "departments",
        sa.Column("is_production", sa.Boolean(), server_default="false", nullable=False, comment="是否生产部门"),
        schema=_SCHEMA,
    )
    op.add_column(
        "departments",
        sa.Column("production_start_time", sa.String(length=8), nullable=True, comment="生产班次开始时间(HH:MM)"),
        schema=_SCHEMA,
    )
    op.add_column(
        "departments",
        sa.Column("production_end_time", sa.String(length=8), nullable=True, comment="生产班次结束时间(HH:MM)"),
        schema=_SCHEMA,
    )

    op.create_table(
        "teams",
        sa.Column("name", sa.String(length=64), nullable=False, comment="班组名称"),
        sa.Column("code", sa.String(length=32), nullable=True, comment="班组编码"),
        sa.Column("description", sa.String(length=256), nullable=True, comment="班组描述"),
        sa.Column("department_id", sa.Uuid(), nullable=False, comment="所属部门ID"),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["identity.users.id"]),
        sa.ForeignKeyConstraint(["department_id"], ["hr.departments.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["identity.users.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema=_SCHEMA,
    )
    op.create_index("ix_teams_department_id", "teams", ["department_id"], unique=False, schema=_SCHEMA)
    op.create_index("ix_teams_name", "teams", ["name"], unique=False, schema=_SCHEMA)
