"""rebuild hr onboarding records with the 2026 ledger fields

Revision ID: 0118_hr_onboarding_records_2026
Revises: 0117_hr_employee_profiles
Create Date: 2026-11-12

入职台账（ticket #199）重建：
- 删除旧的 `hr.onboarding_records` 及其数据（旧的飞书多维表格镜像已废弃）；
- 按 2026 台账字段重建：流水号 / 一级、二级部门 / 姓名 / 岗位 / 岗位层级 /
  人员身份 / 入职日期 / 入职类别 / 学历 / 性别 / 年龄 / 手机号码 /
  集团月报表人员分类；
- 仅保留内部 UUID，不再保留序号与飞书同步字段。
只动 hr schema。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0118_hr_onboarding_records_2026"
down_revision: str = "0117_hr_employee_profiles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "hr"
_TABLE = "onboarding_records"


def upgrade() -> None:
    op.drop_table(_TABLE, schema=_SCHEMA)

    op.create_table(
        _TABLE,
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
    op.create_index("ix_onboarding_department_level1", _TABLE, ["department_level1"], unique=False, schema=_SCHEMA)
    op.create_index("ix_onboarding_hire_date", _TABLE, ["hire_date"], unique=False, schema=_SCHEMA)
    op.create_index("ix_onboarding_name", _TABLE, ["name"], unique=False, schema=_SCHEMA)


def downgrade() -> None:
    op.drop_table(_TABLE, schema=_SCHEMA)

    op.create_table(
        _TABLE,
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
    op.create_index("ix_onboarding_department", _TABLE, ["department"], unique=False, schema=_SCHEMA)
    op.create_index("ix_onboarding_employee_number", _TABLE, ["employee_number"], unique=False, schema=_SCHEMA)
    op.create_index("ix_onboarding_feishu_record_id", _TABLE, ["feishu_record_id"], unique=False, schema=_SCHEMA)
    op.create_index("ix_onboarding_hire_date", _TABLE, ["hire_date"], unique=False, schema=_SCHEMA)
