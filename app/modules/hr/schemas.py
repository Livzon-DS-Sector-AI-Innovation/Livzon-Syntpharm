"""HR business request and response schemas live here."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ─── Department Schemas ───

class DepartmentBase(BaseModel):
    name: str = Field(..., max_length=64, description="部门名称")
    code: str = Field(..., max_length=32, description="部门编码")
    description: str | None = Field(None, max_length=256, description="部门描述")
    is_production: bool = Field(False, description="是否生产部门")
    production_start_time: str | None = Field(None, max_length=8, description="生产班次开始时间(HH:MM)")
    production_end_time: str | None = Field(None, max_length=8, description="生产班次结束时间(HH:MM)")


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: str | None = Field(None, max_length=64)
    code: str | None = Field(None, max_length=32)
    description: str | None = Field(None, max_length=256)
    is_production: bool | None = Field(None, description="是否生产部门")
    production_start_time: str | None = Field(None, max_length=8)
    production_end_time: str | None = Field(None, max_length=8)


class DepartmentResponse(DepartmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ─── Team Schemas ───

class TeamBase(BaseModel):
    name: str = Field(..., max_length=64, description="班组名称")
    code: str | None = Field(None, max_length=32, description="班组编码")
    description: str | None = Field(None, max_length=256, description="班组描述")
    department_id: UUID = Field(..., description="所属部门ID")


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    name: str | None = Field(None, max_length=64)
    code: str | None = Field(None, max_length=32)
    description: str | None = Field(None, max_length=256)
    department_id: UUID | None = Field(None)


class TeamResponse(TeamBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    department: DepartmentResponse | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ─── Employee Schemas ───

class EmployeeBase(BaseModel):
    # Core
    employee_number: str = Field(..., max_length=32, description="工号")
    name: str = Field(..., max_length=64, description="姓名")
    domain_account: str | None = Field(None, max_length=64, description="域账号")

    # Department & job
    department: str = Field(..., max_length=64, description="部门")
    team: str | None = Field(None, max_length=64, description="班组")
    position: str = Field(..., max_length=64, description="职位")
    job_category: str | None = Field(None, max_length=32, description="职类")
    level: str | None = Field(None, max_length=32, description="级别")
    position_level: str | None = Field(None, max_length=16, description="职位级别(自动判定): 普通员工/工程师级/主管级")

    # Qualifications
    qualifications: list[str] | None = Field(None, description="职称／职业资格")
    qualification_type: str | None = Field(None, max_length=32, description="职称类型")

    # Personal
    gender: str | None = Field(None, max_length=8, description="性别")
    native_place: str | None = Field(None, max_length=64, description="籍贯")
    political_status: str | None = Field(None, max_length=32, description="政治面貌")
    marital_status: str | None = Field(None, max_length=16, description="婚姻状况")
    household_type: str | None = Field(None, max_length=16, description="户籍类型")
    status_category: str | None = Field(None, max_length=32, description="统计类别")

    # Birth
    birth_year: int | None = Field(None, description="出生年份")
    birth_month: int | None = Field(None, description="出生月份")
    birth_day: int | None = Field(None, description="出生日期")
    age: int | None = Field(None, description="年龄")

    # Dates
    work_start_date: date | None = Field(None, description="参加工作时间")
    factory_entry_date: date | None = Field(None, description="进厂时间")
    livo_entry_date: date | None = Field(None, description="入丽珠时间")
    hire_date: date = Field(..., description="入职日期")
    graduation_date: date | None = Field(None, description="毕业时间")

    # Computed
    work_years: int | None = Field(None, description="工作年限")
    factory_tenure: str | None = Field(None, max_length=32, description="厂龄")
    company_tenure: str | None = Field(None, max_length=32, description="司龄")

    # Education
    education: str | None = Field(None, max_length=16, description="学历")
    classification: str | None = Field(None, max_length=16, description="分类")
    school: str | None = Field(None, max_length=128, description="毕业学校")
    major: str | None = Field(None, max_length=64, description="专业")

    # ID & address
    id_card: str | None = Field(None, max_length=18, description="身份证号")
    id_card_expiry: str | None = Field(None, max_length=32, description="身份证到期日")
    id_card_address: str | None = Field(None, description="身份证地址|家庭地址")
    current_address: str | None = Field(None, description="现住址")

    # Contract
    contract_type: str | None = Field(None, max_length=32, description="合同期限")
    contract_start_date: date | None = Field(None, description="合同开始日期")
    contract_end_date: date | None = Field(None, description="合同结束日期")
    contract_start_2: date | None = Field(None, description="第二次合同起点")
    contract_end_2: date | None = Field(None, description="第二次合同终止")
    contract_start_3: date | None = Field(None, description="第三次合同起点")
    contract_end_3: date | None = Field(None, description="第三次合同终止")
    contract_start_4: date | None = Field(None, description="第四次合同起点")
    contract_end_4: date | None = Field(None, description="第四次合同终止")

    # Contact
    phone: str | None = Field(None, max_length=32, description="手机")
    email: str | None = Field(None, max_length=128, description="邮箱")
    emergency_contact_name: str | None = Field(
        None, max_length=64, description="紧急联系人姓名"
    )
    emergency_contact_phone: str | None = Field(
        None, max_length=32, description="紧急联系人电话"
    )
    emergency_contact_relation: str | None = Field(
        None, max_length=32, description="紧急联系人关系"
    )

    # Banking & training
    bank_account: str | None = Field(None, max_length=32, description="银行卡号")
    training_id: str | None = Field(None, max_length=32, description="培训档案编号")

    # Other
    transfer_history: str | None = Field(None, description="异动记录")
    remarks: list[str] | None = Field(None, description="备注")
    status: str = Field("待审批", max_length=16, description="状态")


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    model_config = ConfigDict(extra="allow")

    employee_number: str | None = Field(None, max_length=32)
    name: str | None = Field(None, max_length=64)
    domain_account: str | None = Field(None, max_length=64)
    department: str | None = Field(None, max_length=64)
    team: str | None = Field(None, max_length=64)
    position: str | None = Field(None, max_length=64)
    job_category: str | None = Field(None, max_length=32)
    level: str | None = Field(None, max_length=32)
    position_level: str | None = Field(None, max_length=16, description="职位级别")
    qualifications: list[str] | None = Field(None)
    qualification_type: str | None = Field(None, max_length=32)
    gender: str | None = Field(None, max_length=8)
    native_place: str | None = Field(None, max_length=64)
    political_status: str | None = Field(None, max_length=32)
    marital_status: str | None = Field(None, max_length=16)
    household_type: str | None = Field(None, max_length=16)
    status_category: str | None = Field(None, max_length=32)
    birth_year: int | None = Field(None)
    birth_month: int | None = Field(None)
    birth_day: int | None = Field(None)
    age: int | None = Field(None)
    work_start_date: date | None = Field(None)
    factory_entry_date: date | None = Field(None)
    livo_entry_date: date | None = Field(None)
    hire_date: date | None = Field(None)
    graduation_date: date | None = Field(None)
    work_years: int | None = Field(None)
    factory_tenure: str | None = Field(None, max_length=32)
    company_tenure: str | None = Field(None, max_length=32)
    education: str | None = Field(None, max_length=16)
    classification: str | None = Field(None, max_length=16)
    school: str | None = Field(None, max_length=128)
    major: str | None = Field(None, max_length=64)
    id_card: str | None = Field(None, max_length=18)
    id_card_expiry: str | None = Field(None, max_length=32)
    id_card_address: str | None = Field(None)
    current_address: str | None = Field(None)
    contract_type: str | None = Field(None, max_length=32)
    contract_start_date: date | None = Field(None)
    contract_end_date: date | None = Field(None)
    contract_start_2: date | None = Field(None)
    contract_end_2: date | None = Field(None)
    contract_start_3: date | None = Field(None)
    contract_end_3: date | None = Field(None)
    contract_start_4: date | None = Field(None)
    contract_end_4: date | None = Field(None)
    phone: str | None = Field(None, max_length=32)
    email: str | None = Field(None, max_length=128)
    emergency_contact_name: str | None = Field(None, max_length=64)
    emergency_contact_phone: str | None = Field(None, max_length=32)
    emergency_contact_relation: str | None = Field(None, max_length=32)
    bank_account: str | None = Field(None, max_length=32)
    training_id: str | None = Field(None, max_length=32)
    transfer_history: str | None = Field(None)
    remarks: list[str] | None = Field(None)
    status: str | None = Field(None, max_length=16)


class EmployeeResponse(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    feishu_open_id: str | None = None
    feishu_record_id: str | None = None
    feishu_synced_at: date | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SyncStatusResponse(BaseModel):
    local_total: int
    feishu_total: int
    synced_count: int
    unsynced_count: int
    conflict_count: int
    last_sync_at: datetime | None = None


class TrainingSignInSheetInput(BaseModel):
    training_date: date = Field(..., description="培训日期")
    training_time_start: str | None = Field(None, max_length=32, description="培训开始时间")
    training_time_end: str | None = Field(None, max_length=32, description="培训结束时间")
    department: str = Field(..., max_length=256, description="受训部门")
    training_subject: str | None = Field(None, max_length=128, description="培训主题")
    topic: str = Field(..., max_length=256, description="培训题目或内容概要")
    instructor: str | None = Field(None, max_length=64, description="授课人")
    location: str | None = Field(None, max_length=128, description="培训地点")
    training_method: str | None = Field(None, max_length=32, description="培训方式")
    employee_names: list[str] = Field(default_factory=list, description="应出席受训人员姓名列表")
    remarks: str | None = Field(None, max_length=512, description="备注")


class TrainingNotificationInput(BaseModel):
    department: str = Field(..., max_length=64, description="主办部门")
    training_date: date = Field(..., description="培训日期")
    subject: str = Field(..., max_length=128, description="培训主题")
    training_time_start: str | None = Field(None, max_length=32, description="培训开始时间")
    training_time_end: str | None = Field(None, max_length=32, description="培训结束时间")
    location: str | None = Field(None, max_length=128, description="培训地点")
    trainer: str | None = Field(None, max_length=64, description="培训师")
    content: str | None = Field(None, max_length=512, description="培训内容")
    trainee_names: list[str] = Field(default_factory=list, description="培训人员姓名列表")
    issuer_department: str | None = Field(None, max_length=64, description="落款部门")
    issue_date: date | None = Field(None, description="落款日期")


class TrainingNotifyInput(BaseModel):
    """Send training notification via Feishu IM."""

    employee_numbers: list[str] = Field(..., description="受训人员工号列表")
    department: str | None = Field(None, max_length=64, description="主办部门")
    subject: str = Field(..., max_length=128, description="培训主题")
    training_date: date = Field(..., description="培训日期")
    training_time_start: str | None = Field(None, max_length=32, description="培训开始时间")
    training_time_end: str | None = Field(None, max_length=32, description="培训结束时间")
    location: str | None = Field(None, max_length=128, description="培训地点")
    trainer: str | None = Field(None, max_length=64, description="培训师")
    content: str | None = Field(None, max_length=512, description="培训内容")
    training_method: str | None = Field(None, max_length=32, description="培训方式")
    issuer_department: str | None = Field(None, max_length=64, description="落款部门")
    issue_date: date | None = Field(None, description="落款日期")
    factory: str | None = Field(None, max_length=8, description="厂区: old=旧厂, new=新厂")


class TrainingSelectTaskCreate(BaseModel):
    """Create a temporary task for selecting trainees via Feishu."""

    department: str = Field(..., max_length=64, description="主办部门")
    training_date: str = Field(..., max_length=32, description="培训日期")
    subject: str = Field(..., max_length=128, description="培训主题")
    training_time_start: str | None = Field(None, max_length=32, description="培训开始时间")
    training_time_end: str | None = Field(None, max_length=32, description="培训结束时间")
    location: str | None = Field(None, max_length=128, description="培训地点")
    trainer: str | None = Field(None, max_length=64, description="培训师")
    content: str | None = Field(None, max_length=512, description="培训内容")
    training_method: str | None = Field(None, max_length=32, description="培训方式")
    issuer_department: str | None = Field(None, max_length=64, description="落款部门")
    issue_date: str | None = Field(None, max_length=32, description="落款日期")
    factory: str | None = Field(None, max_length=8, description="厂区: old=旧厂, new=新厂")


class TrainingSelectTaskSubmit(BaseModel):
    """Submit selected trainees for a training task."""

    employee_numbers: list[str] = Field(..., description="选择的受训人员工号列表")
    employee_names: list[str] | None = Field(None, description="选择的受训人员姓名列表")


class TrainingEvaluationInput(BaseModel):
    subject: str = Field(..., max_length=128, description="培训主题")
    training_date: date | None = Field(None, description="培训日期")
    training_time_start: str | None = Field(None, max_length=32, description="培训开始时间")
    training_time_end: str | None = Field(None, max_length=32, description="培训结束时间")
    duration_hours: float | None = Field(None, description="学时")
    training_method: str | None = Field(None, max_length=32, description="培训方式")
    is_exam: bool = Field(False, description="是否考试")
    trainer_type: str | None = Field(None, max_length=64, description="培训人员类型")
    trainer: str | None = Field(None, max_length=64, description="授课人")
    department_personnel: str | None = Field(None, max_length=256, description="部门/班组/人员")
    expected_count: int | None = Field(None, description="应出席人数")
    actual_count: int | None = Field(None, description="实际出席人数")
    absent_count: int | None = Field(None, description="缺席人数")
    textbook: str | None = Field(None, max_length=256, description="培训教材")
    makeup_training: bool | None = Field(None, description="是否补课")
    assessment_method: str | None = Field(None, max_length=32, description="考核方式")
    pass_count: int | None = Field(None, description="合格人数")
    fail_count: int | None = Field(None, description="不合格人数")
    absent_exam_count: int | None = Field(None, description="缺考人数")
    absent_exam_handling: str | None = Field(None, max_length=512, description="缺考人员处理方式和原因")
    excellent_count: int | None = Field(None, description="优秀人数")
    qualified_count: int | None = Field(None, description="合格人数")
    unqualified_count: int | None = Field(None, description="不合格人数")
    evaluation_conclusion: str | None = Field(None, max_length=1024, description="培训效果评估及结论")
    organizer: str | None = Field(None, max_length=64, description="培训组织人")
    organizer_date: date | None = Field(None, description="组织日期")
    remarks: str | None = Field(None, max_length=512, description="备注")
    employee_names: list[str] | None = Field(None, description="受训人员姓名列表")


class OnboardingEvaluationInput(BaseModel):
    employee_name: str = Field(..., max_length=64, description="员工姓名")
    employee_number: str | None = Field(None, max_length=32, description="工作卡号")
    gender: str | None = Field(None, max_length=8, description="性别")
    department_position: str | None = Field(None, max_length=128, description="所在部门/岗位")
    hire_date: date | None = Field(None, description="入厂时间")
    training_period: str | None = Field(None, max_length=64, description="培训/考核期")
    regularization_date: date | None = Field(None, description="转正时间")
    assessment_contents: list[str] = Field(default_factory=list, description="上岗培训期内考核内容")
    comprehensive_comment: str | None = Field(None, max_length=1024, description="培训/考核期综合评语")
    is_qualified: bool | None = Field(None, description="是否同意上岗")
    assigned_position: str | None = Field(None, max_length=64, description="担任岗位")
    assessment_method: str | None = Field(None, max_length=32, description="考核方式")
    dept_manager_signature: str | None = Field(None, max_length=64, description="部门负责人签名")
    signature_date: date | None = Field(None, description="签名日期")
    remarks: str | None = Field(None, max_length=512, description="备注")
    dept_manager_agree: bool | None = Field(None, description="部门负责人是否同意")
    hr_manager_agree: bool | None = Field(None, description="人事行政部负责人是否同意")
    qa_manager_agree: bool | None = Field(None, description="质量管理负责人是否同意")
    dept_manager: str | None = Field(None, max_length=64, description="部门负责人")
    hr_manager: str | None = Field(None, max_length=64, description="人事行政部负责人")
    qa_manager: str | None = Field(None, max_length=64, description="质量管理负责人")
    approval_date: date | None = Field(None, description="审批日期")


# ─── OffboardingRecord Schemas ───

class OffboardingRecordBase(BaseModel):
    employee_id: UUID = Field(..., description="员工ID")
    offboarding_date: date = Field(..., description="离职日期")
    offboarding_type: str = Field("辞职", max_length=16, description="离职类型")
    reason: str | None = Field(None, max_length=512, description="离职原因")
    handover_status: str = Field("待交接", max_length=16, description="交接状态")
    notes: str | None = Field(None, max_length=512, description="备注")


class OffboardingRecordCreate(OffboardingRecordBase):
    pass


class OffboardingRecordUpdate(BaseModel):
    employee_id: UUID | None = Field(None)
    offboarding_date: date | None = Field(None)
    offboarding_type: str | None = Field(None, max_length=16)
    reason: str | None = Field(None, max_length=512)
    handover_status: str | None = Field(None, max_length=16)
    notes: str | None = Field(None, max_length=512)


class OffboardingRecordResponse(OffboardingRecordBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee: EmployeeResponse | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ─── DepartureRecord Schemas ───

class DepartureRecordBase(BaseModel):
    # Basic
    name: str = Field(..., max_length=64, description="姓名")
    department: str = Field(..., max_length=64, description="部门")
    team: str | None = Field(None, max_length=64, description="班组")
    position: str = Field(..., max_length=64, description="职位")
    job_category: str | None = Field(None, max_length=64, description="职类")
    gender: str | None = Field(None, max_length=8, description="性别")
    status_category: str | None = Field(None, max_length=64, description="统计类别")

    # Dates
    livo_entry_date: date | None = Field(None, description="入丽珠时间")
    factory_entry_date: date | None = Field(None, description="进厂时间")
    work_start_date: date | None = Field(None, description="参加工作时间")
    offboarding_date: date | None = Field(None, description="离职日期")
    company_tenure_at_leave: str | None = Field(None, max_length=64, description="离职时司龄")

    # Education
    education: str | None = Field(None, max_length=16, description="学历")
    school: str | None = Field(None, max_length=128, description="毕业学校")
    major: str | None = Field(None, max_length=64, description="专业")
    classification: str | None = Field(None, max_length=16, description="分类")

    # Personal
    id_card: str | None = Field(None, max_length=18, description="身份证号")
    native_place: str | None = Field(None, max_length=64, description="籍贯")
    household_type: str | None = Field(None, max_length=128, description="户籍类型")
    marital_status: str | None = Field(None, max_length=32, description="婚姻状况")
    political_status: str | None = Field(None, max_length=64, description="政治面貌")

    # Contact
    phone: str | None = Field(None, max_length=32, description="手机")
    emergency_contact_phone: str | None = Field(None, max_length=32, description="紧急联系人电话")
    emergency_contact_relation: str | None = Field(None, max_length=64, description="紧急联系人|关系")
    bank_account: str | None = Field(None, max_length=128, description="银行卡号")

    # Contract
    contract_type: str | None = Field(None, max_length=64, description="合同期限")

    # Work history
    transfer_history: str | None = Field(None, description="异动记录")

    # Offboarding specific
    offboarding_type: str = Field("辞职", max_length=16, description="离职类型")
    offboarding_reason: list[str] | None = Field(None, description="离职原因")
    offboarding_reason_2: list[str] | None = Field(None, description="离职原因2")
    offboarding_remarks: list[str] | None = Field(None, description="离职备注")

    # Other
    remarks: str | None = Field(None, description="备注")


class DepartureRecordCreate(DepartureRecordBase):
    pass


class DepartureRecordUpdate(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str | None = Field(None, max_length=64)
    department: str | None = Field(None, max_length=64)
    team: str | None = Field(None, max_length=64)
    position: str | None = Field(None, max_length=64)
    job_category: str | None = Field(None, max_length=32)
    gender: str | None = Field(None, max_length=8)
    status_category: str | None = Field(None, max_length=32)
    livo_entry_date: date | None = Field(None)
    factory_entry_date: date | None = Field(None)
    work_start_date: date | None = Field(None)
    offboarding_date: date | None = Field(None)
    company_tenure_at_leave: str | None = Field(None, max_length=32)
    education: str | None = Field(None, max_length=16)
    school: str | None = Field(None, max_length=128)
    major: str | None = Field(None, max_length=64)
    classification: str | None = Field(None, max_length=16)
    id_card: str | None = Field(None, max_length=18)
    native_place: str | None = Field(None, max_length=64)
    household_type: str | None = Field(None, max_length=16)
    marital_status: str | None = Field(None, max_length=16)
    political_status: str | None = Field(None, max_length=32)
    phone: str | None = Field(None, max_length=32)
    emergency_contact_phone: str | None = Field(None, max_length=32)
    emergency_contact_relation: str | None = Field(None, max_length=32)
    bank_account: str | None = Field(None, max_length=32)
    contract_type: str | None = Field(None, max_length=32)
    transfer_history: str | None = Field(None)
    offboarding_type: str | None = Field(None, max_length=16)
    offboarding_reason: list[str] | None = Field(None)
    offboarding_reason_2: list[str] | None = Field(None)
    offboarding_remarks: list[str] | None = Field(None)
    remarks: list[str] | None = Field(None)


class DepartureRecordResponse(DepartureRecordBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    feishu_record_id: str | None = None
    feishu_synced_at: date | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ─── OnboardingRecord Schemas ───

class OnboardingRecordBase(BaseModel):
    # Core
    seq_number: int | None = Field(None, description="编号")
    employee_number: str = Field(..., max_length=32, description="工号")
    name: str = Field(..., max_length=64, description="姓名")
    domain_account: str | None = Field(None, max_length=64, description="域账号")

    # Department & job
    department: str = Field(..., max_length=64, description="部门")
    team: str | None = Field(None, max_length=64, description="班组")
    position: str = Field(..., max_length=64, description="岗位")
    job_category: str | None = Field(None, max_length=32, description="职类")
    status_category: str | None = Field(None, max_length=32, description="统计类别")

    # Employment status
    is_employed: str | None = Field(None, max_length=8, description="是否在职")

    # Dates
    hire_date: date = Field(..., description="入职时间")
    factory_entry_date: date | None = Field(None, description="进厂时间")
    livo_entry_date: date | None = Field(None, description="入丽珠时间")
    work_start_date: date | None = Field(None, description="参加工作时间")
    graduation_date: date | None = Field(None, description="毕业时间")
    birth_month: int | None = Field(None, description="出生月份")
    birth_day: int | None = Field(None, description="出生日期")

    # Contract
    contract_type: str | None = Field(None, max_length=32, description="合同期限")
    contract_start_date: date | None = Field(None, description="第一次合同起点")
    contract_end_date: date | None = Field(None, description="第一次合同终止")
    contract_start_2: date | None = Field(None, description="第二次合同起点")
    contract_end_2: date | None = Field(None, description="第二次合同终止")
    contract_start_3: date | None = Field(None, description="第三次合同起点")
    contract_end_3: date | None = Field(None, description="第三次合同终止")
    contract_start_4: date | None = Field(None, description="第四次合同起点")
    contract_end_4: date | None = Field(None, description="第四次合同终止")

    # Computed
    age: int | None = Field(None, description="年龄")
    work_years: int | None = Field(None, description="工作年限")
    factory_tenure: str | None = Field(None, max_length=32, description="厂龄")
    company_tenure: str | None = Field(None, max_length=32, description="司龄")
    hire_month: str | None = Field(None, max_length=16, description="入职月份")

    # Education
    school: str | None = Field(None, max_length=128, description="毕业学校")
    education: str | None = Field(None, max_length=16, description="学历")
    major: str | None = Field(None, max_length=64, description="专业")
    classification: str | None = Field(None, max_length=16, description="分类")

    # Personal
    id_card: str | None = Field(None, max_length=18, description="身份证号")
    id_card_expiry: str | None = Field(None, max_length=32, description="身份证到期日")
    id_card_address: str | None = Field(None, description="身份证地址|家庭地址")
    current_address: str | None = Field(None, description="现住址")
    marital_status: str | None = Field(None, max_length=16, description="婚姻状况")
    household_type: str | None = Field(None, max_length=16, description="户籍类型")
    political_status: str | None = Field(None, max_length=32, description="政治面貌")

    # Contact
    phone: str | None = Field(None, max_length=32, description="手机")
    email: str | None = Field(None, max_length=128, description="邮箱")
    emergency_contact_phone: str | None = Field(None, max_length=32, description="紧急联系人电话")
    emergency_contact_relation: str | None = Field(None, max_length=32, description="紧急联系人|关系")

    # Banking
    bank_account: str | None = Field(None, max_length=32, description="银行卡号")
    bank_account_location: str | None = Field(None, max_length=32, description="银行卡开户地")

    # Other
    training_id: str | None = Field(None, max_length=32, description="培训档案编号")
    transfer_history: str | None = Field(None, description="异动记录")
    remarks: list[str] | None = Field(None, description="备注")


class OnboardingRecordCreate(OnboardingRecordBase):
    pass


class OnboardingRecordUpdate(BaseModel):
    model_config = ConfigDict(extra="allow")

    seq_number: int | None = Field(None)
    employee_number: str | None = Field(None, max_length=32)
    name: str | None = Field(None, max_length=64)
    domain_account: str | None = Field(None, max_length=64)
    department: str | None = Field(None, max_length=64)
    team: str | None = Field(None, max_length=64)
    position: str | None = Field(None, max_length=64)
    job_category: str | None = Field(None, max_length=32)
    status_category: str | None = Field(None, max_length=32)
    is_employed: str | None = Field(None, max_length=8)
    hire_date: date | None = Field(None)
    factory_entry_date: date | None = Field(None)
    livo_entry_date: date | None = Field(None)
    work_start_date: date | None = Field(None)
    graduation_date: date | None = Field(None)
    birth_month: int | None = Field(None)
    birth_day: int | None = Field(None)
    contract_type: str | None = Field(None, max_length=32)
    contract_start_date: date | None = Field(None)
    contract_end_date: date | None = Field(None)
    contract_start_2: date | None = Field(None)
    contract_end_2: date | None = Field(None)
    contract_start_3: date | None = Field(None)
    contract_end_3: date | None = Field(None)
    contract_start_4: date | None = Field(None)
    contract_end_4: date | None = Field(None)
    age: int | None = Field(None)
    work_years: int | None = Field(None)
    factory_tenure: str | None = Field(None, max_length=32)
    company_tenure: str | None = Field(None, max_length=32)
    hire_month: str | None = Field(None, max_length=16)
    school: str | None = Field(None, max_length=128)
    education: str | None = Field(None, max_length=16)
    major: str | None = Field(None, max_length=64)
    classification: str | None = Field(None, max_length=16)
    id_card: str | None = Field(None, max_length=18)
    id_card_expiry: str | None = Field(None, max_length=32)
    id_card_address: str | None = Field(None)
    current_address: str | None = Field(None)
    marital_status: str | None = Field(None, max_length=16)
    household_type: str | None = Field(None, max_length=16)
    political_status: str | None = Field(None, max_length=32)
    phone: str | None = Field(None, max_length=32)
    email: str | None = Field(None, max_length=128)
    emergency_contact_phone: str | None = Field(None, max_length=32)
    emergency_contact_relation: str | None = Field(None, max_length=32)
    bank_account: str | None = Field(None, max_length=32)
    bank_account_location: str | None = Field(None, max_length=32)
    training_id: str | None = Field(None, max_length=32)
    transfer_history: str | None = Field(None)
    remarks: list[str] | None = Field(None)


class OnboardingRecordResponse(OnboardingRecordBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    feishu_record_id: str | None = None
    feishu_synced_at: date | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ─── TrainingLedger Schemas ───

class TrainingLedgerBase(BaseModel):
    employee_number: str = Field(..., max_length=32, description="工号")
    training_date: date = Field(..., description="培训日期")
    training_subject: str = Field(..., max_length=256, description="培训课程/主题")
    training_method: str | None = Field(None, max_length=32, description="培训方式")
    duration_hours: float | None = Field(None, description="课时")
    location: str | None = Field(None, max_length=128, description="培训地点")
    trainer: str | None = Field(None, max_length=128, description="培训单位/培训师")
    assessment_result: str | None = Field(None, max_length=16, description="考核成绩")
    source_type: str = Field("manual", max_length=16, description="来源: manual, notification")
    source_id: str | None = Field(None, max_length=64, description="来源ID")
    remarks: str | None = Field(None, max_length=512, description="备注")
    ledger_type: str = Field("event", max_length=16, description="台账类型: event=事件台账, sop=SOP培训台账")


class TrainingLedgerCreate(TrainingLedgerBase):
    pass


class TrainingLedgerUpdate(BaseModel):
    model_config = ConfigDict(extra="allow")

    employee_number: str | None = Field(None, max_length=32)
    training_date: date | None = Field(None)
    training_subject: str | None = Field(None, max_length=256)
    training_method: str | None = Field(None, max_length=32)
    duration_hours: float | None = Field(None)
    location: str | None = Field(None, max_length=128)
    trainer: str | None = Field(None, max_length=128)
    assessment_result: str | None = Field(None, max_length=16)
    source_type: str | None = Field(None, max_length=16)
    source_id: str | None = Field(None, max_length=64)
    remarks: str | None = Field(None, max_length=512)


class TrainingLedgerResponse(TrainingLedgerBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TrainingLedgerListResponse(BaseModel):
    code: int
    message: str
    data: list[TrainingLedgerResponse]
    meta: dict | None = None


class TrainingSessionBase(BaseModel):
    factory: str = Field("old", max_length=8, description="厂区: old=旧厂, new=新厂")
    department: str = Field(..., max_length=64, description="主办部门")
    training_date: date = Field(..., description="培训日期")
    subject: str = Field(..., max_length=256, description="培训主题")
    training_time_start: str | None = Field(None, max_length=32, description="培训开始时间")
    training_time_end: str | None = Field(None, max_length=32, description="培训结束时间")
    location: str | None = Field(None, max_length=128, description="培训地点")
    trainer: str | None = Field(None, max_length=128, description="培训师")
    training_method: str | None = Field(None, max_length=32, description="培训方式")
    content: str | None = Field(None, max_length=512, description="培训内容")
    trainee_departments: list[str] | None = Field(None, description="受训部门列表")
    employee_names: list[str] | None = Field(None, description="应出席受训人员姓名列表")
    employee_numbers: list[str] | None = Field(None, description="应出席受训人员工号列表")
    issuer_department: str | None = Field(None, max_length=64, description="落款部门")
    issue_date: date | None = Field(None, description="落款日期")
    remarks: str | None = Field(None, max_length=512, description="备注")
    status: str | None = Field("draft", max_length=16, description="状态: draft, notified, selecting, confirmed, evaluated, archived")
    select_task_token: str | None = Field(None, max_length=64, description="飞书选择任务token")
    select_tasks: list[dict] | None = Field(None, description="多部门选择任务列表")


class TrainingSessionCreate(TrainingSessionBase):
    pass


class TrainingSessionUpdate(BaseModel):
    model_config = ConfigDict(extra="allow")

    factory: str | None = Field(None, max_length=8)
    department: str | None = Field(None, max_length=64)
    training_date: date | None = Field(None)
    subject: str | None = Field(None, max_length=256)
    training_time_start: str | None = Field(None, max_length=32)
    training_time_end: str | None = Field(None, max_length=32)
    location: str | None = Field(None, max_length=128)
    trainer: str | None = Field(None, max_length=128)
    training_method: str | None = Field(None, max_length=32)
    content: str | None = Field(None, max_length=512)
    trainee_departments: list[str] | None = Field(None)
    employee_names: list[str] | None = Field(None)
    employee_numbers: list[str] | None = Field(None)
    issuer_department: str | None = Field(None, max_length=64)
    issue_date: date | None = Field(None)
    remarks: str | None = Field(None, max_length=512)
    status: str | None = Field(None, max_length=16)
    select_task_token: str | None = Field(None, max_length=64)


class TrainingSessionStatusUpdate(BaseModel):
    status: str = Field(..., max_length=16, description="状态: draft, notified, selecting, confirmed, evaluated, archived")


class TrainingSessionResponse(TrainingSessionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TrainingSessionListResponse(BaseModel):
    code: int
    message: str
    data: list[TrainingSessionResponse]
    meta: dict | None = None


# ─── TrainingLedgerPage Schemas ───

class TrainingLedgerPageCreate(BaseModel):
    employee_number: str = Field(..., max_length=32, description="工号")
    employee_name: str = Field(..., max_length=64, description="员工姓名")
    ledger_type: str = Field("event", max_length=16, description="台账类型: event=事件台账, sop=SOP培训台账")


class TrainingLedgerPageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_number: str
    employee_name: str
    ledger_type: str = Field("event", max_length=16, description="台账类型")
    department: str | None = Field(None, max_length=64, description="所属部门")
    factory: str | None = Field(None, max_length=8, description="厂区: old=旧厂, new=新厂")
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ─── AnnualTrainingPlan Schemas ───

class AnnualTrainingPlanBase(BaseModel):
    year: int = Field(..., description="年度")
    department: str = Field(..., max_length=64, description="部门")
    status: str = Field("草稿", max_length=16, description="状态: 草稿, 已确认")


class AnnualTrainingPlanCreate(AnnualTrainingPlanBase):
    pass


class AnnualTrainingPlanUpdate(BaseModel):
    year: int | None = Field(None, description="年度")
    department: str | None = Field(None, max_length=64, description="部门")
    status: str | None = Field(None, max_length=16, description="状态")


class AnnualTrainingPlanResponse(AnnualTrainingPlanBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AnnualTrainingPlanListResponse(BaseModel):
    code: int
    message: str
    data: list[AnnualTrainingPlanResponse]
    meta: dict | None = None


# ─── AnnualTrainingPlanItem Schemas ───

class AnnualTrainingPlanItemBase(BaseModel):
    month: str | None = Field(None, max_length=16, description="月份/季度")
    trainee_count: int | None = Field(None, description="培训人数")
    duration_hours: float | None = Field(None, description="课时")
    content_and_textbook: str | None = Field(None, max_length=512, description="培训内容及使用教材")
    target_audience: str | None = Field(None, max_length=256, description="培训对象")
    position_and_count: str | None = Field(None, max_length=256, description="参加岗位/参加人数")
    training_method: str | None = Field(None, max_length=64, description="培训方式")
    training_hours: float | None = Field(None, description="培训学时")
    confirmer: str | None = Field(None, max_length=64, description="确认者")
    confirm_date: date | None = Field(None, description="确认日期")
    remarks: str | None = Field(None, max_length=512, description="备注")
    tracking_status: str | None = Field(None, max_length=16, description="培训跟踪: 完成, 未完成")
    sort_order: int = Field(0, description="排序")


class AnnualTrainingPlanItemCreate(AnnualTrainingPlanItemBase):
    pass


class AnnualTrainingPlanItemUpdate(BaseModel):
    month: str | None = Field(None, max_length=16)
    trainee_count: int | None = Field(None)
    duration_hours: float | None = Field(None)
    content_and_textbook: str | None = Field(None, max_length=512)
    target_audience: str | None = Field(None, max_length=256)
    position_and_count: str | None = Field(None, max_length=256)
    training_method: str | None = Field(None, max_length=64)
    training_hours: float | None = Field(None)
    confirmer: str | None = Field(None, max_length=64)
    confirm_date: date | None = Field(None)
    remarks: str | None = Field(None, max_length=512)
    tracking_status: str | None = Field(None, max_length=16)
    sort_order: int | None = Field(None)
    target_audience: str | None = Field(None, max_length=256)
    position_and_count: str | None = Field(None, max_length=256)
    training_method: str | None = Field(None, max_length=64)
    training_hours: float | None = Field(None)
    confirmer: str | None = Field(None, max_length=64)
    confirm_date: date | None = Field(None)
    remarks: str | None = Field(None, max_length=512)
    sort_order: int | None = Field(None)


class AnnualTrainingPlanItemResponse(AnnualTrainingPlanItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plan_id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AnnualTrainingPlanItemBatchUpdate(BaseModel):
    items: list[AnnualTrainingPlanItemCreate] = Field(default_factory=list, description="明细列表")


# ─── Training Specialist Schemas ───

class TrainingSpecialistCreate(BaseModel):
    department: str = Field(..., max_length=64, description="部门名称")
    employee_number: str = Field(..., max_length=32, description="培训专员工号")
    employee_name: str = Field(..., max_length=64, description="培训专员姓名")
    factory: str = Field("old", max_length=8, description="厂区: old=旧厂, new=新厂")


class TrainingSpecialistUpdate(BaseModel):
    employee_number: str | None = Field(None, max_length=32)
    employee_name: str | None = Field(None, max_length=64)


class TrainingSpecialistResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    department: str
    employee_number: str
    employee_name: str
    factory: str
    feishu_open_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ─── Training Team Schemas ───

class TrainingTeamCreate(BaseModel):
    name: str = Field(..., max_length=128, description="班组名称")
    factory: str = Field("old", max_length=8, description="厂区: old=旧厂, new=新厂")
    department: str = Field(..., max_length=64, description="所属部门")
    specialist_employee_number: str = Field(..., max_length=32, description="培训专员工号")
    specialist_name: str = Field(..., max_length=64, description="培训专员姓名")
    employee_names: list[str] = Field(default_factory=list, description="受训人员姓名列表")
    employee_numbers: list[str] = Field(default_factory=list, description="受训人员工号列表")


class TrainingTeamUpdate(BaseModel):
    name: str | None = Field(None, max_length=128)
    department: str | None = Field(None, max_length=64)
    specialist_employee_number: str | None = Field(None, max_length=32)
    specialist_name: str | None = Field(None, max_length=64)
    employee_names: list[str] | None = Field(None)
    employee_numbers: list[str] | None = Field(None)


class TrainingTeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    factory: str
    department: str
    specialist_employee_number: str
    specialist_name: str
    employee_names: list | None = None
    employee_numbers: list | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ─── Candidate Schemas ───

class CandidateBase(BaseModel):
    name: str = Field(..., max_length=64, description="候选人姓名")
    position: str = Field(..., max_length=64, description="应聘职位名称")
    gender: str | None = Field(None, max_length=8, description="性别")
    school: str | None = Field(None, max_length=128, description="学校名称")
    education: str | None = Field(None, max_length=16, description="学历")
    major: str | None = Field(None, max_length=64, description="专业")
    match_report: str | None = Field(None, description="候选人匹配度报告")
    recommendation_level: str | None = Field(None, max_length=16, description="推荐等级")


class CandidateResponse(CandidateBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    resume_attachments: list[dict] | None = None
    feishu_record_id: str | None = None
    feishu_synced_at: date | None = None
    feishu_sync_status: str | None = None
    feishu_sync_error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CandidateListResponse(BaseModel):
    code: int
    message: str
    data: list[CandidateResponse]
    meta: dict | None = None


class CandidateUpdateRecommendationLevel(BaseModel):
    recommendation_level: str = Field(..., max_length=16, description="推荐等级")


class CandidateCreate(CandidateBase):
    pass


class CandidateUpdate(BaseModel):
    name: str | None = Field(None, max_length=64, description="候选人姓名")
    position: str | None = Field(None, max_length=64, description="应聘职位名称")
    gender: str | None = Field(None, max_length=8, description="性别")
    school: str | None = Field(None, max_length=128, description="学校名称")
    education: str | None = Field(None, max_length=16, description="学历")
    major: str | None = Field(None, max_length=64, description="专业")
    match_report: str | None = Field(None, description="候选人匹配度报告")
    recommendation_level: str | None = Field(None, max_length=16, description="推荐等级")


# ─── Pre-job Training Plan Template Schemas ───


class PrejobTemplateItem(BaseModel):
    """岗前培训计划单行条目（共10行）。"""
    seq: int = Field(..., description="序号 1-10")
    content: str = Field("", max_length=256, description="培训内容")
    deadline: str = Field("", max_length=64, description="完成期限")
    trainer: str = Field("", max_length=64, description="培训师")


class PrejobTemplateCreate(BaseModel):
    """保存部门岗前培训计划模板。"""
    department: str = Field(..., max_length=64, description="部门名称")
    factory: str = Field("old", max_length=8, description="厂区: old=旧厂, new=新厂")
    items: list[PrejobTemplateItem] = Field(
        default_factory=list, description="10行培训计划条目"
    )


class PrejobTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    department: str
    factory: str
    items: list[PrejobTemplateItem]
    created_at: datetime | None = None
    updated_at: datetime | None = None
