"""Instrument Calibration Schemas (仪器校准管理Pydantic Schema)

仪器设备台账、校准规则配置、校准记录、审批记录的数据验证模型
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
import enum


class InstrumentStatus(str, enum.Enum):
    """仪器状态"""
    DRAFT = "draft"                    # 草稿
    SUBMITTED = "submitted"            # 已提交
    ADMIN_APPROVED = "admin_approved"  # 设备管理员已审核
    QA_APPROVED = "qa_approved"        # QA已审核
    ACTIVE = "active"                 # 已启用
    INACTIVE = "inactive"              # 已停用


class CalibrationMethod(str, enum.Enum):
    """校准方式"""
    EXTERNAL = "external"  # 外委校准
    INTERNAL = "internal"  # 内部校准


class CalibrationCycleUnit(str, enum.Enum):
    """校准周期单位"""
    MONTH = "month"   # 月
    YEAR = "year"    # 年


class IQStatus(str, enum.Enum):
    """IQ确认状态"""
    PENDING = "pending"           # 待确认
    CONFIRMED = "confirmed"       # 已确认
    NOT_REQUIRED = "not_required"  # 不需要


class OQStatus(str, enum.Enum):
    """OQ确认状态"""
    PENDING = "pending"           # 待确认
    CONFIRMED = "confirmed"        # 已确认
    NOT_REQUIRED = "not_required" # 不需要


class InstrumentCategory(str, enum.Enum):
    """仪器分类"""
    PHYSICOCHEMICAL = "physicochemical"  # 理化
    CHROMATOGRAPHY = "chromatography"    # 色谱
    MICROBIOLOGY = "microbiology"        # 微生物
    BALANCE = "balance"                   # 天平
    OVEN = "oven"                         # 烘箱
    OTHER = "other"                       # 其他


class CalibrationResult(str, enum.Enum):
    """校准结论"""
    QUALIFIED = "qualified"      # 合格
    UNQUALIFIED = "unqualified"  # 不合格
    LIMITED = "limited"         # 限用


class RecordStatus(str, enum.Enum):
    """校准记录状态"""
    ACTIVE = "active"           # 已启用/有效
    DRAFT = "draft"             # 草稿
    SUBMITTED = "submitted"     # 已提交
    ADMIN_APPROVED = "admin_approved"  # 设备管理员已审核
    QA_APPROVED = "qa_approved"        # QA已审核
    COMPLETED = "completed"      # 已完成


class ApprovalType(str, enum.Enum):
    """审批类型"""
    INSTRUMENT = "instrument"   # 仪器档案审批
    RECORD = "record"           # 校准记录审批


class ApprovalStatus(str, enum.Enum):
    """审批状态"""
    PENDING = "pending"     # 待审批
    APPROVED = "approved"   # 已批准
    REJECTED = "rejected"   # 已驳回


# ========== 仪器设备台账 Schema ==========
class InstrumentBase(BaseModel):
    """仪器基础Schema"""
    instrument_no: str = Field(..., description="仪器编号")
    instrument_name: str = Field(..., description="仪器名称")
    model: Optional[str] = Field(None, description="型号")
    serial_no: Optional[str] = Field(None, description="出厂编号")
    manufacturer: Optional[str] = Field(None, description="制造商")
    location: Optional[str] = Field(None, description="存放地点")
    category: Optional[InstrumentCategory] = Field(None, description="仪器分类")
    manufacture_date: Optional[datetime] = Field(None, description="出厂日期")
    iq_status: Optional[IQStatus] = Field(None, description="IQ确认状态")
    oq_status: Optional[OQStatus] = Field(None, description="OQ确认状态")
    iq_confirm_date: Optional[datetime] = Field(None, description="IQ确认日期")
    oq_confirm_date: Optional[datetime] = Field(None, description="OQ确认日期")
    responsible_id: Optional[UUID] = Field(None, description="使用负责人ID")
    responsible_name: Optional[str] = Field(None, description="使用负责人")
    is_active: bool = Field(True, description="是否启用")
    deactivate_date: Optional[datetime] = Field(None, description="停用日期")
    deactivate_reason: Optional[str] = Field(None, description="停用原因")
    remark: Optional[str] = Field(None, description="备注")


class InstrumentCreate(InstrumentBase):
    """创建仪器"""
    pass


class InstrumentUpdate(BaseModel):
    """更新仪器"""
    instrument_name: Optional[str] = None
    model: Optional[str] = None
    serial_no: Optional[str] = None
    manufacturer: Optional[str] = None
    location: Optional[str] = None
    category: Optional[InstrumentCategory] = None
    manufacture_date: Optional[datetime] = None
    iq_status: Optional[IQStatus] = None
    oq_status: Optional[OQStatus] = None
    iq_confirm_date: Optional[datetime] = None
    oq_confirm_date: Optional[datetime] = None
    responsible_id: Optional[UUID] = None
    responsible_name: Optional[str] = None
    is_active: Optional[bool] = None
    deactivate_date: Optional[datetime] = None
    deactivate_reason: Optional[str] = None
    remark: Optional[str] = None


class InstrumentResponse(InstrumentBase):
    """仪器响应"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: InstrumentStatus
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None


