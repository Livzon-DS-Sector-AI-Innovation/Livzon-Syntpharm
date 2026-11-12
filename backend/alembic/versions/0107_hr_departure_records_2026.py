"""rebuild hr departure records with the 2026 ledger fields

Revision ID: 0107_hr_departure_records_2026
Revises: 0106_hr_onboarding_records_2026
Create Date: 2026-11-12

离职台账（ticket #200）重建：
- 删除旧的 `hr.departure_records` 及其数据（旧的飞书多维表格镜像已废弃）；
- 按 2026 台账字段重建：一级/二级部门 / 姓名 / 性别 / 岗位 / 岗位层级 /
  人员身份 / 入职日期 / 离职日期 / 离职类别 / 离职原因 / 学历 / 年龄 / 司龄 /
  集团月报表人员分类；
- 人员字段来自 `hr.employee_profiles`，保存后冻结；`person_id` 仅作来源引用；
- 员工档案镜像补充 `education` / `age`，供离职台账冻结人员快照。
只动 hr schema。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0107_hr_departure_records_2026"
down_revision: str = "0106_hr_onboarding_records_2026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "hr"
_PROFILE_TABLE = "employee_profiles"
_TABLE = "departure_records"


def upgrade() -> None:
    op.add_column(
        _PROFILE_TABLE,
        sa.Column("education", sa.String(length=16), server_default="", nullable=False, comment="学历"),
        schema=_SCHEMA,
    )
    op.add_column(
        _PROFILE_TABLE,
        sa.Column("age", sa.Integer(), nullable=True, comment="年龄"),
        schema=_SCHEMA,
    )

    op.drop_table(_TABLE, schema=_SCHEMA)

    op.create_table(
        _TABLE,
        sa.Column(
            "person_id",
            sa.Uuid(),
            nullable=False,
            comment="员工档案 id（人员来源）",
        ),
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
        sa.Column(
            "tenure_years",
            sa.Numeric(precision=4, scale=1),
            nullable=False,
            comment="司龄（年，保留一位小数）",
        ),
        sa.Column("group_classification", sa.String(length=32), nullable=False, comment="集团月报表人员分类"),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["identity.users.id"]),
        sa.ForeignKeyConstraint(["person_id"], [f"{_SCHEMA}.{_PROFILE_TABLE}.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["identity.users.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema=_SCHEMA,
    )
    op.create_index("ix_departure_department_level1", _TABLE, ["department_level1"], unique=False, schema=_SCHEMA)
    op.create_index("ix_departure_leave_date", _TABLE, ["leave_date"], unique=False, schema=_SCHEMA)
    op.create_index("ix_departure_name", _TABLE, ["name"], unique=False, schema=_SCHEMA)


def downgrade() -> None:
    op.drop_table(_TABLE, schema=_SCHEMA)

    op.drop_column(_PROFILE_TABLE, "age", schema=_SCHEMA)
    op.drop_column(_PROFILE_TABLE, "education", schema=_SCHEMA)

    op.create_table(
        _TABLE,
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
    op.create_index("ix_departure_department", _TABLE, ["department"], unique=False, schema=_SCHEMA)
    op.create_index("ix_departure_feishu_record_id", _TABLE, ["feishu_record_id"], unique=False, schema=_SCHEMA)
    op.create_index("ix_departure_offboarding_date", _TABLE, ["offboarding_date"], unique=False, schema=_SCHEMA)
