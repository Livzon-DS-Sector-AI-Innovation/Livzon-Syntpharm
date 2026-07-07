"""Instrument Calibration Schemas (仪器校准管理Pydantic Schema)

仪器设备台账、校准规则配置、校准记录、审批记录的数据验证模型
"""

import enum
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InstrumentStatus(str, enum.Enum):
    """仪器状态"""

    DRAFT = "draft"  # 草稿
    SUBMITTED = "submitted"  # 已提交
    ADMIN_APPROVED = "admin_approved"  # 设备管理员已审核
    QA_APPROVED = "qa_approved"  # QA已审核
    ACTIVE = "active"  # 已启用
    INACTIVE = "inactive"  # 已停用


class CalibrationMethod(str, enum.Enum):
    """校准方式"""

    EXTERNAL = "external"  # 外委校准
    INTERNAL = "internal"  # 内部校准


class CalibrationCycleUnit(str, enum.Enum):
    """校准周期单位"""

    MONTH = "month"  # 月
    YEAR = "year"  # 年


class IQStatus(str, enum.Enum):
    """IQ确认状态"""

    PENDING = "pending"  # 待确认
    CONFIRMED = "confirmed"  # 已确认
    NOT_REQUIRED = "not_required"  # 不需要


class OQStatus(str, enum.Enum):
    """OQ确认状态"""

    PENDING = "pending"  # 待确认
    CONFIRMED = "confirmed"  # 已确认
    NOT_REQUIRED = "not_required"  # 不需要


class InstrumentCategory(str, enum.Enum):
    """仪器分类"""

    PHYSICOCHEMICAL = "physicochemical"  # 理化
    CHROMATOGRAPHY = "chromatography"  # 色谱
    MICROBIOLOGY = "microbiology"  # 微生物
    BALANCE = "balance"  # 天平
    OVEN = "oven"  # 烘箱
    OTHER = "other"  # 其他


class CalibrationResult(str, enum.Enum):
    """校准结论"""

    QUALIFIED = "qualified"  # 合格
    UNQUALIFIED = "unqualified"  # 不合格
    LIMITED = "limited"  # 限用


class RecordStatus(str, enum.Enum):
    """校准记录状态"""

    ACTIVE = "active"  # 已启用/有效
    DRAFT = "draft"  # 草稿
    SUBMITTED = "submitted"  # 已提交
    ADMIN_APPROVED = "admin_approved"  # 设备管理员已审核
    QA_APPROVED = "qa_approved"  # QA已审核
    COMPLETED = "completed"  # 已完成


class ApprovalType(str, enum.Enum):
    """审批类型"""

    INSTRUMENT = "instrument"  # 仪器档案审批
    RECORD = "record"  # 校准记录审批


class ApprovalStatus(str, enum.Enum):
    """审批状态"""

    PENDING = "pending"  # 待审批
    APPROVED = "approved"  # 已批准
    REJECTED = "rejected"  # 已驳回


# ========== 仪器设备台账 Schema ==========
class InstrumentBase(BaseModel):
    """仪器基础Schema"""

    instrument_no: str = Field(..., description="仪器编号")
    instrument_name: str = Field(..., description="仪器名称")
    model: str | None = Field(None, description="型号")
    serial_no: str | None = Field(None, description="出厂编号")
    manufacturer: str | None = Field(None, description="制造商")
    location: str | None = Field(None, description="存放地点")
    category: InstrumentCategory | None = Field(None, description="仪器分类")
    manufacture_date: datetime | None = Field(None, description="出厂日期")
    iq_status: IQStatus | None = Field(None, description="IQ确认状态")
    oq_status: OQStatus | None = Field(None, description="OQ确认状态")
    iq_confirm_date: datetime | None = Field(None, description="IQ确认日期")
    oq_confirm_date: datetime | None = Field(None, description="OQ确认日期")
    responsible_id: UUID | None = Field(None, description="使用负责人ID")
    responsible_name: str | None = Field(None, description="使用负责人")
    is_active: bool = Field(True, description="是否启用")
    deactivate_date: datetime | None = Field(None, description="停用日期")
    deactivate_reason: str | None = Field(None, description="停用原因")
    remark: str | None = Field(None, description="备注")


class InstrumentCreate(InstrumentBase):
    """创建仪器"""

    pass