class InstrumentListItem(BaseModel):
    """仪器列表项"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    instrument_no: str
    instrument_name: str
    model: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    responsible_name: Optional[str] = None
    is_active: bool
    status: InstrumentStatus
    next_calibration_date: Optional[datetime] = None
    is_overdue: bool = False
    created_at: datetime


# ========== 校准规则 Schema ==========
class CalibrationRuleBase(BaseModel):
    """校准规则基础Schema"""
    calibration_method: CalibrationMethod = Field(..., description="校准方式")
    calibration_cycle: Optional[int] = Field(None, description="校准周期")
    calibration_unit: Optional[CalibrationCycleUnit] = Field(None, description="周期单位")
    last_calibration_date: Optional[datetime] = Field(None, description="最近校准日期")
    next_calibration_date: Optional[datetime] = Field(None, description="下次校准日期")
    calibration_agency: Optional[str] = Field(None, description="校准机构名称")
    agency_contact: Optional[str] = Field(None, description="机构联系方式")
    internal_calibrator_id: Optional[UUID] = Field(None, description="内校人员ID")
    internal_calibrator_name: Optional[str] = Field(None, description="内校人员")
    warning_days: int = Field(7, description="提前预警天数")
    is_active: bool = Field(True, description="是否启用")


class CalibrationRuleCreate(CalibrationRuleBase):
    """创建校准规则"""
    instrument_id: UUID = Field(..., description="关联仪器ID")


class CalibrationRuleUpdate(BaseModel):
    """更新校准规则"""
    calibration_method: Optional[CalibrationMethod] = None
    calibration_cycle: Optional[int] = None
    calibration_unit: Optional[CalibrationCycleUnit] = None
    last_calibration_date: Optional[datetime] = None
    next_calibration_date: Optional[datetime] = None
    calibration_agency: Optional[str] = None
    agency_contact: Optional[str] = None
    internal_calibrator_id: Optional[UUID] = None
    internal_calibrator_name: Optional[str] = None
    warning_days: Optional[int] = None
    is_active: Optional[bool] = None


class CalibrationRuleResponse(CalibrationRuleBase):
    """校准规则响应"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    instrument_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None


# ========== 校准记录 Schema ==========
class CalibrationRecordBase(BaseModel):
    """校准记录基础Schema"""
    calibration_date: datetime = Field(..., description="校准日期")
    calibration_end_date: Optional[datetime] = Field(None, description="校准完成日期")
    calibration_method: CalibrationMethod = Field(..., description="校准方式")
    calibration_agency: Optional[str] = Field(None, description="校准机构")
    calibrator_id: Optional[UUID] = Field(None, description="校准人员ID")
    calibrator_name: Optional[str] = Field(None, description="校准人员")
    certificate_no: Optional[str] = Field(None, description="校准证书编号")
    certificate_url: Optional[str] = Field(None, description="校准证书附件URL")
    calibration_result: CalibrationResult = Field(..., description="校准结论")
    result_reason: Optional[str] = Field(None, description="结论说明")
    valid_from: Optional[datetime] = Field(None, description="有效期起")
    valid_until: Optional[datetime] = Field(None, description="有效期至")
    is_scheduled: bool = Field(False, description="是否计划校准")
    scheduled_date: Optional[datetime] = Field(None, description="计划校准日期")
    remark: Optional[str] = Field(None, description="备注")


class CalibrationRecordCreate(CalibrationRecordBase):
    """创建校准记录"""
    instrument_id: UUID = Field(..., description="关联仪器ID")
    rule_id: Optional[UUID] = Field(None, description="关联校准规则ID")


