"""IQC (Incoming Quality Control) inspection schemas"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ========== Enums ==========
class SourceType(str, Enum):
    """来源类型"""
    PURCHASE_INBOUND = "purchase_inbound"  # 采购到货
    SUPPLIER_DELIVERY = "supplier_delivery"  # 供应商直送


class MaterialCategory(str, Enum):
    """物料类别"""
    RAW_MATERIAL = "raw_material"  # 原料药
    EXCIPIENT = "excipient"  # 辅料
    PACKAGING_MATERIAL = "packaging_material"  # 包装材料


class InspectionStatus(str, Enum):
    """检验单状态"""
    DRAFT = "draft"  # 草稿
    SUBMITTED = "submitted"  # 已提交
    DEPARTMENT_APPROVED = "department_approved"  # 部门负责人已审核
    QA_APPROVED = "qa_approved"  # QA已审核
    FINAL_APPROVED = "final_approved"  # 质量负责人终审通过
    REJECTED = "rejected"  # 驳回


class InspectionConclusion(str, Enum):
    """检验结论"""
    QUALIFIED = "qualified"  # 合格
    UNQUALIFIED = "unqualified"  # 不合格
    CONDITIONAL = "conditional"  # 条件合格


class ItemResult(str, Enum):
    """单项判定"""
    PASS = "pass"  # 合格
    FAIL = "fail"  # 不合格
    NA = "na"  # 不适用


class ApprovalStatus(str, Enum):
    """审批状态"""
    PENDING = "pending"  # 待审批
    APPROVED = "approved"  # 已批准
    REJECTED = "rejected"  # 驳回


# ========== IQC Inspection Item Schemas ==========
class IQCInspectionItemBase(BaseModel):
    """IQC检验明细基础Schema"""
    item_no: int = Field(..., description="项次")
    inspection_item: str = Field(..., description="检验项目名称")
    inspection_method: Optional[str] = Field(None, description="检验方法")
    standard_value: Optional[str] = Field(None, description="标准值")
    unit: Optional[str] = Field(None, description="单位")
    measured_value: Optional[str] = Field(None, description="实测值")
    result: Optional[ItemResult] = Field(None, description="单项判定")
    is_repeat_test: bool = Field(False, description="是否复测")
    raw_data: Optional[str] = Field(None, description="原始数据记录")
    remark: Optional[str] = Field(None, description="备注")


class IQCInspectionItemCreate(IQCInspectionItemBase):
    """创建IQC检验明细"""
    pass


class IQCInspectionItemUpdate(IQCInspectionItemBase):
    """更新IQC检验明细"""
    id: Optional[UUID] = None


class IQCInspectionItemResponse(IQCInspectionItemBase):
    """IQC检验明细响应"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    iqc_inspection_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None


# ========== IQC Inspection Schemas ==========
class IQCInspectionBase(BaseModel):
    """IQC检验基础Schema"""
    # 来源信息
    source_type: SourceType = Field(..., description="来源类型")
    source_no: Optional[str] = Field(None, description="来源单号")
    sampling_order_id: Optional[UUID] = Field(None, description="关联取样单ID")
    sampling_order_no: Optional[str] = Field(None, description="关联取样单号")

    # 物料信息
    material_code: str = Field(..., description="物料编码")
    material_name: Optional[str] = Field(None, description="物料名称")
    material_category: Optional[MaterialCategory] = Field(None, description="物料类别")
    specification: Optional[str] = Field(None, description="规格")
    batch_no: Optional[str] = Field(None, description="批次号")
    supplier_code: Optional[str] = Field(None, description="供应商编码")
    supplier_name: Optional[str] = Field(None, description="供应商名称")
    manufacturing_date: Optional[datetime] = Field(None, description="生产日期")
    expiry_date: Optional[datetime] = Field(None, description="有效期")
    quantity_received: Optional[Decimal] = Field(None, description="到货数量")
    unit: Optional[str] = Field(None, description="单位")

    # 检验信息
    inspection_date: Optional[datetime] = Field(None, description="检验日期")
    inspector_id: Optional[UUID] = Field(None, description="检验员ID")
    inspector_name: Optional[str] = Field(None, description="检验员姓名")

    # 质量标准
    standard_id: Optional[UUID] = Field(None, description="检验标准ID")
    standard_name: Optional[str] = Field(None, description="检验标准名称")
    standard_version: Optional[str] = Field(None, description="标准版本")

    # 检验结论
    inspection_conclusion: Optional[InspectionConclusion] = Field(None, description="检验结论")
    remark: Optional[str] = Field(None, description="备注")


class IQCInspectionCreate(IQCInspectionBase):
    """创建IQC检验单"""
    items: list[IQCInspectionItemCreate] = Field(default_factory=list, description="检验明细")


class IQCInspectionUpdate(BaseModel):
    """更新IQC检验单"""
    source_type: Optional[SourceType] = None
    source_no: Optional[str] = None
    sampling_order_id: Optional[UUID] = None
    sampling_order_no: Optional[str] = None
    material_code: Optional[str] = None
    material_name: Optional[str] = None
    material_category: Optional[MaterialCategory] = None
    specification: Optional[str] = None
    batch_no: Optional[str] = None
    supplier_code: Optional[str] = None
    supplier_name: Optional[str] = None
    manufacturing_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    quantity_received: Optional[Decimal] = None
    unit: Optional[str] = None
    inspection_date: Optional[datetime] = None
    inspector_id: Optional[UUID] = None
    inspector_name: Optional[str] = None
    standard_id: Optional[UUID] = None
    standard_name: Optional[str] = None
    standard_version: Optional[str] = None
    inspection_conclusion: Optional[InspectionConclusion] = None
    remark: Optional[str] = None
    items: Optional[list[IQCInspectionItemCreate]] = None


class IQCInspectionResponse(IQCInspectionBase):
    """IQC检验单响应"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    inspection_no: str
    status: InspectionStatus
    deviation_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    items: list[IQCInspectionItemResponse] = []


class IQCInspectionListResponse(BaseModel):
    """IQC检验单列表响应"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    inspection_no: str
    source_type: SourceType
    source_no: Optional[str] = None
    material_code: str
    material_name: Optional[str] = None
    material_category: Optional[MaterialCategory] = None
    batch_no: Optional[str] = None
    supplier_name: Optional[str] = None
    inspection_date: Optional[datetime] = None
    inspector_name: Optional[str] = None
    status: InspectionStatus
    inspection_conclusion: Optional[InspectionConclusion] = None
    created_at: datetime


# ========== Approval Schemas ==========
class IQCApprovalCreate(BaseModel):
    """IQC审批"""
    approval_status: ApprovalStatus = Field(..., description="审批状态")
    comments: Optional[str] = Field(None, description="审批意见")


class IQCApprovalRecordResponse(BaseModel):
    """审批记录响应"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    iqc_inspection_id: UUID
    approval_level: int
    approval_status: ApprovalStatus
    approver_role: Optional[str] = None
    approver_id: Optional[UUID] = None
    approver_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    comments: Optional[str] = None
    created_at: datetime


# ========== Filter Schemas ==========
class IQCInspectionFilter(BaseModel):
    """IQC检验单筛选条件"""
    material_code: Optional[str] = None
    material_name: Optional[str] = None
    material_category: Optional[MaterialCategory] = None
    supplier_name: Optional[str] = None
    status: Optional[InspectionStatus] = None
    inspection_conclusion: Optional[InspectionConclusion] = None
    inspection_no: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None