class InstrumentUpdate(BaseModel):
    """更新仪器"""

    instrument_name: str | None = None
    model: str | None = None
    serial_no: str | None = None
    manufacturer: str | None = None
    location: str | None = None
    category: InstrumentCategory | None = None
    manufacture_date: datetime | None = None
    iq_status: IQStatus | None = None
    oq_status: OQStatus | None = None
    iq_confirm_date: datetime | None = None
    oq_confirm_date: datetime | None = None
    responsible_id: UUID | None = None
    responsible_name: str | None = None
    is_active: bool | None = None
    deactivate_date: datetime | None = None
    deactivate_reason: str | None = None
    remark: str | None = None


class InstrumentResponse(InstrumentBase):
    """仪器响应"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: InstrumentStatus
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None


class InstrumentListItem(BaseModel):
    """仪器列表项"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    instrument_no: str
    instrument_name: str
    model: str | None = None
    category: str | None = None
    location: str | None = None
    responsible_name: str | None = None
    is_active: bool
    status: InstrumentStatus
    next_calibration_date: datetime | None = None
    is_overdue: bool = False
    created_at: datetime


# ========== 校准规则 Schema ==========
class CalibrationRuleBase(BaseModel):
    """校准规则基础Schema"""

    calibration_method: CalibrationMethod = Field(..., description="校准方式")
    calibration_cycle: int | None = Field(None, description="校准周期")
    calibration_unit: CalibrationCycleUnit | None = Field(
        None, description="周期单位"
    )
    last_calibration_date: datetime | None = Field(None, description="最近校准日期")
    next_calibration_date: datetime | None = Field(None, description="下次校准日期")
    calibration_agency: str | None = Field(None, description="校准机构名称")
    agency_contact: str | None = Field(None, description="机构联系方式")
    internal_calibrator_id: UUID | None = Field(None, description="内校人员ID")
    internal_calibrator_name: str | None = Field(None, description="内校人员")
    warning_days: int = Field(7, description="提前预警天数")
    is_active: bool = Field(True, description="是否启用")


class CalibrationRuleCreate(CalibrationRuleBase):
    """创建校准规则"""

    instrument_id: UUID = Field(..., description="关联仪器ID")


class CalibrationRuleUpdate(BaseModel):
    """更新校准规则"""

    calibration_method: CalibrationMethod | None = None
    calibration_cycle: int | None = None
    calibration_unit: CalibrationCycleUnit | None = None
    last_calibration_date: datetime | None = None
    next_calibration_date: datetime | None = None
    calibration_agency: str | None = None
    agency_contact: str | None = None
    internal_calibrator_id: UUID | None = None
    internal_calibrator_name: str | None = None
    warning_days: int | None = None
    is_active: bool | None = None


class CalibrationRuleResponse(CalibrationRuleBase):
    """校准规则响应"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    instrument_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None


# ========== 校准记录 Schema ==========
class CalibrationRecordBase(BaseModel):
    """校准记录基础Schema"""

    calibration_date: datetime = Field(..., description="校准日期")
    calibration_end_date: datetime | None = Field(None, description="校准完成日期")
    calibration_method: CalibrationMethod = Field(..., description="校准方式")
    calibration_agency: str | None = Field(None, description="校准机构")
    calibrator_id: UUID | None = Field(None, description="校准人员ID")
    calibrator_name: str | None = Field(None, description="校准人员")
    certificate_no: str | None = Field(None, description="校准证书编号")
    certificate_url: str | None = Field(None, description="校准证书附件URL")
    calibration_result: CalibrationResult = Field(..., description="校准结论")
    result_reason: str | None = Field(None, description="结论说明")
    valid_from: datetime | None = Field(None, description="有效期起")
    valid_until: datetime | None = Field(None, description="有效期至")
    is_scheduled: bool = Field(False, description="是否计划校准")
    scheduled_date: datetime | None = Field(None, description="计划校准日期")
    remark: str | None = Field(None, description="备注")


class CalibrationRecordCreate(CalibrationRecordBase):
    """创建校准记录"""

    instrument_id: UUID = Field(..., description="关联仪器ID")
    rule_id: UUID | None = Field(None, description="关联校准规则ID")


class CalibrationRecordUpdate(BaseModel):
    """更新校准记录"""

    calibration_date: datetime | None = None
    calibration_end_date: datetime | None = None
    calibration_method: CalibrationMethod | None = None
    calibration_agency: str | None = None
    calibrator_id: UUID | None = None
    calibrator_name: str | None = None
    certificate_no: str | None = None
    certificate_url: str | None = None
    calibration_result: CalibrationResult | None = None
    result_reason: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    is_scheduled: bool | None = None
    scheduled_date: datetime | None = None
    remark: str | None = None


class CalibrationRecordResponse(CalibrationRecordBase):
    """校准记录响应"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    instrument_id: UUID
    rule_id: UUID | None = None
    calibration_no: str
    status: RecordStatus
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None
    # 关联仪器信息
    instrument_no: str | None = None
    instrument_name: str | None = None


