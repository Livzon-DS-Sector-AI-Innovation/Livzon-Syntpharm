"""Stability Study (稳定性试验) schemas"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ========== Enums ==========
class StabilityStudyType(str, Enum):
    """稳定性试验类型"""
    LONG_TERM = "long_term"  # 长期试验
    ACCELERATED = "accelerated"  # 加速试验
    INTERMEDIATE = "intermediate"  # 中间条件试验


class StabilityStudyStatus(str, Enum):
    """稳定性试验状态"""
    DRAFT = "draft"  # 草稿
    SUBMITTED = "submitted"  # 已提交
    DEVELOPER_APPROVED = "developer_approved"  # 研发主管审核
    QC_SUPERVISOR_APPROVED = "qc_supervisor_approved"  # QC主管审核
    QA_APPROVED = "qa_approved"  # QA审核
    FINAL_APPROVED = "final_approved"  # 质量负责人批准
    ACTIVE = "active"  # 试验中
    COMPLETED = "completed"  # 已完成
    CLOSED = "closed"  # 已关闭
    REJECTED = "rejected"  # 驳回


class StabilityStudyConclusion(str, Enum):
    """稳定性试验结论"""
    QUALIFIED = "qualified"  # 合格
    CONDITIONAL = "conditional"  # 条件合格
    UNQUALIFIED = "unqualified"  # 不合格


class SampleNodeStatus(str, Enum):
    """取样节点状态"""
    PENDING = "pending"  # 待取样
    SAMPLING_DONE = "sampling_done"  # 已取样
    INSPECTION_DONE = "inspection_done"  # 检验完成
    OVERDUE = "overdue"  # 逾期


class StabilityInspectionStatus(str, Enum):
    """稳定性检验状态"""
    DRAFT = "draft"  # 草稿
    SUBMITTED = "submitted"  # 已提交
    APPROVED = "approved"  # 已审核
    REJECTED = "rejected"  # 驳回


class StabilityInspectionConclusion(str, Enum):
    """稳定性检验结论"""
    QUALIFIED = "qualified"  # 合格
    UNQUALIFIED = "unqualified"  # 不合格


class StabilityItemResult(str, Enum):
    """稳定性单项判定"""
    PASS = "pass"  # 合格
    FAIL = "fail"  # 不合格
    NA = "na"  # 不适用


class StabilityApprovalType(str, Enum):
    """审批类型"""
    STUDY = "study"  # 方案审批
    INSPECTION = "inspection"  # 检验审批


class StabilityApprovalStatus(str, Enum):
    """审批状态"""
    PENDING = "pending"  # 待审批
    APPROVED = "approved"  # 已批准
    REJECTED = "rejected"  # 驳回


# ========== Sample Node Schemas ==========
class StabilitySampleNodeBase(BaseModel):
    """取样节点基础Schema"""
    node_no: int = Field(..., description="节点序号")
    node_month: int = Field(..., description="节点月数")
    node_name: Optional[str] = Field(None, description="节点名称")
    planned_date: Optional[datetime] = Field(None, description="计划取样日期")
    actual_date: Optional[datetime] = Field(None, description="实际取样日期")
    status: SampleNodeStatus = Field(SampleNodeStatus.PENDING, description="状态")
    remark: Optional[str] = Field(None, description="备注")


class StabilitySampleNodeCreate(StabilitySampleNodeBase):
    """创建取样节点"""
    pass


class StabilitySampleNodeUpdate(BaseModel):
    """更新取样节点"""
    node_no: Optional[int] = None
    node_month: Optional[int] = None
    node_name: Optional[str] = None
    planned_date: Optional[datetime] = None
    actual_date: Optional[datetime] = None
    status: Optional[SampleNodeStatus] = None
    remark: Optional[str] = None


class StabilitySampleNodeResponse(StabilitySampleNodeBase):
    """取样节点响应"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    stability_study_id: UUID
    reminder_sent: bool = False
    reminder_date: Optional[datetime] = None
    inspection_id: Optional[UUID] = None
    inspection_no: Optional[str] = None
    inspection_status: Optional[str] = None
    inspection_conclusion: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ========== Inspection Item Schemas ==========
class StabilityInspectionItemBase(BaseModel):
    """检验明细基础Schema"""
    item_no: int = Field(..., description="项次")
    inspection_item: str = Field(..., description="检验项目名称")
    inspection_method: Optional[str] = Field(None, description="检验方法")
    standard_value: Optional[str] = Field(None, description="标准值/限度")
    unit: Optional[str] = Field(None, description="单位")
    measured_value: Optional[str] = Field(None, description="实测值")
    result: Optional[StabilityItemResult] = Field(None, description="单项判定")
    is_oos: bool = Field(False, description="是否超标")
    oos_description: Optional[str] = Field(None, description="超标描述")
    data_point: Optional[str] = Field(None, description="数据点")
    chromatogram_urls: Optional[str] = Field(None, description="图谱附件JSON")
    remark: Optional[str] = Field(None, description="备注")


