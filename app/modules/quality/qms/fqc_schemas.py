"""FQC (Finished Product Quality Control) inspection schemas"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ========== Enums ==========
class FQCInspectionStatus(str, Enum):
    """FQC检验单状态"""
    DRAFT = "draft"  # 草稿
    SUBMITTED = "submitted"  # 已提交
    QC_SUPERVISOR_APPROVED = "qc_supervisor_approved"  # QC主管已审核
    QA_APPROVED = "qa_approved"  # QA已审核
    FINAL_APPROVED = "final_approved"  # 质量负责人终审
    RELEASED = "released"  # 已放行
    LOCKED = "locked"  # 锁定
    CLOSED = "closed"  # 已关闭
    REJECTED = "rejected"  # 驳回


class FQCInspectionConclusion(str, Enum):
    """FQC检验结论"""
    QUALIFIED = "qualified"  # 合格
    UNQUALIFIED = "unqualified"  # 不合格


class FQCItemResult(str, Enum):
    """FQC单项判定"""
    PASS = "pass"  # 合格
    FAIL = "fail"  # 不合格
    NA = "na"  # 不适用


class FQCReleaseStatus(str, Enum):
    """FQC放行状态"""
    PENDING_RELEASE = "pending_release"  # 待放行
    RELEASED = "released"  # 已放行
    NOT_RELEASED = "not_released"  # 未放行


class FQCApprovalStatus(str, Enum):
    """FQC审批状态"""
    PENDING = "pending"  # 待审批
    APPROVED = "approved"  # 已批准
    REJECTED = "rejected"  # 驳回


class FQCInspectionCategory(str, Enum):
    """FQC检验类别"""
    CONTENT = "content"  # 含量
    RELATED_SUBSTANCES = "related_substances"  # 有关物质
    RESIDUAL_SOLVENTS = "residual_solvents"  # 残留溶剂
    PHYSICAL_CHEMICAL = "physical_chemical"  # 理化
    MICROBIOLOGY = "microbiology"  # 微生物


# ========== FQC Inspection Item Schemas ==========
class FQCInspectionItemBase(BaseModel):
    """FQC检验明细基础Schema"""
    item_no: int = Field(..., description="项次")
    inspection_category: Optional[FQCInspectionCategory] = Field(None, description="检验类别")
    inspection_item: str = Field(..., description="检验项目名称")
    inspection_method: Optional[str] = Field(None, description="检验方法")
    standard_value: Optional[str] = Field(None, description="标准值/限度")
    unit: Optional[str] = Field(None, description="单位")
    measured_value: Optional[str] = Field(None, description="实测值")
    result: Optional[FQCItemResult] = Field(None, description="单项判定")
    is_oos: bool = Field(False, description="是否超标")
    oos_description: Optional[str] = Field(None, description="超标描述")
    is_repeat_test: bool = Field(False, description="是否复测")
    repeat_times: int = Field(0, description="复测次数")
    chromatogram_urls: Optional[str] = Field(None, description="图谱附件JSON")
    raw_record_url: Optional[str] = Field(None, description="原始记录PDF URL")
    remark: Optional[str] = Field(None, description="备注")


class FQCInspectionItemCreate(FQCInspectionItemBase):
    """创建FQC检验明细"""
    pass


class FQCInspectionItemUpdate(FQCInspectionItemBase):
    """更新FQC检验明细"""
    id: Optional[UUID] = None


class FQCInspectionItemResponse(FQCInspectionItemBase):
    """FQC检验明细响应"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    fqc_inspection_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None


# ========== FQC Inspection Schemas ==========
class FQCInspectionBase(BaseModel):
    """FQC检验基础Schema"""
    # 单据关联
    batch_record_id: Optional[UUID] = Field(None, description="关联批生产记录ID")
    batch_record_no: Optional[str] = Field(None, description="批生产记录编号")
    batch_no: Optional[str] = Field(None, description="成品生产批号")
    product_code: str = Field(..., description="成品物料编码")
    product_name: Optional[str] = Field(None, description="产品名称")
    sampling_order_id: Optional[UUID] = Field(None, description="入库取样单ID")
    sampling_order_no: Optional[str] = Field(None, description="入库取样单号")
    batch_quantity: Optional[Decimal] = Field(None, description="批量")
    production_workshop: Optional[str] = Field(None, description="生产车间")

    # 基础信息
    cas_no: Optional[str] = Field(None, description="CAS号")
    manufacturing_date: Optional[datetime] = Field(None, description="生产日期")
    expiry_date: Optional[datetime] = Field(None, description="有效期至")
    manufacturer: Optional[str] = Field(None, description="生产厂家")
    specification: Optional[str] = Field(None, description="产品规格/包装")

    # 检验信息
    inspection_date: Optional[datetime] = Field(None, description="检验日期")
    inspector_id: Optional[UUID] = Field(None, description="检验员ID")
    inspector_name: Optional[str] = Field(None, description="检验员")

    # 质量标准
    standard_id: Optional[UUID] = Field(None, description="检验标准ID")
    standard_name: Optional[str] = Field(None, description="质量标准名称")
    standard_version: Optional[str] = Field(None, description="标准版本")

    # 检验结论
    inspection_conclusion: Optional[FQCInspectionConclusion] = Field(None, description="检验结论")
    conclusion_reason: Optional[str] = Field(None, description="结论说明")
    remark: Optional[str] = Field(None, description="备注")

    # OOS与偏差
    oos_report_no: Optional[str] = Field(None, description="OOS报告编号")
    reinspection_applied: bool = Field(False, description="是否申请复检")
    reinspection_reason: Optional[str] = Field(None, description="复检原因")

    # 附件
    attachments: Optional[str] = Field(None, description="附件JSON")


