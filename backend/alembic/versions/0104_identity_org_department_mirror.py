"""identity department mirror: Feishu directory fields + org sync runs

Revision ID: 0104_identity_org_department_mirror
Revises: 0103_drop_hr_teams_and_production_settings
Create Date: 2026-11-12

部门管理（ticket #197）改为飞书组织架构只读镜像：
- `identity.departments` 增加启用状态、排序权重、部门路径、负责人 ids、
  递归/直属成员数与下级部门数、数据来源、最近目录同步时间、自定义字段；
- 新增 `identity.org_sync_runs` 保存每次同步的时间、成功/失败、数量与错误。
只动 identity schema；部门缺失时只标记隐藏，不物理删除。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0104_identity_org_department_mirror"
down_revision: str = "0103_drop_hr_teams_and_production_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "identity"
_TABLE = "departments"


def upgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column("enabled_status", sa.Boolean(), nullable=True, comment="飞书启用状态"),
        schema=_SCHEMA,
    )
    op.add_column(
        _TABLE,
        sa.Column("order_weight", sa.String(length=64), nullable=True, comment="飞书排序权重（原始字符串）"),
        schema=_SCHEMA,
    )
    op.add_column(
        _TABLE,
        sa.Column(
            "department_path",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="部门路径，按根到自身的顺序存储 id+名称",
        ),
        schema=_SCHEMA,
    )
    op.add_column(
        _TABLE,
        sa.Column(
            "leader_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="负责人 open_id，按飞书返回顺序",
        ),
        schema=_SCHEMA,
    )
    op.add_column(
        _TABLE,
        sa.Column("recursive_members_count", sa.Integer(), nullable=True, comment="递归成员数（含下级部门）"),
        schema=_SCHEMA,
    )
    op.add_column(
        _TABLE,
        sa.Column("direct_members_count", sa.Integer(), nullable=True, comment="直属成员数"),
        schema=_SCHEMA,
    )
    op.add_column(
        _TABLE,
        sa.Column("recursive_departments_count", sa.Integer(), nullable=True, comment="递归下级部门数"),
        schema=_SCHEMA,
    )
    op.add_column(
        _TABLE,
        sa.Column("direct_departments_count", sa.Integer(), nullable=True, comment="直属下级部门数"),
        schema=_SCHEMA,
    )
    op.add_column(
        _TABLE,
        sa.Column("data_source", sa.Integer(), nullable=True, comment="飞书数据来源枚举"),
        schema=_SCHEMA,
    )
    op.add_column(
        _TABLE,
        sa.Column(
            "directory_synced_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="最近一次目录同步时间",
        ),
        schema=_SCHEMA,
    )
    op.add_column(
        _TABLE,
        sa.Column(
            "custom_fields",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="飞书部门自定义字段（无标签，按 key 存储）",
        ),
        schema=_SCHEMA,
    )

    op.create_table(
        "org_sync_runs",
        sa.Column("status", sa.String(length=20), nullable=False, comment="running / success / failed"),
        sa.Column(
            "department_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
            comment="同步部门数",
        ),
        sa.Column(
            "people_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
            comment="同步人员数",
        ),
        sa.Column("error_message", sa.Text(), nullable=True, comment="失败原因"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, comment="开始时间"),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True, comment="结束时间"),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["created_by"], [f"{_SCHEMA}.users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], [f"{_SCHEMA}.users.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema=_SCHEMA,
    )
    op.create_index(
        "idx_identity_org_sync_runs_started_at",
        "org_sync_runs",
        ["started_at"],
        unique=False,
        schema=_SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("idx_identity_org_sync_runs_started_at", table_name="org_sync_runs", schema=_SCHEMA)
    op.drop_table("org_sync_runs", schema=_SCHEMA)

    op.drop_column(_TABLE, "custom_fields", schema=_SCHEMA)
    op.drop_column(_TABLE, "directory_synced_at", schema=_SCHEMA)
    op.drop_column(_TABLE, "data_source", schema=_SCHEMA)
    op.drop_column(_TABLE, "direct_departments_count", schema=_SCHEMA)
    op.drop_column(_TABLE, "recursive_departments_count", schema=_SCHEMA)
    op.drop_column(_TABLE, "direct_members_count", schema=_SCHEMA)
    op.drop_column(_TABLE, "recursive_members_count", schema=_SCHEMA)
    op.drop_column(_TABLE, "leader_ids", schema=_SCHEMA)
    op.drop_column(_TABLE, "department_path", schema=_SCHEMA)
    op.drop_column(_TABLE, "order_weight", schema=_SCHEMA)
    op.drop_column(_TABLE, "enabled_status", schema=_SCHEMA)
