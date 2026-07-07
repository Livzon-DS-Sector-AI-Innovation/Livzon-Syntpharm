"""Stability Study (稳定性试验) schemas"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
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
    node_name: str | None = Field(None, description="节点名称")
    planned_date: datetime | None = Field(None, description="计划取样日期")
    actual_date: datetime | None = Field(None, description="实际取样日期")
    status: SampleNodeStatus = Field(SampleNodeStatus.PENDING, description="状态")
    remark: str | None = Field(None, description="备注")


class StabilitySampleNodeCreate(StabilitySampleNodeBase):
    """创建取样节点"""

    pass


class StabilitySampleNodeUpdate(BaseModel):
    """更新取样节点"""

    node_no: int | None = None
    node_month: int | None = None
    node_name: str | None = None
    planned_date: datetime | None = None
    actual_date: datetime | None = None
    status: SampleNodeStatus | None = None
    remark: str | None = None


class StabilitySampleNodeResponse(StabilitySampleNodeBase):
    """取样节点响应"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    stability_study_id: UUID
    reminder_sent: bool = False
    reminder_date: datetime | None = None
    inspection_id: UUID | None = None
    inspection_no: str | None = None
    inspection_status: str | None = None
    inspection_conclusion: str | None = None
    created_at: datetime
    updated_at: datetime


# ========== Inspection Item Schemas ==========
class StabilityInspectionItemBase(BaseModel):
    """检验明细基础Schema"""

    item_no: int = Field(..., description="项次")
    inspection_item: str = Field(..., description="检验项目名称")
    inspection_method: str | None = Field(None, description="检验方法")
    standard_value: str | None = Field(None, description="标准值/限度")
    unit: str | None = Field(None, description="单位")
    measured_value: str | None = Field(None, description="实测值")
    result: StabilityItemResult | None = Field(None, description="单项判定")
    is_oos: bool = Field(False, description="是否超标")
    oos_description: str | None = Field(None, description="超标描述")
    data_point: str | None = Field(None, description="数据点")
    chromatogram_urls: str | None = Field(None, description="图谱附件JSON")
    remark: str | None = Field(None, description="备注")


class StabilityInspectionItemCreate(StabilityInspectionItemBase):
    """创建检验明细"""

    pass


class StabilityInspectionItemUpdate(StabilityInspectionItemBase):
    """更新检验明细"""

    id: UUID | None = None


class StabilityInspectionItemResponse(StabilityInspectionItemBase):
    """检验明细响应"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    stability_inspection_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None


# ========== Stability Inspection Schemas ==========
class StabilityInspectionBase(BaseModel):
    """检验记录基础Schema"""

    inspection_date: datetime | None = Field(None, description="检验日期")
    inspector_id: UUID | None = Field(None, description="检验员ID")
    inspector_name: str | None = Field(None, description="检验员")
    sample_quantity: Decimal | None = Field(None, description="取样数量")
    sample_no: str | None = Field(None, description="样品编号")
    sample_condition: str | None = Field(None, description="样品状态")
    standard_id: UUID | None = Field(None, description="检验标准ID")
    standard_name: str | None = Field(None, description="质量标准名称")
    inspection_conclusion: StabilityInspectionConclusion | None = Field(
        None, description="检验结论"
    )
    conclusion_reason: str | None = Field(None, description="结论说明")
    remark: str | None = Field(None, description="备注")
    oos_report_no: str | None = Field(None, description="OOS报告编号")
    attachments: str | None = Field(None, description="附件JSON")


class StabilityInspectionCreate(StabilityInspectionBase):
    """创建检验记录"""

    study_id: UUID = Field(..., description="稳定性试验ID")
    sample_node_id: UUID = Field(..., description="取样节点ID")
    items: list[StabilityInspectionItemCreate] = Field(
        default_factory=list, description="检验明细"
    )


class StabilityInspectionUpdate(BaseModel):
    """更新检验记录"""

    inspection_date: datetime | None = None
    inspector_id: UUID | None = None
    inspector_name: str | None = None
    sample_quantity: Decimal | None = None
    sample_no: str | None = None
    sample_condition: str | None = None
    standard_id: UUID | None = None
    standard_name: str | None = None
    inspection_conclusion: StabilityInspectionConclusion | None = None
    conclusion_reason: str | None = None
    remark: str | None = None
    oos_report_no: str | None = None
    attachments: str | None = None
    items: list[StabilityInspectionItemCreate] | None = None


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
    product_name: str | None = None
    batch_no: str
    specification: str | None = None
    status: StabilityInspectionStatus
    is_oos: bool = False
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None
    items: list[StabilityInspectionItemResponse] = []


class StabilityInspectionListResponse(BaseModel):
    """检验记录列表响应"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    inspection_no: str
    study_no: str
    node_month: int
    product_code: str
    product_name: str | None = None
    batch_no: str
    inspection_date: datetime | None = None
    inspector_name: str | None = None
    status: StabilityInspectionStatus
    inspection_conclusion: StabilityInspectionConclusion | None = None
    created_at: datetime


