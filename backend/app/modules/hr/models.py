"""HR business ORM models live here."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import Base, BaseModel


class HrDepartment(BaseModel):
    __tablename__ = "departments"
    __table_args__ = (
        Index("ix_departments_code", "code"),
        UniqueConstraint("feishu_department_id", name="uq_hr_departments_feishu_id"),
        {"schema": "hr"},
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="部门名称")
    code: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True, comment="部门编码（飞书部门可空）")
    description: Mapped[str | None] = mapped_column(String(256), nullable=True, comment="部门描述")

    # ── 飞书组织目录镜像字段 ──
    feishu_department_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="飞书部门 open_department_id"
    )
    parent_feishu_department_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="父部门 open_id")
    level: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="层级：0 公司 / 1 一级 / 2 二级")
    order: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="同级排序")
    order_weight: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="飞书排序权重（原始字符串）")
    leader_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True, comment="负责人 open_id，按飞书返回顺序")
    department_path: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True, comment="部门路径，按根到自身的顺序存储 id+名称"
    )
    recursive_members_count: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="递归成员数")
    direct_members_count: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="直属成员数")
    recursive_departments_count: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="递归下级部门数")
    direct_departments_count: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="直属下级部门数")
    enabled_status: Mapped[bool | None] = mapped_column(Boolean, nullable=True, comment="飞书启用状态")
    data_source: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="飞书数据来源枚举")
    custom_fields: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True, comment="飞书部门自定义字段"
    )
    directory_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="最近一次同步时间"
    )
    status_is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", comment="是否在飞书中移除/不在范围内"
    )


class HrOrgSyncRun(BaseModel):
    """一次 HR 组织目录同步的运行记录。"""

    __tablename__ = "org_sync_runs"
    __table_args__ = (
        Index("ix_hr_org_sync_runs_started_at", "started_at"),
        {"schema": "hr"},
    )

    status: Mapped[str] = mapped_column(String(20), nullable=False, comment="running / success / failed")
    department_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    people_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Employee(BaseModel):
    __tablename__ = "employees"
    __table_args__ = (
        Index("ix_employees_department", "department"),
        Index("ix_employees_status", "status"),
        Index("ix_employees_employee_number", "employee_number"),
        Index("ix_employees_feishu_record_id", "feishu_record_id"),
        {"schema": "hr"},
    )

    # ─── Core identifiers ───
    employee_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, comment="工号")
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="姓名")
    domain_account: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="域账号")

    # ─── Department & job ───
    department: Mapped[str] = mapped_column(String(64), nullable=False, comment="部门")
    team: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="班组")
    position: Mapped[str] = mapped_column(String(64), nullable=False, comment="职位")
    job_category: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="职类")
    level: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="级别")

    # ─── 考勤相关 ───
    position_level: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        comment="职位级别(自动判定): 普通员工/工程师级/主管级",
    )

    # ─── Qualifications ───
    qualifications: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True, comment="职称／职业资格（多选）")
    qualification_type: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="职称类型")

    # ─── Personal info ───
    gender: Mapped[str | None] = mapped_column(String(8), nullable=True, comment="性别")
    native_place: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="籍贯")
    political_status: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="政治面貌")
    marital_status: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="婚姻状况")
    household_type: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="户籍类型")
    status_category: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="统计类别")

    # ─── Birth date (split as in Feishu) ───
    birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="出生年份")
    birth_month: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="出生月份")
    birth_day: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="出生日期")
    age: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="年龄（飞书公式）")

    # ─── Dates ───
    work_start_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="参加工作时间")
    factory_entry_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="进厂时间")
    livo_entry_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="入丽珠时间")
    hire_date: Mapped[date] = mapped_column(Date, nullable=False, comment="入职日期")
    graduation_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="毕业时间")

    # ─── Computed tenure (read-only mirrors of Feishu formulas) ───
    work_years: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="工作年限（飞书公式）")
    factory_tenure: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="厂龄（飞书公式）")
    company_tenure: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="司龄（飞书公式）")

    # ─── Education ───
    education: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="学历")
    classification: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="分类：全日制/非全日制")
    school: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="毕业学校")
    major: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="专业")

    # ─── ID & address ───
    id_card: Mapped[str | None] = mapped_column(String(18), nullable=True, comment="身份证号")
    id_card_expiry: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="身份证到期日")
    id_card_address: Mapped[str | None] = mapped_column(Text, nullable=True, comment="身份证地址|家庭地址")
    current_address: Mapped[str | None] = mapped_column(Text, nullable=True, comment="现住址")

    # ─── Contract ───
    contract_type: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="合同期限")
    contract_start_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="合同开始日期（第一次）")
    contract_end_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="合同结束日期（第一次）")
    contract_start_2: Mapped[date | None] = mapped_column(Date, nullable=True, comment="第二次合同起点")
    contract_end_2: Mapped[date | None] = mapped_column(Date, nullable=True, comment="第二次合同终止")
    contract_start_3: Mapped[date | None] = mapped_column(Date, nullable=True, comment="第三次合同起点")
    contract_end_3: Mapped[date | None] = mapped_column(Date, nullable=True, comment="第三次合同终止")
    contract_start_4: Mapped[date | None] = mapped_column(Date, nullable=True, comment="第四次合同起点")
    contract_end_4: Mapped[date | None] = mapped_column(Date, nullable=True, comment="第四次合同终止")

    # ─── Contact ───
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="手机")
    email: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="邮箱")
    emergency_contact_name: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="紧急联系人姓名")
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="紧急联系人电话")
    emergency_contact_relation: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="紧急联系人关系")

    # ─── Banking & training ───
    bank_account: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="银行卡号")
    training_id: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="培训档案编号")

    # ─── Work history & remarks ───
    transfer_history: Mapped[str | None] = mapped_column(Text, nullable=True, comment="异动（含曾经工作部门、岗位)")
    remarks: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True, comment="备注（多选）")

    # ─── Status ───
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="待审批",
        server_default="待审批",
        comment="状态: 在职, 离职, 试用期, 待审批",
    )

    # ─── Feishu sync metadata ───
    feishu_open_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="飞书 open_id")
    feishu_record_id: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="飞书多维表格 record_id")
    feishu_synced_at: Mapped[date | None] = mapped_column(Date, nullable=True, comment="上次飞书同步时间")


class DepartureRecord(BaseModel):
    """2026 离职台账（ticket #200）：人工录入，人员字段在保存时冻结。"""

    __tablename__ = "departure_records"
    __table_args__ = (
        Index("ix_departure_department_level1", "department_level1"),
        Index("ix_departure_leave_date", "leave_date"),
        Index("ix_departure_name", "name"),
        {"schema": "hr"},
    )

    person_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("hr.employee_profiles.id"),
        nullable=True,
        comment="员工档案 id（可选；不在档案中的人员可手工录入）",
    )

    # ─── 人员快照（选中人员时写入，之后冻结）───
    department_level1: Mapped[str] = mapped_column(String(64), nullable=False, comment="一级部门")
    department_level2: Mapped[str] = mapped_column(String(64), nullable=False, comment="二级部门")
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="姓名")
    gender: Mapped[str] = mapped_column(String(8), nullable=False, comment="性别")
    position: Mapped[str] = mapped_column(String(64), nullable=False, comment="岗位")
    hire_date: Mapped[date] = mapped_column(Date, nullable=False, comment="入职日期")
    education: Mapped[str] = mapped_column(String(16), nullable=False, comment="学历")
    age: Mapped[int] = mapped_column(Integer, nullable=False, comment="年龄")

    # ─── 录入字段 ───
    position_level: Mapped[str] = mapped_column(String(16), nullable=False, comment="岗位层级")
    personnel_identity: Mapped[str] = mapped_column(String(16), nullable=False, comment="人员身份")
    leave_date: Mapped[date] = mapped_column(Date, nullable=False, comment="离职日期")
    leave_category: Mapped[str] = mapped_column(String(16), nullable=False, comment="离职类别")
    leave_reason: Mapped[str] = mapped_column(String(255), nullable=False, comment="离职原因")
    tenure_years: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False, comment="司龄（年，保留一位小数）")
    group_classification: Mapped[str] = mapped_column(String(32), nullable=False, comment="集团月报表人员分类")