class StabilityInspectionItemCreate(StabilityInspectionItemBase):
    """创建检验明细"""
    pass


class StabilityInspectionItemUpdate(StabilityInspectionItemBase):
    """更新检验明细"""
    id: Optional[UUID] = None


class StabilityInspectionItemResponse(StabilityInspectionItemBase):
    """检验明细响应"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    stability_inspection_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None


# ========== Stability Inspection Schemas ==========
class StabilityInspectionBase(BaseModel):
    """检验记录基础Schema"""
    inspection_date: Optional[datetime] = Field(None, description="检验日期")
    inspector_id: Optional[UUID] = Field(None, description="检验员ID")
    inspector_name: Optional[str] = Field(None, description="检验员")
    sample_quantity: Optional[Decimal] = Field(None, description="取样数量")
    sample_no: Optional[str] = Field(None, description="样品编号")
    sample_condition: Optional[str] = Field(None, description="样品状态")
    standard_id: Optional[UUID] = Field(None, description="检验标准ID")
    standard_name: Optional[str] = Field(None, description="质量标准名称")
    inspection_conclusion: Optional[StabilityInspectionConclusion] = Field(None, description="检验结论")
    conclusion_reason: Optional[str] = Field(None, description="结论说明")
    remark: Optional[str] = Field(None, description="备注")
    oos_report_no: Optional[str] = Field(None, description="OOS报告编号")
    attachments: Optional[str] = Field(None, description="附件JSON")


class StabilityInspectionCreate(StabilityInspectionBase):
    """创建检验记录"""
    study_id: UUID = Field(..., description="稳定性试验ID")
    sample_node_id: UUID = Field(..., description="取样节点ID")
    items: list[StabilityInspectionItemCreate] = Field(default_factory=list, description="检验明细")


class StabilityInspectionUpdate(BaseModel):
    """更新检验记录"""
    inspection_date: Optional[datetime] = None
    inspector_id: Optional[UUID] = None
    inspector_name: Optional[str] = None
    sample_quantity: Optional[Decimal] = None
    sample_no: Optional[str] = None
    sample_condition: Optional[str] = None
    standard_id: Optional[UUID] = None
    standard_name: Optional[str] = None
    inspection_conclusion: Optional[StabilityInspectionConclusion] = None
    conclusion_reason: Optional[str] = None
    remark: Optional[str] = None
    oos_report_no: Optional[str] = None
    attachments: Optional[str] = None
    items: Optional[list[StabilityInspectionItemCreate]] = None


class StabilityInspectionResponse(StabilityInspectionBase):
    """检验记录响应"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    study_id: UUID
    study_no: str
    sample_node_id: UUID
    node_month: int
    inspection_no: str
    product_code: str
    product_name: Optional[str] = None
    batch_no: str
    specification: Optional[str] = None
    status: StabilityInspectionStatus
    is_oos: bool = False
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    items: list[StabilityInspectionItemResponse] = []