# ========== Stability Study Schemas ==========
class StabilityStudyBase(BaseModel):
    """稳定性试验基础Schema"""

    product_code: str = Field(..., description="产品编码")
    product_name: str | None = Field(None, description="产品名称")
    product_category: str | None = Field(None, description="产品类别")
    batch_no: str = Field(..., description="批号")
    batch_quantity: Decimal | None = Field(None, description="批量")
    packaging_spec: str | None = Field(None, description="包装规格")
    study_type: StabilityStudyType = Field(..., description="试验类型")
    temperature: str | None = Field(None, description="温度条件")
    humidity: str | None = Field(None, description="湿度条件")
    start_date: datetime | None = Field(None, description="试验开始日期")
    end_date: datetime | None = Field(None, description="试验结束日期")
    expiry_date: datetime | None = Field(None, description="有效期")
    sample_intervals: str | list[int] | None = Field(
        None, description="取样周期节点，逗号分隔或数组"
    )
    standard_id: UUID | None = Field(None, description="检验标准ID")
    standard_name: str | None = Field(None, description="质量标准名称")
    standard_version: str | None = Field(None, description="标准版本")
    developer_id: UUID | None = Field(None, description="研发人员ID")
    developer_name: str | None = Field(None, description="研发人员")
    study_conclusion: StabilityStudyConclusion | None = Field(
        None, description="试验结论"
    )
    conclusion_reason: str | None = Field(None, description="结论说明")
    remark: str | None = Field(None, description="备注")
    attachments: str | None = Field(None, description="附件JSON")


class StabilityStudyCreate(StabilityStudyBase):
    """创建稳定性试验"""

    sample_nodes: list[StabilitySampleNodeCreate] = Field(
        default_factory=list, description="取样节点列表"
    )


class StabilityStudyUpdate(BaseModel):
    """更新稳定性试验"""

    product_code: str | None = None
    product_name: str | None = None
    product_category: str | None = None
    batch_no: str | None = None
    batch_quantity: Decimal | None = None
    packaging_spec: str | None = None
    study_type: StabilityStudyType | None = None
    temperature: str | None = None
    humidity: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    expiry_date: datetime | None = None
    sample_intervals: str | None = None
    standard_id: UUID | None = None
    standard_name: str | None = None
    standard_version: str | None = None
    developer_id: UUID | None = None
    developer_name: str | None = None
    study_conclusion: StabilityStudyConclusion | None = None
    conclusion_reason: str | None = None
    remark: str | None = None
    attachments: str | None = None
    sample_nodes: list[StabilitySampleNodeCreate] | None = None


class StabilityStudyResponse(StabilityStudyBase):
    """稳定性试验响应"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    study_no: str
    status: StabilityStudyStatus
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None
    sample_nodes: list[StabilitySampleNodeResponse] = []


class StabilityStudyListResponse(BaseModel):
    """稳定性试验列表响应"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    study_no: str
    product_code: str
    product_name: str | None = None
    batch_no: str
    study_type: StabilityStudyType
    status: StabilityStudyStatus
    start_date: datetime | None = None
    end_date: datetime | None = None
    expiry_date: datetime | None = None
    developer_name: str | None = None
    study_conclusion: StabilityStudyConclusion | None = None
    created_at: datetime


# ========== Approval Schemas ==========
class StabilityApprovalCreate(BaseModel):
    """稳定性审批"""

    approval_status: StabilityApprovalStatus = Field(..., description="审批状态")
    comments: str | None = Field(None, description="审批意见")


class StabilityApprovalRecordResponse(BaseModel):
    """审批记录响应"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    study_id: UUID | None = None
    inspection_id: UUID | None = None
    approval_type: StabilityApprovalType
    approval_level: int
    approval_status: StabilityApprovalStatus
    approver_role: str | None = None
    approver_id: UUID | None = None
    approver_name: str | None = None
    approved_at: datetime | None = None
    comments: str | None = None
    created_at: datetime


# ========== Filter Schemas ==========
class StabilityStudyFilter(BaseModel):
    """稳定性试验筛选条件"""

    study_no: str | None = None
    product_code: str | None = None
    product_name: str | None = None
    batch_no: str | None = None
    study_type: StabilityStudyType | None = None
    status: StabilityStudyStatus | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None


class StabilityInspectionFilter(BaseModel):
    """稳定性检验筛选条件"""

    study_id: UUID | None = None
    study_no: str | None = None
    inspection_no: str | None = None
    batch_no: str | None = None
    status: StabilityInspectionStatus | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None


# ========== Trend Analysis Schemas ==========
class StabilityTrendDataPoint(BaseModel):
    """趋势分析数据点"""

    model_config = ConfigDict(from_attributes=True)
    inspection_item: str
    node_month: int
    measured_value: str | None = None
    result: StabilityItemResult | None = None
    inspection_date: datetime | None = None


class StabilityTrendResponse(BaseModel):
    """趋势分析响应"""

    product_code: str
    product_name: str | None = None
    batch_no: str
    study_type: StabilityStudyType
    inspection_items: list[str]
    data_points: dict[int, list[StabilityTrendDataPoint]]  # node_month -> data points
