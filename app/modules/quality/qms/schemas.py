"""Quality request and response schemas live here."""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class MaterialCategory(str, Enum):
    """物料分类"""

    RAW_MATERIAL = "raw_material"  # 原料
    EXCIPIENT = "excipient"  # 辅料
    PACKAGING_MATERIAL = "packaging_material"  # 包装材料
    INTERMEDIATE = "intermediate"  # 中间体
    FINISHED_PRODUCT = "finished_product"  # 原料药成品


class Pharmacopeia(str, Enum):
    """执行药典"""

    CHP = "ChP"  # 中国药典
    USP = "USP"  # 美国药典
    EP = "EP"  # 欧洲药典
    BP = "BP"  # 英国药典
    INTERNAL = "internal"  # 企业内控


class StandardStatus(str, Enum):
    """标准状态"""

    DRAFT = "draft"  # 草稿
    TECH_REVIEW = "tech_review"  # 技术部门审核
    QA_REVIEW = "qa_review"  # QA审核
    APPROVED = "approved"  # 已批准
    EFFECTIVE = "effective"  # 已生效
    OBSOLETE = "obsolete"  # 已作废
    REJECTED = "rejected"  # 已驳回


class LimitType(str, Enum):
    """限度类型"""

    UPPER_LIMIT = "upper_limit"  # 上限
    LOWER_LIMIT = "lower_limit"  # 下限
    RANGE = "range"  # 区间
    NOT_DETECTABLE = "not_detectable"  # 不得检出


class ItemCategory(str, Enum):
    """项目分类"""

    PHYSICAL_CHEMICAL = "physical_chemical"  # 理化
    RELATED_SUBSTANCES = "related_substances"  # 有关物质
    RESIDUAL_SOLVENTS = "residual_solvents"  # 残留溶剂
    MICROBIAL = "microbial"  # 微生物


class ApprovalStatus(str, Enum):
    """审批状态"""

    PENDING = "pending"  # 待审批
    APPROVED = "approved"  # 已批准
    REJECTED = "rejected"  # 已驳回


# ============ InspectionStandard Schemas ============


class InspectionStandardItemBase(BaseModel):
    """检验项目基础模式"""

    item_no: int = Field(..., ge=1, description="项目序号")
    item_name: str = Field(..., max_length=255, description="项目名称")
    test_method: str | None = Field(None, description="检测方法")
    instrument_code: str | None = Field(None, max_length=64, description="关联仪器编号")
    reference_materials: str | None = Field(None, max_length=500, description="所需对照品/试液")
    limit_type: LimitType = Field(..., description="限度类型")
    limit_value: str | None = Field(None, max_length=255, description="合格限值")
    item_category: ItemCategory | None = Field(None, description="项目分类")
    is_critical: bool = Field(False, description="是否关键项目")
    notes: str | None = Field(None, description="备注")


class InspectionStandardItemCreate(InspectionStandardItemBase):
    """创建检验项目"""

    pass


class InspectionStandardItemUpdate(BaseModel):
    """更新检验项目"""

    item_no: int | None = Field(None, ge=1, description="项目序号")
    item_name: str | None = Field(None, max_length=255, description="项目名称")
    test_method: str | None = Field(None, description="检测方法")
    instrument_code: str | None = Field(None, max_length=64, description="关联仪器编号")
    reference_materials: str | None = Field(None, max_length=500, description="所需对照品/试液")
    limit_type: LimitType | None = Field(None, description="限度类型")
    limit_value: str | None = Field(None, max_length=255, description="合格限值")
    item_category: ItemCategory | None = Field(None, description="项目分类")
    is_critical: bool | None = Field(None, description="是否关键项目")
    notes: str | None = Field(None, description="备注")


class InspectionStandardItemResponse(InspectionStandardItemBase):
    """检验项目响应"""

    id: uuid.UUID
    standard_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InspectionStandardBase(BaseModel):
    """检验标准基础模式"""

    material_code: str = Field(..., max_length=64, description="物料编码")
    material_name: str | None = Field(None, max_length=255, description="物料名称")
    cas_no: str | None = Field(None, max_length=32, description="CAS号")
    material_category: MaterialCategory = Field(..., description="物料分类")
    pharmacopeia: Pharmacopeia | None = Field(None, description="执行药典")
    version: str = Field("1.0", max_length=20, description="版本号")
    effective_date: datetime | None = Field(None, description="生效日期")
    obsolete_date: datetime | None = Field(None, description="作废日期")
    sop_no: str | None = Field(None, max_length=64, description="SOP编号")
    attachment_urls: str | None = Field(None, description="附件URLs(JSON)")
    notes: str | None = Field(None, description="备注")


class InspectionStandardCreate(InspectionStandardBase):
    """创建检验标准"""

    items: list[InspectionStandardItemCreate] = Field(default_factory=list, description="检验项目列表")


class InspectionStandardUpdate(BaseModel):
    """更新检验标准"""

    material_code: str | None = Field(None, max_length=64, description="物料编码")
    material_name: str | None = Field(None, max_length=255, description="物料名称")
    cas_no: str | None = Field(None, max_length=32, description="CAS号")
    material_category: MaterialCategory | None = Field(None, description="物料分类")
    pharmacopeia: Pharmacopeia | None = Field(None, description="执行药典")
    version: str | None = Field(None, max_length=20, description="版本号")
    effective_date: datetime | None = Field(None, description="生效日期")
    obsolete_date: datetime | None = Field(None, description="作废日期")
    is_obsolete: bool | None = Field(None, description="是否作废")
    obsolete_reason: str | None = Field(None, description="作废原因")
    sop_no: str | None = Field(None, max_length=64, description="SOP编号")
    attachment_urls: str | None = Field(None, description="附件URLs(JSON)")
    notes: str | None = Field(None, description="备注")
    items: list[InspectionStandardItemCreate] | None = Field(None, description="检验项目列表")


class InspectionStandardCopy(BaseModel):
    """复制检验标准"""

    source_id: uuid.UUID = Field(..., description="源标准ID")
    new_version: str = Field(..., max_length=20, description="新版本号")


class InspectionStandardResponse(InspectionStandardBase):
    """检验标准响应"""

    id: uuid.UUID
    standard_no: str
    status: StandardStatus
    is_obsolete: bool
    obsolete_reason: str | None = None
    source_version: str | None = None
    created_at: datetime
    updated_at: datetime
    items: list[InspectionStandardItemResponse] = []

    class Config:
        from_attributes = True


# ============ Approval Schemas ============


class ApprovalRecordBase(BaseModel):
    """审批记录基础模式"""

    approval_level: int = Field(..., ge=1, description="审批层级")
    approval_status: ApprovalStatus = Field(..., description="审批状态")
    approver_role: str | None = Field(None, max_length=64, description="审批人角色")
    comments: str | None = Field(None, description="审批意见")


class ApprovalRecordCreate(ApprovalRecordBase):
    """创建审批记录"""

    standard_id: uuid.UUID


class ApprovalRecordResponse(ApprovalRecordBase):
    """审批记录响应"""

    id: uuid.UUID
    standard_id: uuid.UUID
    approver_id: uuid.UUID | None = None
    approver_name: str | None = None
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApprovalSubmit(BaseModel):
    """提交审批"""

    pass


class ObsoleteSubmit(BaseModel):
    """提交作废"""

    obsolete_reason: str = Field(..., description="作废原因")