class FQCInspectionCreate(FQCInspectionBase):
    """创建FQC检验单"""
    items: list[FQCInspectionItemCreate] = Field(default_factory=list, description="检验明细")


class FQCInspectionUpdate(BaseModel):
    """更新FQC检验单"""
    batch_record_id: Optional[UUID] = None
    batch_record_no: Optional[str] = None
    batch_no: Optional[str] = None
    product_code: Optional[str] = None
    product_name: Optional[str] = None
    sampling_order_id: Optional[UUID] = None
    sampling_order_no: Optional[str] = None
    batch_quantity: Optional[Decimal] = None
    production_workshop: Optional[str] = None
    cas_no: Optional[str] = None
    manufacturing_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    manufacturer: Optional[str] = None
    specification: Optional[str] = None
    inspection_date: Optional[datetime] = None
    inspector_id: Optional[UUID] = None
    inspector_name: Optional[str] = None
    standard_id: Optional[UUID] = None
    standard_name: Optional[str] = None
    standard_version: Optional[str] = None
    inspection_conclusion: Optional[FQCInspectionConclusion] = None
    conclusion_reason: Optional[str] = None
    remark: Optional[str] = None
    oos_report_no: Optional[str] = None
    reinspection_applied: Optional[bool] = None
    reinspection_reason: Optional[str] = None
    attachments: Optional[str] = None
    items: Optional[list[FQCInspectionItemCreate]] = None


class FQCInspectionResponse(FQCInspectionBase):
    """FQC检验单响应"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    inspection_no: str
    status: FQCInspectionStatus
    batch_locked: bool = False
    batch_lock_reason: Optional[str] = None
    warehouse_isolation: bool = False
    release_status: Optional[FQCReleaseStatus] = None
    release_reason: Optional[str] = None
    deviation_id: Optional[UUID] = None
    report_no: Optional[str] = None
    report_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    items: list[FQCInspectionItemResponse] = []


class FQCInspectionListResponse(BaseModel):
    """FQC检验单列表响应"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    inspection_no: str
    batch_no: Optional[str] = None
    product_code: str
    product_name: Optional[str] = None
    production_workshop: Optional[str] = None
    batch_quantity: Optional[Decimal] = None
    manufacturing_date: Optional[datetime] = None
    inspector_name: Optional[str] = None
    inspection_date: Optional[datetime] = None
    status: FQCInspectionStatus
    inspection_conclusion: Optional[FQCInspectionConclusion] = None
    release_status: Optional[FQCReleaseStatus] = None
    batch_locked: bool = False
    created_at: datetime


# ========== Approval Schemas ==========
class FQCApprovalCreate(BaseModel):
    """FQC审批"""
    approval_status: FQCApprovalStatus = Field(..., description="审批状态")
    comments: Optional[str] = Field(None, description="审批意见")


class FQCApprovalRecordResponse(BaseModel):
    """FQC审批记录响应"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    fqc_inspection_id: UUID
    approval_level: int
    approval_status: FQCApprovalStatus
    approver_role: Optional[str] = None
    approver_id: Optional[UUID] = None
    approver_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    comments: Optional[str] = None
    created_at: datetime


# ========== Filter Schemas ==========
class FQCInspectionFilter(BaseModel):
    """FQC检验单筛选条件"""
    inspection_no: Optional[str] = None
    batch_no: Optional[str] = None
    product_code: Optional[str] = None
    product_name: Optional[str] = None
    production_workshop: Optional[str] = None
    status: Optional[FQCInspectionStatus] = None
    inspection_conclusion: Optional[FQCInspectionConclusion] = None
    release_status: Optional[FQCReleaseStatus] = None
    batch_locked: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
