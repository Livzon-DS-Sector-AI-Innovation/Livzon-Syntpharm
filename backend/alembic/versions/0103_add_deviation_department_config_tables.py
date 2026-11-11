"""add deviation department config tables

Revision ID: 0103_add_deviation_department_config_tables
Revises: 0102_add_deviation_ledger_detail_fields
Create Date: 2026-11-10

补齐偏差流转依赖的两张组织配置表：部门联系人、部门每周确认。

历史 `0022_add_quality_module_tables` 的 upgrade 曾删除基线里的 `quality.department_contacts`
与 `quality.department_weekly_confirmations`，随后并未重建，因此 ORM 一直缺少对应物理表。
本迁移按 `deviation_department_models.py` 重新建表，字段与 ORM 保持一致。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, TEXT

from alembic import op

revision: str = "0103_add_deviation_department_config_tables"
down_revision: str = "0102_add_deviation_ledger_detail_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "quality"


def _base_columns() -> list[sa.Column]:
    """与 app.shared.base_model.BaseModel 对齐的公共列。"""
    return [
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.Uuid(as_uuid=True), sa.ForeignKey("identity.users.id"), nullable=True),
        sa.Column("updated_by", sa.Uuid(as_uuid=True), sa.ForeignKey("identity.users.id"), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "department_contacts",
        *_base_columns(),
        sa.Column("department", sa.String(length=255), nullable=False, comment="部门名称"),
        sa.Column(
            "dept_head_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("identity.users.id"),
            nullable=True,
            comment="部门负责人",
        ),
        sa.Column(
            "production_head_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("identity.users.id"),
            nullable=True,
            comment="生产负责人",
        ),
        sa.Column(
            "quality_head_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("identity.users.id"),
            nullable=True,
            comment="质量负责人",
        ),
        sa.Column(
            "qa_staff_ids",
            ARRAY(TEXT),
            nullable=True,
            comment="QA 人员（[0]=所属 QA，[1]=QA 负责人；兼容 UUID 与 open_id）",
        ),
        sa.Column("gmp_staff_ids", ARRAY(TEXT), nullable=True, comment="GMP 人员（周确认与未提交提醒的接收人）"),
        sa.Column("additional_contacts", ARRAY(TEXT), nullable=True, comment="其他联系人"),
        sa.Column(
            "is_production_workshop",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=True,
            comment="是否生产车间（周确认与群体提醒按此筛选）",
        ),
        sa.UniqueConstraint("department", name="department_contacts_department_key"),
        schema=_SCHEMA,
    )

    op.create_table(
        "department_weekly_confirmations",
        *_base_columns(),
        sa.Column("department", sa.String(length=255), nullable=False, comment="部门名称"),
        sa.Column("week_key", sa.String(length=20), nullable=False, comment="周标识，如 2026-W46"),
        sa.Column(
            "production_status",
            sa.String(length=20),
            nullable=False,
            comment="本周生产状态 production / stopped",
        ),
        sa.Column(
            "deviation_status",
            sa.String(length=50),
            server_default=sa.text("'unsubmitted'"),
            nullable=False,
            comment="偏差提交情况 submitted / unsubmitted",
        ),
        sa.Column(
            "confirmed_by_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("identity.users.id"),
            nullable=True,
            comment="确认人",
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True, comment="确认时间"),
        sa.UniqueConstraint("department", "week_key", name="uq_dept_weekly_confirmation"),
        schema=_SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("department_weekly_confirmations", schema=_SCHEMA)
    op.drop_table("department_contacts", schema=_SCHEMA)