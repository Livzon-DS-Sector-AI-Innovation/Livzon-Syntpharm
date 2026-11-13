"""consolidated HR org and ledger schema

Revision ID: 0116_hr_org_records
Revises: 0115_add_deviation_investigation_drafts
Create Date: 2026-11-13

Squashed HR migration for main. Unlike the UAT-only history, this migration
never adds or drops anything on `identity.departments`; the HR org mirror lives
entirely in `hr.departments`.

Only `hr` (and the settings migration that follows) is changed.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0116_hr_org_records"
down_revision: str = "0115_add_deviation_investigation_drafts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "hr"
_DEPARTMENTS = "departments"
_PROFILES = "employee_profiles"
_ONBOARDING = "onboarding_records"
_DEPARTURE = "departure_records"
_RUNS = "org_sync_runs"


def _create_profiles() -> None:
    op.create_table(
        _PROFILES,
        sa.Column("open_id", sa.String(length=128), nullable=False, comment="飞书 open_id（唯一键）"),
        sa.Column("name", sa.String(length=100), server_default="", nullable=False, comment="姓名"),
        sa.Column("mobile", sa.String(length=32), server_default="", nullable=False, comment="手机号"),
        sa.Column("email", sa.String(length=255), server_default="", nullable=False, comment="邮箱"),
        sa.Column("enterprise_email", sa.String(length=255), server_default="", nullable=False, comment="企业邮箱"),
        sa.Column("email_aliases", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="企业邮箱别名列表"),
        sa.Column("gender", sa.Integer(), nullable=True, comment="性别（飞书枚举：1 男 / 2 女）"),
        sa.Column("education", sa.String(length=16), server_default="", nullable=False, comment="学历"),
        sa.Column("age", sa.Integer(), nullable=True, comment="年龄"),
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
            "resign_time", sa.String(length=64), server_default="", nullable=False, comment="离职时间（飞书原始字符串）"
        ),
        sa.Column("is_admin", sa.Boolean(), server_default="false", nullable=False, comment="是否普通管理员"),
        sa.Column("is_primary_admin", sa.Boolean(), server_default="false", nullable=False, comment="是否超级管理员"),
        sa.Column("data_source", sa.Integer(), nullable=True, comment="飞书数据来源枚举"),
        sa.Column("employee_no", sa.String(length=64), server_default="", nullable=False, comment="工号"),
        sa.Column("job_title_id", sa.String(length=128), server_default="", nullable=False, comment="职务 ID"),
        sa.Column("job_title_name", sa.String(length=200), server_default="", nullable=False, comment="职务名称"),
        sa.Column("hire_date", sa.Date(), nullable=True, comment="入职日期"),
        sa.Column("employment_type", sa.Integer(), nullable=True, comment="员工类型（飞书枚举）"),
        sa.Column("staff_status", sa.Integer(), nullable=True, comment="人事状态（飞书枚举）"),
        sa.Column(
            "work_country_or_region", sa.String(length=128), server_default="", nullable=False, comment="工作国家/地区"
        ),
        sa.Column("work_place_id", sa.String(length=128), server_default="", nullable=False, comment="工作地点 ID"),
        sa.Column("work_place_name", sa.String(length=200), server_default="", nullable=False, comment="工作地点名称"),
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
        sa.Column("positions", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="职位列表 [{id, name}]"),
        sa.Column("job_level_id", sa.String(length=128), server_default="", nullable=False, comment="职级 ID"),
        sa.Column("job_level_name", sa.String(length=200), server_default="", nullable=False, comment="职级名称"),
        sa.Column("job_family_id", sa.String(length=128), server_default="", nullable=False, comment="序列（职族）ID"),
        sa.Column(
            "job_family_name", sa.String(length=200), server_default="", nullable=False, comment="序列（职族）名称"
        ),
        sa.Column(
            "department_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="所属部门 open_department_id 列表",
        ),
        sa.Column(
            "department_names", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="所属部门名称列表，与 department_ids 对齐"
        ),
        sa.Column("department_path", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="主部门路径，根 → 一级 → 二级，id + 名称"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True, comment="最近一次目录同步时间"),
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
    op.create_index("ix_hr_employee_profiles_name", _PROFILES, ["name"], schema=_SCHEMA)
    op.create_index("ix_hr_employee_profiles_employee_no", _PROFILES, ["employee_no"], schema=_SCHEMA)
    op.create_index("ix_hr_employee_profiles_staff_status", _PROFILES, ["staff_status"], schema=_SCHEMA)


def _create_onboarding() -> None:
    op.create_table(
        _ONBOARDING,
        sa.Column("serial_no", sa.String(length=32), nullable=False, comment="流水号"),
        sa.Column("department_level1", sa.String(length=64), nullable=False, comment="一级部门"),
        sa.Column("department_level2", sa.String(length=64), nullable=False, comment="二级部门"),
        sa.Column("name", sa.String(length=64), nullable=False, comment="姓名"),
        sa.Column("position", sa.String(length=64), nullable=False, comment="岗位"),
        sa.Column("position_level", sa.String(length=16), nullable=False, comment="岗位层级"),
        sa.Column("personnel_identity", sa.String(length=16), nullable=False, comment="人员身份"),
        sa.Column("hire_date", sa.Date(), nullable=False, comment="入职日期"),
        sa.Column("join_category", sa.String(length=16), nullable=False, comment="入职类别"),
        sa.Column("education", sa.String(length=16), nullable=False, comment="学历"),
        sa.Column("gender", sa.String(length=8), nullable=False, comment="性别"),
        sa.Column("age", sa.Integer(), nullable=False, comment="年龄"),
        sa.Column("mobile", sa.String(length=32), nullable=False, comment="手机号码"),
        sa.Column("group_classification", sa.String(length=32), nullable=False, comment="集团月报表人员分类"),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["identity.users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["identity.users.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema=_SCHEMA,
    )
    op.create_index("ix_onboarding_department_level1", _ONBOARDING, ["department_level1"], schema=_SCHEMA)
    op.create_index("ix_onboarding_hire_date", _ONBOARDING, ["hire_date"], schema=_SCHEMA)
    op.create_index("ix_onboarding_name", _ONBOARDING, ["name"], schema=_SCHEMA)


def _create_departure() -> None:
    op.create_table(
        _DEPARTURE,
        sa.Column("person_id", sa.Uuid(), nullable=True, comment="员工档案 id（可选；不在档案中的人员可手工录入）"),
        sa.Column("department_level1", sa.String(length=64), nullable=False, comment="一级部门"),
        sa.Column("department_level2", sa.String(length=64), nullable=False, comment="二级部门"),
        sa.Column("name", sa.String(length=64), nullable=False, comment="姓名"),
        sa.Column("gender", sa.String(length=8), nullable=False, comment="性别"),
        sa.Column("position", sa.String(length=64), nullable=False, comment="岗位"),
        sa.Column("hire_date", sa.Date(), nullable=False, comment="入职日期"),
        sa.Column("education", sa.String(length=16), nullable=False, comment="学历"),
        sa.Column("age", sa.Integer(), nullable=False, comment="年龄"),
        sa.Column("position_level", sa.String(length=16), nullable=False, comment="岗位层级"),
        sa.Column("personnel_identity", sa.String(length=16), nullable=False, comment="人员身份"),
        sa.Column("leave_date", sa.Date(), nullable=False, comment="离职日期"),
        sa.Column("leave_category", sa.String(length=16), nullable=False, comment="离职类别"),
        sa.Column("leave_reason", sa.String(length=255), nullable=False, comment="离职原因"),
        sa.Column("tenure_years", sa.Numeric(precision=4, scale=1), nullable=False, comment="司龄（年，保留一位小数）"),
        sa.Column("group_classification", sa.String(length=32), nullable=False, comment="集团月报表人员分类"),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["identity.users.id"]),
        sa.ForeignKeyConstraint(["person_id"], [f"{_SCHEMA}.{_PROFILES}.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["identity.users.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema=_SCHEMA,
    )
    op.create_index("ix_departure_department_level1", _DEPARTURE, ["department_level1"], schema=_SCHEMA)
    op.create_index("ix_departure_leave_date", _DEPARTURE, ["leave_date"], schema=_SCHEMA)
    op.create_index("ix_departure_name", _DEPARTURE, ["name"], schema=_SCHEMA)


def _create_legacy_onboarding() -> None:
    op.create_table(
        _ONBOARDING,
        sa.Column("seq_number", sa.Integer(), nullable=True, comment="编号（飞书自动编号）"),
        sa.Column("employee_number", sa.String(length=32), nullable=False, comment="工号"),
        sa.Column("name", sa.String(length=64), nullable=False, comment="姓名"),
        sa.Column("domain_account", sa.String(length=64), nullable=True, comment="域账号"),
        sa.Column("department", sa.String(length=64), nullable=False, comment="部门"),
        sa.Column("team", sa.String(length=64), nullable=True, comment="班组"),
        sa.Column("position", sa.String(length=64), nullable=False, comment="岗位"),
        sa.Column("job_category", sa.String(length=32), nullable=True, comment="职类"),
        sa.Column("status_category", sa.String(length=32), nullable=True, comment="统计类别"),
        sa.Column("is_employed", sa.String(length=8), nullable=True, comment="是否在职: 是/否"),
        sa.Column("hire_date", sa.Date(), nullable=False, comment="入职时间"),
        sa.Column("factory_entry_date", sa.Date(), nullable=True, comment="进厂时间"),
        sa.Column("livo_entry_date", sa.Date(), nullable=True, comment="入丽珠时间"),
        sa.Column("work_start_date", sa.Date(), nullable=True, comment="参加工作时间"),
        sa.Column("graduation_date", sa.Date(), nullable=True, comment="毕业时间"),
        sa.Column("birth_month", sa.Integer(), nullable=True, comment="出生月份"),
        sa.Column("birth_day", sa.Integer(), nullable=True, comment="出生日期"),
        sa.Column("contract_type", sa.String(length=32), nullable=True, comment="合同期限"),
        sa.Column("contract_start_date", sa.Date(), nullable=True, comment="第一次合同起点"),
        sa.Column("contract_end_date", sa.Date(), nullable=True, comment="第一次合同终止"),
        sa.Column("contract_start_2", sa.Date(), nullable=True, comment="第二次合同起点"),
        sa.Column("contract_end_2", sa.Date(), nullable=True, comment="第二次合同终止"),
        sa.Column("contract_start_3", sa.Date(), nullable=True, comment="第三次合同起点"),
        sa.Column("contract_end_3", sa.Date(), nullable=True, comment="第三次合同终止"),
        sa.Column("contract_start_4", sa.Date(), nullable=True, comment="第四次合同起点"),
        sa.Column("contract_end_4", sa.Date(), nullable=True, comment="第四次合同终止"),
        sa.Column("age", sa.Integer(), nullable=True, comment="年龄（飞书公式）"),
        sa.Column("work_years", sa.Integer(), nullable=True, comment="工作年限（飞书公式）"),
        sa.Column("factory_tenure", sa.String(length=32), nullable=True, comment="厂龄（飞书公式）"),
        sa.Column("company_tenure", sa.String(length=32), nullable=True, comment="司龄（飞书公式）"),
        sa.Column("hire_month", sa.String(length=16), nullable=True, comment="入职月份（飞书公式）"),
        sa.Column("school", sa.String(length=128), nullable=True, comment="毕业学校"),
        sa.Column("education", sa.String(length=16), nullable=True, comment="学历"),
        sa.Column("major", sa.String(length=64), nullable=True, comment="专业"),
        sa.Column("classification", sa.String(length=16), nullable=True, comment="分类：全日制/非全日制"),
        sa.Column("id_card", sa.String(length=18), nullable=True, comment="身份证号"),
        sa.Column("id_card_expiry", sa.String(length=32), nullable=True, comment="身份证到期日"),
        sa.Column("id_card_address", sa.Text(), nullable=True, comment="身份证地址|家庭地址"),
        sa.Column("current_address", sa.Text(), nullable=True, comment="现住址"),
        sa.Column("marital_status", sa.String(length=16), nullable=True, comment="婚姻状况"),
        sa.Column("household_type", sa.String(length=16), nullable=True, comment="户籍类型"),
        sa.Column("political_status", sa.String(length=32), nullable=True, comment="政治面貌"),
        sa.Column("phone", sa.String(length=32), nullable=True, comment="手机"),
        sa.Column("email", sa.String(length=128), nullable=True, comment="邮箱"),
        sa.Column("emergency_contact_phone", sa.String(length=32), nullable=True, comment="紧急联系人电话"),
        sa.Column("emergency_contact_relation", sa.String(length=32), nullable=True, comment="紧急联系人|关系"),
        sa.Column("bank_account", sa.String(length=32), nullable=True, comment="银行卡号"),
        sa.Column("bank_account_location", sa.String(length=32), nullable=True, comment="银行卡开户地"),
        sa.Column("training_id", sa.String(length=32), nullable=True, comment="培训档案编号"),
        sa.Column("transfer_history", sa.Text(), nullable=True, comment="异动（含曾经工作部门、岗位)"),
        sa.Column("remarks", sa.JSON(), nullable=True, comment="备注（多选）"),
        sa.Column("feishu_record_id", sa.String(length=32), nullable=True, comment="飞书多维表格 record_id"),
        sa.Column("feishu_synced_at", sa.Date(), nullable=True, comment="上次飞书同步时间"),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["identity.users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["identity.users.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema=_SCHEMA,
    )
    op.create_index("ix_onboarding_department", _ONBOARDING, ["department"], unique=False, schema=_SCHEMA)
    op.create_index("ix_onboarding_employee_number", _ONBOARDING, ["employee_number"], unique=False, schema=_SCHEMA)
    op.create_index("ix_onboarding_feishu_record_id", _ONBOARDING, ["feishu_record_id"], unique=False, schema=_SCHEMA)
    op.create_index("ix_onboarding_hire_date", _ONBOARDING, ["hire_date"], unique=False, schema=_SCHEMA)


def _create_legacy_departure() -> None:
    op.create_table(
        _DEPARTURE,
        sa.Column("name", sa.String(length=64), nullable=False, comment="姓名"),
        sa.Column("department", sa.String(length=64), nullable=False, comment="部门"),
        sa.Column("team", sa.String(length=64), nullable=True, comment="班组"),
        sa.Column("position", sa.String(length=64), nullable=False, comment="职位"),
        sa.Column("job_category", sa.String(length=64), nullable=True, comment="职类"),
        sa.Column("gender", sa.String(length=8), nullable=True, comment="性别"),
        sa.Column("status_category", sa.String(length=64), nullable=True, comment="统计类别"),
        sa.Column("livo_entry_date", sa.Date(), nullable=True, comment="入丽珠时间"),
        sa.Column("factory_entry_date", sa.Date(), nullable=True, comment="进厂时间"),
        sa.Column("work_start_date", sa.Date(), nullable=True, comment="参加工作时间"),
        sa.Column("offboarding_date", sa.Date(), nullable=True, comment="离职日期"),
        sa.Column("company_tenure_at_leave", sa.String(length=64), nullable=True, comment="离职时司龄"),
        sa.Column("education", sa.String(length=16), nullable=True, comment="学历"),
        sa.Column("school", sa.String(length=128), nullable=True, comment="毕业学校"),
        sa.Column("major", sa.String(length=64), nullable=True, comment="专业"),
        sa.Column("classification", sa.String(length=16), nullable=True, comment="分类：全日制/非全日制"),
        sa.Column("id_card", sa.String(length=18), nullable=True, comment="身份证号"),
        sa.Column("native_place", sa.String(length=64), nullable=True, comment="籍贯"),
        sa.Column("household_type", sa.String(length=128), nullable=True, comment="户籍类型"),
        sa.Column("marital_status", sa.String(length=32), nullable=True, comment="婚姻状况"),
        sa.Column("political_status", sa.String(length=64), nullable=True, comment="政治面貌"),
        sa.Column("phone", sa.String(length=32), nullable=True, comment="手机"),
        sa.Column("emergency_contact_phone", sa.String(length=32), nullable=True, comment="紧急联系人电话"),
        sa.Column("emergency_contact_relation", sa.String(length=64), nullable=True, comment="紧急联系人|关系"),
        sa.Column("bank_account", sa.String(length=128), nullable=True, comment="银行卡号"),
        sa.Column("contract_type", sa.String(length=64), nullable=True, comment="合同期限"),
        sa.Column("transfer_history", sa.Text(), nullable=True, comment="异动（含曾经工作部门、岗位)"),
        sa.Column(
            "offboarding_type",
            sa.String(length=16),
            server_default="辞职",
            nullable=False,
            comment="离职类型: 辞职, 辞退, 合同到期, 退休, 其他",
        ),
        sa.Column(
            "offboarding_reason", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="离职原因（多选）"
        ),
        sa.Column(
            "offboarding_reason_2",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="离职原因2（多选）",
        ),
        sa.Column(
            "offboarding_remarks",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="离职备注（多选）",
        ),
        sa.Column("remarks", sa.Text(), nullable=True, comment="备注"),
        sa.Column("feishu_record_id", sa.String(length=32), nullable=True, comment="飞书多维表格 record_id"),
        sa.Column("feishu_synced_at", sa.Date(), nullable=True, comment="上次飞书同步时间"),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["identity.users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["identity.users.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema=_SCHEMA,
    )
    op.create_index("ix_departure_department", _DEPARTURE, ["department"], unique=False, schema=_SCHEMA)
    op.create_index("ix_departure_feishu_record_id", _DEPARTURE, ["feishu_record_id"], unique=False, schema=_SCHEMA)
    op.create_index("ix_departure_offboarding_date", _DEPARTURE, ["offboarding_date"], unique=False, schema=_SCHEMA)


def upgrade() -> None:
    op.drop_index("ix_teams_name", table_name="teams", schema=_SCHEMA)
    op.drop_index("ix_teams_department_id", table_name="teams", schema=_SCHEMA)
    op.drop_table("teams", schema=_SCHEMA)

    op.drop_column(_DEPARTMENTS, "production_end_time", schema=_SCHEMA)
    op.drop_column(_DEPARTMENTS, "production_start_time", schema=_SCHEMA)
    op.drop_column(_DEPARTMENTS, "is_production", schema=_SCHEMA)

    op.alter_column(
        _DEPARTMENTS, "name", type_=sa.String(200), existing_type=sa.String(64), existing_nullable=False, schema=_SCHEMA
    )
    op.alter_column(
        _DEPARTMENTS,
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
        sa.Column("leader_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="负责人 open_id，按飞书返回顺序"),
        sa.Column("department_path", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="部门路径，按根到自身的顺序存储 id+名称"),
        sa.Column("recursive_members_count", sa.Integer(), nullable=True, comment="递归成员数"),
        sa.Column("direct_members_count", sa.Integer(), nullable=True, comment="直属成员数"),
        sa.Column("recursive_departments_count", sa.Integer(), nullable=True, comment="递归下级部门数"),
        sa.Column("direct_departments_count", sa.Integer(), nullable=True, comment="直属下级部门数"),
        sa.Column("enabled_status", sa.Boolean(), nullable=True, comment="飞书启用状态"),
        sa.Column("data_source", sa.Integer(), nullable=True, comment="飞书数据来源枚举"),
        sa.Column(
            "custom_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="飞书部门自定义字段"
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
        op.add_column(_DEPARTMENTS, column, schema=_SCHEMA)
    op.create_unique_constraint("uq_hr_departments_feishu_id", _DEPARTMENTS, ["feishu_department_id"], schema=_SCHEMA)

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

    _create_profiles()
    op.drop_table(_ONBOARDING, schema=_SCHEMA)
    _create_onboarding()
    op.drop_table(_DEPARTURE, schema=_SCHEMA)
    _create_departure()
    op.drop_table("offboarding_records", schema=_SCHEMA)

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
                level, "order", status_is_deleted, created_at, updated_at, is_deleted
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
                i."order", COALESCE(i.status_is_deleted, false), now(), now(), false
            FROM identity.departments AS i
            WHERE i.is_deleted = false
              AND NOT EXISTS (
                  SELECT 1 FROM hr.departments AS h WHERE h.feishu_department_id = i.feishu_department_id
              )
            """
        )
    )
    op.execute(sa.text("UPDATE hr.departments SET status_is_deleted = true WHERE feishu_department_id IS NULL"))