class CalibrationRecordUpdate(BaseModel):
    """更新校准记录"""
    calibration_date: Optional[datetime] = None
    calibration_end_date: Optional[datetime] = None
    calibration_method: Optional[CalibrationMethod] = None
    calibration_agency: Optional[str] = None
    calibrator_id: Optional[UUID] = None
    calibrator_name: Optional[str] = None
    certificate_no: Optional[str] = None
    certificate_url: Optional[str] = None
    calibration_result: Optional[CalibrationResult] = None
    result_reason: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_scheduled: Optional[bool] = None
    scheduled_date: Optional[datetime] = None
    remark: Optional[str] = None


class CalibrationRecordResponse(CalibrationRecordBase):
    """校准记录响应"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    instrument_id: UUID
    rule_id: Optional[UUID] = None
    calibration_no: str
    status: RecordStatus
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    # 关联仪器信息
    instrument_no: Optional[str] = None
    instrument_name: Optional[str] = None


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
    calibrator_name: Optional[str] = None
    certificate_no: Optional[str] = None
    created_at: datetime


# ========== 审批记录 Schema ==========
class ApprovalCreate(BaseModel):
    """创建审批"""
    status: ApprovalStatus = Field(..., description="审批状态")
    comments: Optional[str] = Field(None, description="审批意见")


class ApprovalResponse(BaseModel):
    """审批响应"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    related_type: ApprovalType
    related_id: UUID
    approval_type: str
    sequence: int
    status: ApprovalStatus
    approval_date: Optional[datetime] = None
    comments: Optional[str] = None
    approver_id: Optional[UUID] = None
    approver_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ========== 筛选条件 Schema ==========
class InstrumentFilter(BaseModel):
    """仪器筛选条件"""
    instrument_no: Optional[str] = None
    instrument_name: Optional[str] = None
    category: Optional[InstrumentCategory] = None
    is_active: Optional[bool] = None
    status: Optional[InstrumentStatus] = None
    is_overdue: Optional[bool] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class CalibrationRecordFilter(BaseModel):
    """校准记录筛选条件"""
    instrument_id: Optional[UUID] = None
    calibration_no: Optional[str] = None
    calibration_result: Optional[CalibrationResult] = None
    status: Optional[RecordStatus] = None
    calibration_method: Optional[CalibrationMethod] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
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
    name: str = Field(..., description='配置名称')
    feishu_app_id: Optional[str] = Field(None, description='飞书应用AppID')
    feishu_app_secret: Optional[str] = Field(None, description='飞书应用AppSecret')
    chat_id: Optional[str] = Field(None, description='飞书群ID或用户ID')
    receive_id_type: str = Field('chat_id', description='接收类型: chat_id/user_id')
    remind_30_days: bool = Field(True, description='是否在30天前提醒')
    remind_14_days: bool = Field(True, description='是否在14天前提醒')
    remind_7_days: bool = Field(True, description='是否在7天前提醒')
    remind_overdue: bool = Field(True, description='是否在超期后提醒')
    is_active: bool = Field(True, description='是否启用')


class ReminderConfigUpdate(BaseModel):
    """更新提醒配置"""
    name: Optional[str] = None
    feishu_app_id: Optional[str] = None
    feishu_app_secret: Optional[str] = None
    chat_id: Optional[str] = None
    receive_id_type: Optional[str] = None
    remind_30_days: Optional[bool] = None
    remind_14_days: Optional[bool] = None
    remind_7_days: Optional[bool] = None
    remind_overdue: Optional[bool] = None
    is_active: Optional[bool] = None


class ReminderConfigResponse(BaseModel):
    """提醒配置响应"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    feishu_app_id: Optional[str] = None
    feishu_app_secret: Optional[str] = None
    chat_id: Optional[str] = None
    receive_id_type: str
    remind_30_days: bool
    remind_14_days: bool
    remind_7_days: bool
    remind_overdue: bool
    is_active: bool
    last_remind_30_days: Optional[datetime] = None
    last_remind_14_days: Optional[datetime] = None
    last_remind_7_days: Optional[datetime] = None
    last_remind_overdue: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ReminderConfigListResponse(BaseModel):
    """提醒配置列表响应"""
    items: list[ReminderConfigResponse]
    total: int
