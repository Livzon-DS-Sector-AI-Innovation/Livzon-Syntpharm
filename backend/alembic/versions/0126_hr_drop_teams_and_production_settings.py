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
    # 双轨合并守卫：main 链 0116_hr_org_records 已执行过同构清理时跳过
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("teams", schema=_SCHEMA):
        op.execute(sa.text("DROP TABLE hr.teams CASCADE"))

    existing = {c["name"] for c in inspector.get_columns("departments", schema=_SCHEMA)}
    for legacy_column in ("production_end_time", "production_start_time", "is_production"):
        if legacy_column in existing:
            op.drop_column("departments", legacy_column, schema=_SCHEMA)


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