class CalibrationRecordListItem(BaseModel):
    """校准记录列表项"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    calibration_no: str
    instrument_id: UUID
    instrument_no: str
    instrument_name: str
    calibration_date: datetime
    calibration_method: str
    calibration_result: CalibrationResult
    status: RecordStatus
    calibrator_name: str | None = None
    certificate_no: str | None = None
    created_at: datetime


# ========== 审批记录 Schema ==========
class ApprovalCreate(BaseModel):
    """创建审批"""

    status: ApprovalStatus = Field(..., description="审批状态")
    comments: str | None = Field(None, description="审批意见")


class ApprovalResponse(BaseModel):
    """审批响应"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    related_type: ApprovalType
    related_id: UUID
    approval_type: str
    sequence: int
    status: ApprovalStatus
    approval_date: datetime | None = None
    comments: str | None = None
    approver_id: UUID | None = None
    approver_name: str | None = None
    created_at: datetime
    updated_at: datetime


# ========== 筛选条件 Schema ==========
class InstrumentFilter(BaseModel):
    """仪器筛选条件"""

    instrument_no: str | None = None
    instrument_name: str | None = None
    category: InstrumentCategory | None = None
    is_active: bool | None = None
    status: InstrumentStatus | None = None
    is_overdue: bool | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class CalibrationRecordFilter(BaseModel):
    """校准记录筛选条件"""

    instrument_id: UUID | None = None
    calibration_no: str | None = None
    calibration_result: CalibrationResult | None = None
    status: RecordStatus | None = None
    calibration_method: CalibrationMethod | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


# ========== 列表响应 Schema ==========
class InstrumentListResponse(BaseModel):
    """仪器列表响应"""

    items: list[InstrumentListItem]
    total: int
    page: int
    page_size: int


class CalibrationRecordListResponse(BaseModel):
    """校准记录列表响应"""

    items: list[CalibrationRecordListItem]
    total: int
    page: int
    page_size: int


# ========== 校准到期提醒配置 Schema ==========
class ReminderConfigCreate(BaseModel):
    """创建提醒配置"""

    name: str = Field(..., description="配置名称")
    feishu_app_id: str | None = Field(None, description="飞书应用AppID")
    feishu_app_secret: str | None = Field(None, description="飞书应用AppSecret")
    chat_id: str | None = Field(None, description="飞书群ID或用户ID")
    receive_id_type: str = Field("chat_id", description="接收类型: chat_id/user_id")
    remind_30_days: bool = Field(True, description="是否在30天前提醒")
    remind_14_days: bool = Field(True, description="是否在14天前提醒")
    remind_7_days: bool = Field(True, description="是否在7天前提醒")
    remind_overdue: bool = Field(True, description="是否在超期后提醒")
    is_active: bool = Field(True, description="是否启用")


class ReminderConfigUpdate(BaseModel):
    """更新提醒配置"""

    name: str | None = None
    feishu_app_id: str | None = None
    feishu_app_secret: str | None = None
    chat_id: str | None = None
    receive_id_type: str | None = None
    remind_30_days: bool | None = None
    remind_14_days: bool | None = None
    remind_7_days: bool | None = None
    remind_overdue: bool | None = None
    is_active: bool | None = None


class ReminderConfigResponse(BaseModel):
    """提醒配置响应"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    feishu_app_id: str | None = None
    feishu_app_secret: str | None = None
    chat_id: str | None = None
    receive_id_type: str
    remind_30_days: bool
    remind_14_days: bool
    remind_7_days: bool
    remind_overdue: bool
    is_active: bool
    last_remind_30_days: datetime | None = None
    last_remind_14_days: datetime | None = None
    last_remind_7_days: datetime | None = None
    last_remind_overdue: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ReminderConfigListResponse(BaseModel):
    """提醒配置列表响应"""

    items: list[ReminderConfigResponse]
    total: int
