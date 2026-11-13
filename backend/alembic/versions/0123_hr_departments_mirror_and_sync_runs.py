"""make hr.departments the Feishu org mirror

Revision ID: 0123_hr_departments_mirror_and_sync_runs
Revises: 0122_hr_departure_person_comment
Create Date: 2026-11-13

Expand-only phase:
- add Feishu mirror fields to `hr.departments` (and make `code` optional),
- create `hr.org_sync_runs`,
- copy the current `identity.departments` mirror and sync-run history into HR.

The identity columns are dropped in the contract migration, after the code switch.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0123_hr_departments_mirror_and_sync_runs"
down_revision: str = "0122_hr_departure_person_comment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "hr"
_TABLE = "departments"
_RUNS = "org_sync_runs"


def upgrade() -> None:
    op.alter_column(
        _TABLE,
        "name",
        type_=sa.String(200),
        existing_type=sa.String(64),
        existing_nullable=False,
        schema=_SCHEMA,
    )
    op.alter_column(
        _TABLE,
        "code",
        nullable=True,
        existing_type=sa.String(32),
        existing_nullable=False,
        comment="部门编码（飞书部门可空）",
        schema=_SCHEMA,
    )

    for column in (
        sa.Column("feishu_department_id", sa.String(64), nullable=True, comment="飞书部门 open_department_id"),
        sa.Column("parent_feishu_department_id", sa.String(64), nullable=True, comment="父部门 open_id"),
        sa.Column("level", sa.Integer(), nullable=True, comment="层级：0 公司 / 1 一级 / 2 二级"),
        sa.Column("order", sa.Integer(), nullable=True, comment="同级排序"),
        sa.Column("order_weight", sa.String(64), nullable=True, comment="飞书排序权重（原始字符串）"),
        sa.Column(
            "leader_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="负责人 open_id，按飞书返回顺序",
        ),
        sa.Column(
            "department_path",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="部门路径，按根到自身的顺序存储 id+名称",
        ),
        sa.Column("recursive_members_count", sa.Integer(), nullable=True, comment="递归成员数"),
        sa.Column("direct_members_count", sa.Integer(), nullable=True, comment="直属成员数"),
        sa.Column("recursive_departments_count", sa.Integer(), nullable=True, comment="递归下级部门数"),
        sa.Column("direct_departments_count", sa.Integer(), nullable=True, comment="直属下级部门数"),
        sa.Column("enabled_status", sa.Boolean(), nullable=True, comment="飞书启用状态"),
        sa.Column("data_source", sa.Integer(), nullable=True, comment="飞书数据来源枚举"),
        sa.Column(
            "custom_fields",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="飞书部门自定义字段",
        ),
        sa.Column("directory_synced_at", sa.DateTime(timezone=True), nullable=True, comment="最近一次同步时间"),
        sa.Column(
            "status_is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
            comment="是否在飞书中移除/不在范围内",
        ),
    ):
        op.add_column(_TABLE, column, schema=_SCHEMA)

    op.create_unique_constraint("uq_hr_departments_feishu_id", _TABLE, ["feishu_department_id"], schema=_SCHEMA)

    op.create_table(
        _RUNS,
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, comment="running / success / failed"),
        sa.Column("department_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("people_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Uuid(as_uuid=True), sa.ForeignKey("identity.users.id"), nullable=True),
        sa.Column("updated_by", sa.Uuid(as_uuid=True), sa.ForeignKey("identity.users.id"), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        schema=_SCHEMA,
    )
    op.create_index("ix_hr_org_sync_runs_started_at", _RUNS, ["started_at"], schema=_SCHEMA)

    op.execute(
        sa.text(
            """
            UPDATE hr.departments AS h
            SET feishu_department_id = i.feishu_department_id,
                parent_feishu_department_id = i.parent_feishu_department_id,
                level = CASE
                    WHEN i.parent_feishu_department_id IS NULL THEN 1
                    WHEN i.parent_feishu_department_id IN (
                        SELECT feishu_department_id FROM identity.departments
                    ) THEN 2
                    ELSE 1
                END,
                "order" = i."order",
                order_weight = i.order_weight,
                leader_ids = i.leader_ids,
                department_path = i.department_path,
                recursive_members_count = i.recursive_members_count,
                direct_members_count = i.direct_members_count,
                recursive_departments_count = i.recursive_departments_count,
                direct_departments_count = i.direct_departments_count,
                enabled_status = i.enabled_status,
                data_source = i.data_source,
                custom_fields = i.custom_fields,
                directory_synced_at = i.directory_synced_at,
                status_is_deleted = COALESCE(i.status_is_deleted, false)
            FROM identity.departments AS i
            WHERE h.feishu_department_id IS NULL
              AND i.is_deleted = false
              AND h.name = i.name
            """
        )
    )

    op.execute(
        sa.text(
            """
            INSERT INTO hr.departments (
                id, name, code, description, feishu_department_id, parent_feishu_department_id,
                level, "order", order_weight, leader_ids, department_path,
                recursive_members_count, direct_members_count, recursive_departments_count,
                direct_departments_count, enabled_status, data_source, custom_fields,
                directory_synced_at, status_is_deleted, created_at, updated_at, is_deleted
            )
            SELECT
                gen_random_uuid(), i.name, NULL, NULL, i.feishu_department_id, i.parent_feishu_department_id,
                CASE
                    WHEN i.parent_feishu_department_id IS NULL THEN 1
                    WHEN i.parent_feishu_department_id IN (
                        SELECT feishu_department_id FROM identity.departments
                    ) THEN 2
                    ELSE 1
                END,
                i."order", i.order_weight, i.leader_ids, i.department_path,
                i.recursive_members_count, i.direct_members_count, i.recursive_departments_count,
                i.direct_departments_count, i.enabled_status, i.data_source, i.custom_fields,
                i.directory_synced_at, COALESCE(i.status_is_deleted, false), now(), now(), false
            FROM identity.departments AS i
            WHERE i.is_deleted = false
              AND NOT EXISTS (
                  SELECT 1 FROM hr.departments AS h WHERE h.feishu_department_id = i.feishu_department_id
              )
            """
        )
    )

    op.execute(sa.text("UPDATE hr.departments SET status_is_deleted = true WHERE feishu_department_id IS NULL"))

    op.execute(
        sa.text(
            """
            INSERT INTO hr.org_sync_runs (
                id, status, department_count, people_count, error_message,
                started_at, finished_at, created_at, updated_at, is_deleted
            )
            SELECT id, status, department_count, people_count, error_message,
                   started_at, finished_at, created_at, updated_at, false
            FROM identity.org_sync_runs
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_hr_org_sync_runs_started_at", table_name=_RUNS, schema=_SCHEMA)
    op.drop_table(_RUNS, schema=_SCHEMA)
    op.drop_constraint("uq_hr_departments_feishu_id", _TABLE, type_="unique", schema=_SCHEMA)
    for column in (
        "status_is_deleted",
        "directory_synced_at",
        "custom_fields",
        "data_source",
        "enabled_status",
        "direct_departments_count",
        "recursive_departments_count",
        "direct_members_count",
        "recursive_members_count",
        "department_path",
        "leader_ids",
        "order_weight",
        "order",
        "level",
        "parent_feishu_department_id",
        "feishu_department_id",
    ):
        op.drop_column(_TABLE, column, schema=_SCHEMA)
    op.execute(sa.text("DELETE FROM hr.departments WHERE code IS NULL"))
    op.alter_column(
        _TABLE,
        "code",
        nullable=False,
        existing_type=sa.String(32),
        schema=_SCHEMA,
    )
    op.alter_column(
        _TABLE,
        "name",
        type_=sa.String(64),
        existing_type=sa.String(200),
        schema=_SCHEMA,
    )
