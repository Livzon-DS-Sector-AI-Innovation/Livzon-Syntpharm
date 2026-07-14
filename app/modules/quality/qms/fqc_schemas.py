"""FQC (Finished Product Quality Control) inspection schemas"""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ========== Enums ==========
class FQCInspectionStatus(StrEnum):
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


class FQCInspectionConclusion(StrEnum):
    """FQC检验结论"""

    QUALIFIED = "qualified"  # 合格
    UNQUALIFIED = "unqualified"  # 不合格


class FQCItemResult(StrEnum):
    """FQC单项判定"""

    PASS = "pass"  # 合格
    FAIL = "fail"  # 不合格
    NA = "na"  # 不适用


class FQCReleaseStatus(StrEnum):
    """FQC放行状态"""

    PENDING_RELEASE = "pending_release"  # 待放行
    RELEASED = "released"  # 已放行
    NOT_RELEASED = "not_released"  # 未放行


class FQCApprovalStatus(StrEnum):
    """FQC审批状态"""

    PENDING = "pending"  # 待审批
    APPROVED = "approved"  # 已批准
    REJECTED = "rejected"  # 驳回


class FQCInspectionCategory(StrEnum):
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
    inspection_category: FQCInspectionCategory | None = Field(None, description="检验类别")
    inspection_item: str = Field(..., description="检验项目名称")
    inspection_method: str | None = Field(None, description="检验方法")
    standard_value: str | None = Field(None, description="标准值/限度")
    unit: str | None = Field(None, description="单位")
    measured_value: str | None = Field(None, description="实测值")
    result: FQCItemResult | None = Field(None, description="单项判定")
    is_oos: bool = Field(False, description="是否超标")
    oos_description: str | None = Field(None, description="超标描述")
    is_repeat_test: bool = Field(False, description="是否复测")
    repeat_times: int = Field(0, description="复测次数")
    chromatogram_urls: str | None = Field(None, description="图谱附件JSON")
    raw_record_url: str | None = Field(None, description="原始记录PDF URL")
    remark: str | None = Field(None, description="备注")


class FQCInspectionItemCreate(FQCInspectionItemBase):
    """创建FQC检验明细"""

    pass


class FQCInspectionItemUpdate(FQCInspectionItemBase):
    """更新FQC检验明细"""

    id: UUID | None = None


