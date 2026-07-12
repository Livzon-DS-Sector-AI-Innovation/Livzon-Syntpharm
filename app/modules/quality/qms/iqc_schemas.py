"""IQC (Incoming Quality Control) inspection schemas"""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ========== Enums ==========
class SourceType(StrEnum):
    """来源类型"""

    PURCHASE_INBOUND = "purchase_inbound"  # 采购到货
    SUPPLIER_DELIVERY = "supplier_delivery"  # 供应商直送


class MaterialCategory(StrEnum):
    """物料类别"""

    RAW_MATERIAL = "raw_material"  # 原料药
    EXCIPIENT = "excipient"  # 辅料
    PACKAGING_MATERIAL = "packaging_material"  # 包装材料


class InspectionStatus(StrEnum):
    """检验单状态"""

    DRAFT = "draft"  # 草稿
    SUBMITTED = "submitted"  # 已提交
    DEPARTMENT_APPROVED = "department_approved"  # 部门负责人已审核
    QA_APPROVED = "qa_approved"  # QA已审核
    FINAL_APPROVED = "final_approved"  # 质量负责人终审通过
    REJECTED = "rejected"  # 驳回


class InspectionConclusion(StrEnum):
    """检验结论"""

    QUALIFIED = "qualified"  # 合格
    UNQUALIFIED = "unqualified"  # 不合格
    CONDITIONAL = "conditional"  # 条件合格


class ItemResult(StrEnum):
    """单项判定"""

    PASS = "pass"  # 合格
    FAIL = "fail"  # 不合格
    NA = "na"  # 不适用


class ApprovalStatus(StrEnum):
    """审批状态"""

    PENDING = "pending"  # 待审批
    APPROVED = "approved"  # 已批准
    REJECTED = "rejected"  # 驳回


# ========== IQC Inspection Item Schemas ==========
class IQCInspectionItemBase(BaseModel):
    """IQC检验明细基础Schema"""

    item_no: int = Field(..., description="项次")
    inspection_item: str = Field(..., description="检验项目名称")
    inspection_method: str | None = Field(None, description="检验方法")
    standard_value: str | None = Field(None, description="标准值")
    unit: str | None = Field(None, description="单位")
    measured_value: str | None = Field(None, description="实测值")
    result: ItemResult | None = Field(None, description="单项判定")
    is_repeat_test: bool = Field(False, description="是否复测")
    raw_data: str | None = Field(None, description="原始数据记录")
    remark: str | None = Field(None, description="备注")


class IQCInspectionItemCreate(IQCInspectionItemBase):
    """创建IQC检验明细"""

    pass


class IQCInspectionItemUpdate(IQCInspectionItemBase):
    """更新IQC检验明细"""

    id: UUID | None = None


class IQCInspectionItemResponse(IQCInspectionItemBase):
    """IQC检验明细响应"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    iqc_inspection_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None


# ========== IQC Inspection Schemas ==========
class IQCInspectionBase(BaseModel):
    """IQC检验基础Schema"""

    # 来源信息
    source_type: SourceType = Field(..., description="来源类型")
    source_no: str | None = Field(None, description="来源单号")
    sampling_order_id: UUID | None = Field(None, description="关联取样单ID")
    sampling_order_no: str | None = Field(None, description="关联取样单号")

    # 物料信息
    material_code: str = Field(..., description="物料编码")
    material_name: str | None = Field(None, description="物料名称")
    material_category: MaterialCategory | None = Field(None, description="物料类别")
    specification: str | None = Field(None, description="规格")
    batch_no: str | None = Field(None, description="批次号")
    supplier_code: str | None = Field(None, description="供应商编码")
    supplier_name: str | None = Field(None, description="供应商名称")
    manufacturing_date: datetime | None = Field(None, description="生产日期")
    expiry_date: datetime | None = Field(None, description="有效期")
    quantity_received: Decimal | None = Field(None, description="到货数量")
    unit: str | None = Field(None, description="单位")

    # 检验信息
    inspection_date: datetime | None = Field(None, description="检验日期")
    inspector_id: UUID | None = Field(None, description="检验员ID")
    inspector_name: str | None = Field(None, description="检验员姓名")

    # 质量标准
    standard_id: UUID | None = Field(None, description="检验标准ID")
    standard_name: str | None = Field(None, description="检验标准名称")
    standard_version: str | None = Field(None, description="标准版本")

    # 检验结论
    inspection_conclusion: InspectionConclusion | None = Field(None, description="检验结论")
    remark: str | None = Field(None, description="备注")


class IQCInspectionCreate(IQCInspectionBase):
    """创建IQC检验单"""

    items: list[IQCInspectionItemCreate] = Field(default_factory=list, description="检验明细")


class IQCInspectionUpdate(BaseModel):
    """更新IQC检验单"""

    source_type: SourceType | None = None
    source_no: str | None = None
    sampling_order_id: UUID | None = None
    sampling_order_no: str | None = None
    material_code: str | None = None
    material_name: str | None = None
    material_category: MaterialCategory | None = None
    specification: str | None = None
    batch_no: str | None = None
    supplier_code: str | None = None
    supplier_name: str | None = None
    manufacturing_date: datetime | None = None
    expiry_date: datetime | None = None
    quantity_received: Decimal | None = None
    unit: str | None = None
    inspection_date: datetime | None = None
    inspector_id: UUID | None = None
    inspector_name: str | None = None
    standard_id: UUID | None = None
    standard_name: str | None = None
    standard_version: str | None = None
    inspection_conclusion: InspectionConclusion | None = None
    remark: str | None = None
    items: list[IQCInspectionItemCreate] | None = None


class IQCInspectionResponse(IQCInspectionBase):
    """IQC检验单响应"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    inspection_no: str
    status: InspectionStatus
    deviation_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None
    items: list[IQCInspectionItemResponse] = []


class IQCInspectionListResponse(BaseModel):
    """IQC检验单列表响应"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    inspection_no: str
    source_type: SourceType
    source_no: str | None = None
    material_code: str
    material_name: str | None = None
    material_category: MaterialCategory | None = None
    batch_no: str | None = None
    supplier_name: str | None = None
    inspection_date: datetime | None = None
    inspector_name: str | None = None
    status: InspectionStatus
    inspection_conclusion: InspectionConclusion | None = None
    created_at: datetime


# ========== Approval Schemas ==========
class IQCApprovalCreate(BaseModel):
    """IQC审批"""

    approval_status: ApprovalStatus = Field(..., description="审批状态")
    comments: str | None = Field(None, description="审批意见")


class IQCApprovalRecordResponse(BaseModel):
    """审批记录响应"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    iqc_inspection_id: UUID
    approval_level: int
    approval_status: ApprovalStatus
    approver_role: str | None = None
    approver_id: UUID | None = None
    approver_name: str | None = None
    approved_at: datetime | None = None
    comments: str | None = None
    created_at: datetime


# ========== Filter Schemas ==========
class IQCInspectionFilter(BaseModel):
    """IQC检验单筛选条件"""

    material_code: str | None = None
    material_name: str | None = None
    material_category: MaterialCategory | None = None
    supplier_name: str | None = None
    status: InspectionStatus | None = None
    inspection_conclusion: InspectionConclusion | None = None
    inspection_no: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