def downgrade() -> None:
    op.drop_index("ix_departure_name", table_name=_DEPARTURE, schema=_SCHEMA)
    op.drop_index("ix_departure_leave_date", table_name=_DEPARTURE, schema=_SCHEMA)
    op.drop_index("ix_departure_department_level1", table_name=_DEPARTURE, schema=_SCHEMA)
    op.drop_table(_DEPARTURE, schema=_SCHEMA)
    op.drop_index("ix_onboarding_name", table_name=_ONBOARDING, schema=_SCHEMA)
    op.drop_index("ix_onboarding_hire_date", table_name=_ONBOARDING, schema=_SCHEMA)
    op.drop_index("ix_onboarding_department_level1", table_name=_ONBOARDING, schema=_SCHEMA)
    op.drop_table(_ONBOARDING, schema=_SCHEMA)
    op.drop_index("ix_hr_employee_profiles_staff_status", table_name=_PROFILES, schema=_SCHEMA)
    op.drop_index("ix_hr_employee_profiles_employee_no", table_name=_PROFILES, schema=_SCHEMA)
    op.drop_index("ix_hr_employee_profiles_name", table_name=_PROFILES, schema=_SCHEMA)
    op.drop_table(_PROFILES, schema=_SCHEMA)
    op.drop_index("ix_hr_org_sync_runs_started_at", table_name=_RUNS, schema=_SCHEMA)
    op.drop_table(_RUNS, schema=_SCHEMA)
    _create_legacy_onboarding()
    _create_legacy_departure()

    op.drop_constraint("uq_hr_departments_feishu_id", _DEPARTMENTS, type_="unique", schema=_SCHEMA)
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
        op.drop_column(_DEPARTMENTS, column, schema=_SCHEMA)
    op.execute(sa.text("DELETE FROM hr.departments WHERE code IS NULL"))
    op.alter_column(_DEPARTMENTS, "code", nullable=False, existing_type=sa.String(32), schema=_SCHEMA)
    op.alter_column(_DEPARTMENTS, "name", type_=sa.String(64), existing_type=sa.String(200), schema=_SCHEMA)

    op.add_column(
        _DEPARTMENTS,
        sa.Column("is_production", sa.Boolean(), server_default="false", nullable=False, comment="是否生产部门"),
        schema=_SCHEMA,
    )
    op.add_column(
        _DEPARTMENTS,
        sa.Column("production_start_time", sa.String(length=8), nullable=True, comment="生产班次开始时间(HH:MM)"),
        schema=_SCHEMA,
    )
    op.add_column(
        _DEPARTMENTS,
        sa.Column("production_end_time", sa.String(length=8), nullable=True, comment="生产班次结束时间(HH:MM)"),
        schema=_SCHEMA,
    )
    op.create_table(
        "teams",
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=True),
        sa.Column("description", sa.String(length=256), nullable=True),
        sa.Column("department_id", sa.Uuid(), nullable=False),
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
    op.create_index("ix_teams_department_id", "teams", ["department_id"], schema=_SCHEMA)
    op.create_index("ix_teams_name", "teams", ["name"], schema=_SCHEMA)
    op.create_table(
        "offboarding_records",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("employee_id", sa.UUID(), sa.ForeignKey("hr.employees.id"), nullable=False),
        sa.Column("offboarding_date", sa.Date(), nullable=False),
        sa.Column("offboarding_type", sa.String(16), nullable=False, server_default="辞职"),
        sa.Column("reason", sa.String(512), nullable=True),
        sa.Column("handover_status", sa.String(16), nullable=False, server_default="待交接"),
        sa.Column("notes", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        schema=_SCHEMA,
    )
    op.create_index("ix_offboarding_employee_id", "offboarding_records", ["employee_id"], schema=_SCHEMA)
    op.create_index("ix_offboarding_date", "offboarding_records", ["offboarding_date"], schema=_SCHEMA)