class FQCInspectionItemResponse(FQCInspectionItemBase):
    """FQC检验明细响应"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    fqc_inspection_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None


# ========== FQC Inspection Schemas ==========
class FQCInspectionBase(BaseModel):
    """FQC检验基础Schema"""

    # 单据关联
    batch_record_id: UUID | None = Field(None, description="关联批生产记录ID")
    batch_record_no: str | None = Field(None, description="批生产记录编号")
    batch_no: str | None = Field(None, description="成品生产批号")
    product_code: str = Field(..., description="成品物料编码")
    product_name: str | None = Field(None, description="产品名称")
    sampling_order_id: UUID | None = Field(None, description="入库取样单ID")
    sampling_order_no: str | None = Field(None, description="入库取样单号")
    batch_quantity: Decimal | None = Field(None, description="批量")
    production_workshop: str | None = Field(None, description="生产车间")

    # 基础信息
    cas_no: str | None = Field(None, description="CAS号")
    manufacturing_date: datetime | None = Field(None, description="生产日期")
    expiry_date: datetime | None = Field(None, description="有效期至")
    manufacturer: str | None = Field(None, description="生产厂家")
    specification: str | None = Field(None, description="产品规格/包装")

    # 检验信息
    inspection_date: datetime | None = Field(None, description="检验日期")
    inspector_id: UUID | None = Field(None, description="检验员ID")
    inspector_name: str | None = Field(None, description="检验员")

    # 质量标准
    standard_id: UUID | None = Field(None, description="检验标准ID")
    standard_name: str | None = Field(None, description="质量标准名称")
    standard_version: str | None = Field(None, description="标准版本")

    # 检验结论
    inspection_conclusion: FQCInspectionConclusion | None = Field(None, description="检验结论")
    conclusion_reason: str | None = Field(None, description="结论说明")
    remark: str | None = Field(None, description="备注")

    # OOS与偏差
    oos_report_no: str | None = Field(None, description="OOS报告编号")
    reinspection_applied: bool = Field(False, description="是否申请复检")
    reinspection_reason: str | None = Field(None, description="复检原因")

    # 附件
    attachments: str | None = Field(None, description="附件JSON")


class FQCInspectionCreate(FQCInspectionBase):
    """创建FQC检验单"""

    items: list[FQCInspectionItemCreate] = Field(default_factory=list, description="检验明细")


class FQCInspectionUpdate(BaseModel):
    """更新FQC检验单"""

    batch_record_id: UUID | None = None
    batch_record_no: str | None = None
    batch_no: str | None = None
    product_code: str | None = None
    product_name: str | None = None
    sampling_order_id: UUID | None = None
    sampling_order_no: str | None = None
    batch_quantity: Decimal | None = None
    production_workshop: str | None = None
    cas_no: str | None = None
    manufacturing_date: datetime | None = None
    expiry_date: datetime | None = None
    manufacturer: str | None = None
    specification: str | None = None
    inspection_date: datetime | None = None
    inspector_id: UUID | None = None
    inspector_name: str | None = None
    standard_id: UUID | None = None
    standard_name: str | None = None
    standard_version: str | None = None
    inspection_conclusion: FQCInspectionConclusion | None = None
    conclusion_reason: str | None = None
    remark: str | None = None
    oos_report_no: str | None = None
    reinspection_applied: bool | None = None
    reinspection_reason: str | None = None
    attachments: str | None = None
    items: list[FQCInspectionItemCreate] | None = None


class FQCInspectionResponse(FQCInspectionBase):
    """FQC检验单响应"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    inspection_no: str
    status: FQCInspectionStatus
    batch_locked: bool = False
    batch_lock_reason: str | None = None
    warehouse_isolation: bool = False
    release_status: FQCReleaseStatus | None = None
    release_reason: str | None = None
    deviation_id: UUID | None = None
    report_no: str | None = None
    report_url: str | None = None
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None
    items: list[FQCInspectionItemResponse] = []


class FQCInspectionListResponse(BaseModel):
    """FQC检验单列表响应"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    inspection_no: str
    batch_no: str | None = None
    product_code: str
    product_name: str | None = None
    production_workshop: str | None = None
    batch_quantity: Decimal | None = None
    manufacturing_date: datetime | None = None
    inspector_name: str | None = None
    inspection_date: datetime | None = None
    status: FQCInspectionStatus
    inspection_conclusion: FQCInspectionConclusion | None = None
    release_status: FQCReleaseStatus | None = None
    batch_locked: bool = False
    created_at: datetime


# ========== Approval Schemas ==========
class FQCApprovalCreate(BaseModel):
    """FQC审批"""

    approval_status: FQCApprovalStatus = Field(..., description="审批状态")
    comments: str | None = Field(None, description="审批意见")


class FQCApprovalRecordResponse(BaseModel):
    """FQC审批记录响应"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    fqc_inspection_id: UUID
    approval_level: int
    approval_status: FQCApprovalStatus
    approver_role: str | None = None
    approver_id: UUID | None = None
    approver_name: str | None = None
    approved_at: datetime | None = None
    comments: str | None = None
    created_at: datetime


# ========== Filter Schemas ==========
class FQCInspectionFilter(BaseModel):
    """FQC检验单筛选条件"""

    inspection_no: str | None = None
    batch_no: str | None = None
    product_code: str | None = None
    product_name: str | None = None
    production_workshop: str | None = None
    status: FQCInspectionStatus | None = None
    inspection_conclusion: FQCInspectionConclusion | None = None
    release_status: FQCReleaseStatus | None = None
    batch_locked: bool | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