class TrainingLedger(BaseModel):
    __tablename__ = "training_ledgers"
    __table_args__ = (
        Index("ix_training_ledgers_employee_number", "employee_number"),
        Index("ix_training_ledgers_training_date", "training_date"),
        {"schema": "hr"},
    )

    employee_number: Mapped[str] = mapped_column(String(32), nullable=False, comment="工号")
    training_date: Mapped[date] = mapped_column(Date, nullable=False, comment="培训日期")
    training_subject: Mapped[str] = mapped_column(String(256), nullable=False, comment="培训课程/主题")
    training_method: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="培训方式")
    duration_hours: Mapped[float | None] = mapped_column(nullable=True, comment="课时")
    location: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="培训地点")
    trainer: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="培训单位/培训师")
    assessment_result: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="考核成绩")
    source_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="manual",
        server_default="manual",
        comment="来源: manual手动, notification培训通知关联",
    )
    source_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="来源ID")
    remarks: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="备注")
    ledger_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="event",
        server_default="event",
        comment="台账类型: event=事件台账, sop=SOP培训台账",
    )


class TrainingLedgerPage(BaseModel):
    """培训台账专属页面配置（动态菜单持久化）"""

    __tablename__ = "training_ledger_pages"
    __table_args__ = (
        Index(
            "ix_training_ledger_pages_employee_type",
            "employee_number",
            "ledger_type",
            unique=True,
        ),
        {"schema": "hr"},
    )

    employee_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, comment="工号")
    employee_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="员工姓名")
    ledger_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="event",
        server_default="event",
        comment="台账类型: event=事件台账, sop=SOP培训台账",
    )