class StabilityInspectionListResponse(BaseModel):
    """检验记录列表响应"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    inspection_no: str
    study_no: str
    node_month: int
    product_code: str
    product_name: Optional[str] = None
    batch_no: str
    inspection_date: Optional[datetime] = None
    inspector_name: Optional[str] = None
    status: StabilityInspectionStatus
    inspection_conclusion: Optional[StabilityInspectionConclusion] = None
    created_at: datetime


# ========== Stability Study Schemas ==========
class StabilityStudyBase(BaseModel):
    """稳定性试验基础Schema"""
    product_code: str = Field(..., description="产品编码")
    product_name: Optional[str] = Field(None, description="产品名称")
    product_category: Optional[str] = Field(None, description="产品类别")
    batch_no: str = Field(..., description="批号")
    batch_quantity: Optional[Decimal] = Field(None, description="批量")
    packaging_spec: Optional[str] = Field(None, description="包装规格")
    study_type: StabilityStudyType = Field(..., description="试验类型")
    temperature: Optional[str] = Field(None, description="温度条件")
    humidity: Optional[str] = Field(None, description="湿度条件")
    start_date: Optional[datetime] = Field(None, description="试验开始日期")
    end_date: Optional[datetime] = Field(None, description="试验结束日期")
    expiry_date: Optional[datetime] = Field(None, description="有效期")
    sample_intervals: Optional[str | list[int]] = Field(None, description="取样周期节点，逗号分隔或数组")
    standard_id: Optional[UUID] = Field(None, description="检验标准ID")
    standard_name: Optional[str] = Field(None, description="质量标准名称")
    standard_version: Optional[str] = Field(None, description="标准版本")
    developer_id: Optional[UUID] = Field(None, description="研发人员ID")
    developer_name: Optional[str] = Field(None, description="研发人员")
    study_conclusion: Optional[StabilityStudyConclusion] = Field(None, description="试验结论")
    conclusion_reason: Optional[str] = Field(None, description="结论说明")
    remark: Optional[str] = Field(None, description="备注")
    attachments: Optional[str] = Field(None, description="附件JSON")


class StabilityStudyCreate(StabilityStudyBase):
    """创建稳定性试验"""
    sample_nodes: list[StabilitySampleNodeCreate] = Field(default_factory=list, description="取样节点列表")


class StabilityStudyUpdate(BaseModel):
    """更新稳定性试验"""
    product_code: Optional[str] = None
    product_name: Optional[str] = None
    product_category: Optional[str] = None
    batch_no: Optional[str] = None
    batch_quantity: Optional[Decimal] = None
    packaging_spec: Optional[str] = None
    study_type: Optional[StabilityStudyType] = None
    temperature: Optional[str] = None
    humidity: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    sample_intervals: Optional[str] = None
    standard_id: Optional[UUID] = None
    standard_name: Optional[str] = None
    standard_version: Optional[str] = None
    developer_id: Optional[UUID] = None
    developer_name: Optional[str] = None
    study_conclusion: Optional[StabilityStudyConclusion] = None
    conclusion_reason: Optional[str] = None
    remark: Optional[str] = None
    attachments: Optional[str] = None
    sample_nodes: Optional[list[StabilitySampleNodeCreate]] = None


class StabilityStudyResponse(StabilityStudyBase):
    """稳定性试验响应"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    study_no: str
    status: StabilityStudyStatus
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    sample_nodes: list[StabilitySampleNodeResponse] = []


class StabilityStudyListResponse(BaseModel):
    """稳定性试验列表响应"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    study_no: str
    product_code: str
    product_name: Optional[str] = None
    batch_no: str
    study_type: StabilityStudyType
    status: StabilityStudyStatus
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    developer_name: Optional[str] = None
    study_conclusion: Optional[StabilityStudyConclusion] = None
    created_at: datetime


# ========== Approval Schemas ==========
class StabilityApprovalCreate(BaseModel):
    """稳定性审批"""
    approval_status: StabilityApprovalStatus = Field(..., description="审批状态")
    comments: Optional[str] = Field(None, description="审批意见")


class StabilityApprovalRecordResponse(BaseModel):
    """审批记录响应"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    study_id: Optional[UUID] = None
    inspection_id: Optional[UUID] = None
    approval_type: StabilityApprovalType
    approval_level: int
    approval_status: StabilityApprovalStatus
    approver_role: Optional[str] = None
    approver_id: Optional[UUID] = None
    approver_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    comments: Optional[str] = None
    created_at: datetime


# ========== Filter Schemas ==========
class StabilityStudyFilter(BaseModel):
    """稳定性试验筛选条件"""
    study_no: Optional[str] = None
    product_code: Optional[str] = None
    product_name: Optional[str] = None
    batch_no: Optional[str] = None
    study_type: Optional[StabilityStudyType] = None
    status: Optional[StabilityStudyStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class StabilityInspectionFilter(BaseModel):
    """稳定性检验筛选条件"""
    study_id: Optional[UUID] = None
    study_no: Optional[str] = None
    inspection_no: Optional[str] = None
    batch_no: Optional[str] = None
    status: Optional[StabilityInspectionStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


# ========== Trend Analysis Schemas ==========
class StabilityTrendDataPoint(BaseModel):
    """趋势分析数据点"""
    model_config = ConfigDict(from_attributes=True)
    inspection_item: str
    node_month: int
    measured_value: Optional[str] = None
    result: Optional[StabilityItemResult] = None
    inspection_date: Optional[datetime] = None


class StabilityTrendResponse(BaseModel):
    """趋势分析响应"""
    product_code: str
    product_name: Optional[str] = None
    batch_no: str
    study_type: StabilityStudyType
    inspection_items: list[str]
    data_points: dict[int, list[StabilityTrendDataPoint]]  # node_month -> data points
