"""hr employee profile mirror

Revision ID: 0105_hr_employee_profiles
Revises: 0104_identity_org_department_mirror
Create Date: 2026-11-12

员工档案（ticket #198）新增飞书通讯录人员镜像：
- `hr.employee_profiles` 以飞书 open_id 为唯一键保存保留字段；
- 同步只 upsert，不删除、不按未返回停用任何人；
- 不保存 employee_id、subscription_ids、leader_id 及内嵌 department 对象。
只动 hr schema。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0105_hr_employee_profiles"
down_revision: str = "0104_identity_org_department_mirror"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "hr"
_TABLE = "employee_profiles"


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("open_id", sa.String(length=128), nullable=False, comment="飞书 open_id（唯一键）"),
        sa.Column("name", sa.String(length=100), server_default="", nullable=False, comment="姓名"),
        sa.Column("mobile", sa.String(length=32), server_default="", nullable=False, comment="手机号"),
        sa.Column("email", sa.String(length=255), server_default="", nullable=False, comment="邮箱"),
        sa.Column("enterprise_email", sa.String(length=255), server_default="", nullable=False, comment="企业邮箱"),
        sa.Column(
            "email_aliases",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="企业邮箱别名列表",
        ),
        sa.Column("gender", sa.Integer(), nullable=True, comment="性别（飞书枚举：1 男 / 2 女）"),
        sa.Column("description", sa.Text(), server_default="", nullable=False, comment="个性签名"),
        sa.Column("avatar_72", sa.String(length=1024), server_default="", nullable=False, comment="头像 72px URL"),
        sa.Column("avatar_240", sa.String(length=1024), server_default="", nullable=False, comment="头像 240px URL"),
        sa.Column("avatar_640", sa.String(length=1024), server_default="", nullable=False, comment="头像 640px URL"),
        sa.Column("avatar_origin", sa.String(length=1024), server_default="", nullable=False, comment="原始头像 URL"),
        sa.Column("background_image", sa.String(length=1024), server_default="", nullable=False, comment="背景图 URL"),
        sa.Column("geo_name", sa.String(length=64), server_default="", nullable=False, comment="地理名称"),
        sa.Column("active_status", sa.Integer(), nullable=True, comment="账号激活状态（飞书枚举）"),
        sa.Column("is_resigned", sa.Boolean(), server_default="false", nullable=False, comment="是否离职"),
        sa.Column(
            "resign_time",
            sa.String(length=64),
            server_default="",
            nullable=False,
            comment="离职时间（飞书原始字符串）",
        ),
        sa.Column("is_admin", sa.Boolean(), server_default="false", nullable=False, comment="是否普通管理员"),
        sa.Column(
            "is_primary_admin",
            sa.Boolean(),
            server_default="false",
            nullable=False,
            comment="是否超级管理员",
        ),
        sa.Column("data_source", sa.Integer(), nullable=True, comment="飞书数据来源枚举"),
        sa.Column("employee_no", sa.String(length=64), server_default="", nullable=False, comment="工号"),
        sa.Column("job_title_id", sa.String(length=128), server_default="", nullable=False, comment="职务 ID"),
        sa.Column("job_title_name", sa.String(length=200), server_default="", nullable=False, comment="职务名称"),
        sa.Column("hire_date", sa.Date(), nullable=True, comment="入职日期"),
        sa.Column("employment_type", sa.Integer(), nullable=True, comment="员工类型（飞书枚举）"),
        sa.Column("staff_status", sa.Integer(), nullable=True, comment="人事状态（飞书枚举）"),
        sa.Column(
            "work_country_or_region",
            sa.String(length=128),
            server_default="",
            nullable=False,
            comment="工作国家/地区",
        ),
        sa.Column("work_place_id", sa.String(length=128), server_default="", nullable=False, comment="工作地点 ID"),
        sa.Column(
            "work_place_name",
            sa.String(length=200),
            server_default="",
            nullable=False,
            comment="工作地点名称",
        ),
        sa.Column("work_station", sa.String(length=200), server_default="", nullable=False, comment="工位"),
        sa.Column("extension_number", sa.String(length=64), server_default="", nullable=False, comment="分机号"),
        sa.Column(
            "dotted_line_leader_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="虚线上级 open_id 列表",
        ),
        sa.Column("resign_date", sa.Date(), nullable=True, comment="离职日期"),
        sa.Column("resign_type", sa.String(length=100), server_default="", nullable=False, comment="离职类型"),
        sa.Column("resign_reason", sa.String(length=255), server_default="", nullable=False, comment="离职原因"),
        sa.Column("resign_remark", sa.Text(), server_default="", nullable=False, comment="离职备注"),
        sa.Column(
            "positions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="职位列表 [{id, name}]",
        ),
        sa.Column("job_level_id", sa.String(length=128), server_default="", nullable=False, comment="职级 ID"),
        sa.Column("job_level_name", sa.String(length=200), server_default="", nullable=False, comment="职级名称"),
        sa.Column(
            "job_family_id",
            sa.String(length=128),
            server_default="",
            nullable=False,
            comment="序列（职族）ID",
        ),
        sa.Column(
            "job_family_name",
            sa.String(length=200),
            server_default="",
            nullable=False,
            comment="序列（职族）名称",
        ),
        sa.Column(
            "department_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="所属部门 open_department_id 列表",
        ),
        sa.Column(
            "department_names",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="所属部门名称列表，与 department_ids 对齐",
        ),
        sa.Column(
            "department_path",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="主部门路径，根 → 一级 → 二级，id + 名称",
        ),
        sa.Column(
            "last_synced_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="最近一次目录同步时间",
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["identity.users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["identity.users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("open_id", name="uq_hr_employee_profiles_open_id"),
        schema=_SCHEMA,
    )
    op.create_index("ix_hr_employee_profiles_name", _TABLE, ["name"], unique=False, schema=_SCHEMA)
    op.create_index("ix_hr_employee_profiles_employee_no", _TABLE, ["employee_no"], unique=False, schema=_SCHEMA)
    op.create_index("ix_hr_employee_profiles_staff_status", _TABLE, ["staff_status"], unique=False, schema=_SCHEMA)


def downgrade() -> None:
    op.drop_index("ix_hr_employee_profiles_staff_status", table_name=_TABLE, schema=_SCHEMA)
    op.drop_index("ix_hr_employee_profiles_employee_no", table_name=_TABLE, schema=_SCHEMA)
    op.drop_index("ix_hr_employee_profiles_name", table_name=_TABLE, schema=_SCHEMA)
    op.drop_table(_TABLE, schema=_SCHEMA)