class TrainingSpecialist(BaseModel):
    """培训专员配置 — 每个部门在每个厂区对应一个培训专员."""

    __tablename__ = "training_specialists"
    __table_args__ = (
        Index(
            "ix_training_specialists_department_factory",
            "department",
            "factory",
            unique=True,
        ),
        {"schema": "hr"},
    )

    department: Mapped[str] = mapped_column(String(64), nullable=False, comment="部门名称")
    employee_number: Mapped[str] = mapped_column(String(32), nullable=False, comment="培训专员工号")
    employee_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="培训专员姓名")
    factory: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        default="old",
        server_default="old",
        comment="厂区: old=旧厂, new=新厂",
    )
    feishu_open_id: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="飞书 user open_id")


class TrainingTeam(BaseModel):
    """自定义培训受训班组 — 替代培训场次中的受训部门选择."""

    __tablename__ = "training_teams"
    __table_args__ = {"schema": "hr"}

    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="班组名称")
    factory: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        default="old",
        server_default="old",
        comment="厂区: old=旧厂, new=新厂",
    )
    department: Mapped[str] = mapped_column(String(64), nullable=False, comment="所属部门")
    specialist_employee_number: Mapped[str] = mapped_column(String(32), nullable=False, comment="培训专员工号")
    specialist_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="培训专员姓名")
    employee_names: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True, comment="受训人员姓名列表")
    employee_numbers: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True, comment="受训人员工号列表")


class OnboardingRecord(BaseModel):
    """2026 入职台账（ticket #199）：全部字段手工录入，不再与飞书多维表格同步。"""

    __tablename__ = "onboarding_records"
    __table_args__ = (
        Index("ix_onboarding_department_level1", "department_level1"),
        Index("ix_onboarding_hire_date", "hire_date"),
        Index("ix_onboarding_name", "name"),
        {"schema": "hr"},
    )

    serial_no: Mapped[str] = mapped_column(String(32), nullable=False, comment="流水号")
    department_level1: Mapped[str] = mapped_column(String(64), nullable=False, comment="一级部门")
    department_level2: Mapped[str] = mapped_column(String(64), nullable=False, comment="二级部门")
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="姓名")
    position: Mapped[str] = mapped_column(String(64), nullable=False, comment="岗位")
    position_level: Mapped[str] = mapped_column(String(16), nullable=False, comment="岗位层级")
    personnel_identity: Mapped[str] = mapped_column(String(16), nullable=False, comment="人员身份")
    hire_date: Mapped[date] = mapped_column(Date, nullable=False, comment="入职日期")
    join_category: Mapped[str] = mapped_column(String(16), nullable=False, comment="入职类别")
    education: Mapped[str] = mapped_column(String(16), nullable=False, comment="学历")
    gender: Mapped[str] = mapped_column(String(8), nullable=False, comment="性别")
    age: Mapped[int] = mapped_column(Integer, nullable=False, comment="年龄")
    mobile: Mapped[str] = mapped_column(String(32), nullable=False, comment="手机号码")
    group_classification: Mapped[str] = mapped_column(String(32), nullable=False, comment="集团月报表人员分类")


class AnnualTrainingPlan(BaseModel):
    __tablename__ = "annual_training_plans"
    __table_args__ = (
        Index("ix_annual_training_plans_year", "year"),
        Index("ix_annual_training_plans_department", "department"),
        {"schema": "hr"},
    )

    year: Mapped[int] = mapped_column(Integer, nullable=False, comment="年度")
    department: Mapped[str] = mapped_column(String(64), nullable=False, comment="部门")
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="草稿",
        server_default="草稿",
        comment="状态: 草稿, 已确认",
    )

    items: Mapped[list["AnnualTrainingPlanItem"]] = relationship(
        "AnnualTrainingPlanItem",
        back_populates="plan",
        lazy="select",
        cascade="all, delete-orphan",
    )


class TrainingSession(BaseModel):
    """培训活动记录（按培训场次维度）"""

    __tablename__ = "training_sessions"
    __table_args__ = (
        Index("ix_training_sessions_department", "department"),
        Index("ix_training_sessions_training_date", "training_date"),
        Index("ix_training_sessions_status", "status"),
        {"schema": "hr"},
    )

    factory: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        default="old",
        server_default="old",
        comment="厂区: old=旧厂, new=新厂",
    )
    department: Mapped[str] = mapped_column(String(64), nullable=False, comment="主办部门")
    training_date: Mapped[date] = mapped_column(Date, nullable=False, comment="培训日期")
    subject: Mapped[str] = mapped_column(String(256), nullable=False, comment="培训主题")
    training_time_start: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="培训开始时间")
    training_time_end: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="培训结束时间")
    location: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="培训地点")
    trainer: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="培训师")
    training_method: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="培训方式")
    content: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="培训内容")
    trainee_departments: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True, comment="受训部门列表")
    employee_names: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True, comment="应出席受训人员姓名列表")
    employee_numbers: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True, comment="应出席受训人员工号列表")
    issuer_department: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="落款部门")
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="落款日期")
    remarks: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="备注")
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="draft",
        server_default="draft",
        comment="状态: draft草稿, notified已通知, selecting选择中, confirmed已确认, evaluated已评估, archived已归档",
    )
    select_task_token: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="飞书选择任务token（兼容旧单任务）"
    )
    select_tasks: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="多部门选择任务列表[{department, token, status, employee_names, employee_numbers}]",
    )


class AnnualTrainingPlanItem(BaseModel):
    __tablename__ = "annual_training_plan_items"
    __table_args__ = (
        Index("ix_annual_training_plan_items_plan_id", "plan_id"),
        {"schema": "hr"},
    )

    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("hr.annual_training_plans.id"),
        nullable=False,
        comment="年度计划ID",
    )
    month: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="月份")
    trainee_count: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="培训人数")
    duration_hours: Mapped[float | None] = mapped_column(nullable=True, comment="课时")
    content_and_textbook: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="培训内容及使用教材")
    target_audience: Mapped[str | None] = mapped_column(String(256), nullable=True, comment="培训对象")
    position_and_count: Mapped[str | None] = mapped_column(String(256), nullable=True, comment="参加岗位/参加人数")
    training_method: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="培训方式")
    training_hours: Mapped[float | None] = mapped_column(nullable=True, comment="培训学时")
    confirmer: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="确认者")
    confirm_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="确认日期")
    remarks: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="备注")
    tracking_status: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="培训跟踪: 完成, 未完成")
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="排序",
    )

    plan: Mapped["AnnualTrainingPlan"] = relationship("AnnualTrainingPlan", back_populates="items", lazy="select")


class Candidate(BaseModel):
    __tablename__ = "candidates"
    __table_args__ = (
        Index("ix_candidates_name", "name"),
        Index("ix_candidates_position", "position"),
        Index("ix_candidates_recommendation_level", "recommendation_level"),
        Index("ix_candidates_feishu_record_id", "feishu_record_id"),
        {"schema": "hr"},
    )

    # ─── Basic info ───
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="候选人姓名")
    position: Mapped[str] = mapped_column(String(64), nullable=False, comment="应聘职位名称")
    gender: Mapped[str | None] = mapped_column(String(8), nullable=True, comment="性别")

    # ─── Education ───
    school: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="学校名称")
    education: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="学历")
    major: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="专业")

    # ─── AI report ───
    match_report: Mapped[str | None] = mapped_column(Text, nullable=True, comment="候选人匹配度报告")

    # ─── Recommendation level ───
    recommendation_level: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="推荐等级")

    # ─── Resume attachments (JSON metadata from Feishu) ───
    resume_attachments: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True, comment="简历附件元数据"
    )

    # ─── Local resume file path (downloaded from Feishu during sync) ───
    resume_storage_path: Mapped[str | None] = mapped_column(String(256), nullable=True, comment="本地简历存储路径")

    # ─── Feishu sync metadata ───
    feishu_record_id: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="飞书多维表格 record_id")
    feishu_synced_at: Mapped[date | None] = mapped_column(Date, nullable=True, comment="上次飞书同步时间")
    feishu_sync_status: Mapped[str | None] = mapped_column(
        String(16), nullable=True, comment="飞书同步状态: synced/failed"
    )
    feishu_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True, comment="飞书同步失败原因")


class EmployeeProfile(BaseModel):
    """飞书通讯录人员镜像（ticket #198）。

    以飞书 open_id 为唯一键，保存员工档案页面展示的人员字段。同步只 upsert，
    不删除、不按"未返回"停用任何人；历史离职人员仍可作为台账的人员来源。
    不保存 employee_id、subscription_ids、leader_id 以及内嵌的 department 对象。
    """

    __tablename__ = "employee_profiles"
    __table_args__ = (
        UniqueConstraint("open_id", name="uq_hr_employee_profiles_open_id"),
        Index("ix_hr_employee_profiles_name", "name"),
        Index("ix_hr_employee_profiles_employee_no", "employee_no"),
        Index("ix_hr_employee_profiles_staff_status", "staff_status"),
        {"schema": "hr"},
    )

    open_id: Mapped[str] = mapped_column(String(128), nullable=False, comment="飞书 open_id（唯一键）")
    name: Mapped[str] = mapped_column(String(100), nullable=False, server_default="", comment="姓名")
    mobile: Mapped[str] = mapped_column(String(32), nullable=False, server_default="", comment="手机号")
    email: Mapped[str] = mapped_column(String(255), nullable=False, server_default="", comment="邮箱")
    enterprise_email: Mapped[str] = mapped_column(String(255), nullable=False, server_default="", comment="企业邮箱")
    email_aliases: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True, comment="企业邮箱别名列表")
    gender: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="性别（飞书枚举：1 男 / 2 女）")
    education: Mapped[str] = mapped_column(String(16), nullable=False, server_default="", comment="学历")
    age: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="年龄")
    description: Mapped[str] = mapped_column(Text, nullable=False, server_default="", comment="个性签名")
    avatar_72: Mapped[str] = mapped_column(String(1024), nullable=False, server_default="", comment="头像 72px URL")
    avatar_240: Mapped[str] = mapped_column(String(1024), nullable=False, server_default="", comment="头像 240px URL")
    avatar_640: Mapped[str] = mapped_column(String(1024), nullable=False, server_default="", comment="头像 640px URL")
    avatar_origin: Mapped[str] = mapped_column(String(1024), nullable=False, server_default="", comment="原始头像 URL")
    background_image: Mapped[str] = mapped_column(String(1024), nullable=False, server_default="", comment="背景图 URL")
    geo_name: Mapped[str] = mapped_column(String(64), nullable=False, server_default="", comment="地理名称")
    active_status: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="账号激活状态（飞书枚举）")
    is_resigned: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", comment="是否离职")
    resign_time: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default="", comment="离职时间（飞书原始字符串）"
    )
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", comment="是否普通管理员")
    is_primary_admin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", comment="是否超级管理员"
    )
    data_source: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="飞书数据来源枚举")
    employee_no: Mapped[str] = mapped_column(String(64), nullable=False, server_default="", comment="工号")
    job_title_id: Mapped[str] = mapped_column(String(128), nullable=False, server_default="", comment="职务 ID")
    job_title_name: Mapped[str] = mapped_column(String(200), nullable=False, server_default="", comment="职务名称")
    hire_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="入职日期")
    employment_type: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="员工类型（飞书枚举）")
    staff_status: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="人事状态（飞书枚举）")
    work_country_or_region: Mapped[str] = mapped_column(
        String(128), nullable=False, server_default="", comment="工作国家/地区"
    )
    work_place_id: Mapped[str] = mapped_column(String(128), nullable=False, server_default="", comment="工作地点 ID")
    work_place_name: Mapped[str] = mapped_column(String(200), nullable=False, server_default="", comment="工作地点名称")
    work_station: Mapped[str] = mapped_column(String(200), nullable=False, server_default="", comment="工位")
    extension_number: Mapped[str] = mapped_column(String(64), nullable=False, server_default="", comment="分机号")
    dotted_line_leader_ids: Mapped[list[str] | None] = mapped_column(
        JSONB, nullable=True, comment="虚线上级 open_id 列表"
    )
    resign_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="离职日期")
    resign_type: Mapped[str] = mapped_column(String(100), nullable=False, server_default="", comment="离职类型")
    resign_reason: Mapped[str] = mapped_column(String(255), nullable=False, server_default="", comment="离职原因")
    resign_remark: Mapped[str] = mapped_column(Text, nullable=False, server_default="", comment="离职备注")
    positions: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True, comment="职位列表 [{id, name}]"
    )
    job_level_id: Mapped[str] = mapped_column(String(128), nullable=False, server_default="", comment="职级 ID")
    job_level_name: Mapped[str] = mapped_column(String(200), nullable=False, server_default="", comment="职级名称")
    job_family_id: Mapped[str] = mapped_column(String(128), nullable=False, server_default="", comment="序列（职族）ID")
    job_family_name: Mapped[str] = mapped_column(
        String(200), nullable=False, server_default="", comment="序列（职族）名称"
    )
    department_ids: Mapped[list[str] | None] = mapped_column(
        JSONB, nullable=True, comment="所属部门 open_department_id 列表"
    )
    department_names: Mapped[list[str] | None] = mapped_column(
        JSONB, nullable=True, comment="所属部门名称列表，与 department_ids 对齐"
    )
    department_path: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True, comment="主部门路径，根 → 一级 → 二级，id + 名称"
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="最近一次目录同步时间"
    )


class PrejobTrainingPlanTemplate(BaseModel):
    """岗前培训计划模板 — 按部门+厂区保存培训计划内容。"""

    __tablename__ = "prejob_training_plan_templates"
    __table_args__ = (
        Index(
            "ix_prejob_template_dept_factory",
            "department",
            "factory",
            unique=True,
        ),
        {"schema": "hr"},
    )

    department: Mapped[str] = mapped_column(String(64), nullable=False, comment="部门名称")
    factory: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        default="old",
        server_default="old",
        comment="厂区: old=旧厂, new=新厂",
    )
    items: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'"),
        comment="培训计划条目列表 [{seq, content, deadline, trainer}]",
    )


class SystemSetting(Base):
    """`hr.system_settings`：配置键值表（迁移 0087 建表）。

    物理表以 `key` 为主键、没有 `BaseModel` 的审计列，因此不继承 `BaseModel`。
    代码里仍用原生 SQL 读写，模型只用于让 `alembic check` / `autogenerate` 感知这张表。
    """

    __tablename__ = "system_settings"
    __table_args__ = {"schema": "hr"}

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text, server_default=text(""))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
