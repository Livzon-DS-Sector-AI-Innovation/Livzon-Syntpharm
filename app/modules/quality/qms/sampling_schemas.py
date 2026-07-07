"""Sampling management schemas"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ========== Enums ==========
class SamplingSource(str, Enum):
    """取样来源"""
    PURCHASED_MATERIAL = "purchased_material"  # 外购原料
    WORKSHOP_INTERMEDIATE = "workshop_intermediate"  # 车间中间体
    FINISHED_PRODUCT = "finished_product"  # 成品


class SourceType(str, Enum):
    """来源类型"""
    PURCHASE_INBOUND = "purchase_inbound"  # 来料入库单
    BATCH_NO = "batch_no"  # 生产批号


class SamplingStatus(str, Enum):
    """取样单状态"""
    DRAFT = "draft"  # 草稿
    PENDING_WAREHOUSE = "pending_warehouse"  # 待仓储/生产审核
    PENDING_QA = "pending_qa"  # 待QA审核
    APPROVED = "approved"  # 已批准
    EFFECTIVE = "effective"  # 已生效
    REJECTED = "rejected"  # 驳回


class SamplingResult(str, Enum):
    """取样判定"""
    NORMAL = "normal"  # 正常取样
    ABNORMAL = "abnormal"  # 取样异常


class SampleStatus(str, Enum):
    """样品状态"""
    PENDING = "pending"  # 待留样
    RETAINED = "retained"  # 已留样
    USED = "used"  # 已使用
    EXPIRED = "expired"  # 已到期


class RetentionStatus(str, Enum):
    """留样状态"""
    RETAINED = "retained"  # 已留样
    EXPIRED = "expired"  # 已到期
    DISPOSED = "disposed"  # 已处置


class ApprovalStatus(str, Enum):
    """审批状态"""
    PENDING = "pending"  # 待审批
    APPROVED = "approved"  # 已批准
    REJECTED = "rejected"  # 驳回


# ========== Sampling Order Schemas ==========
class SamplingOrderItemBase(BaseModel):
    """取样明细基础Schema"""
    item_no: int = Field(..., description="项次")
    sample_no: str = Field(..., description="样品编号")
    sampling_count: Optional[int] = Field(None, description="取样份数")
    retention_count: Optional[int] = Field(None, description="留样份数")
    retention_location: Optional[str] = Field(None, description="留样存放位置")
    sample_status: Optional[SampleStatus] = Field(None, description="样品状态")
    retention_date: Optional[datetime] = Field(None, description="留样日期")
    expiry_date: Optional[datetime] = Field(None, description="留样有效期")
    remark: Optional[str] = Field(None, description="备注")


class SamplingOrderItemCreate(SamplingOrderItemBase):
    """创建取样明细"""
    # sample_no 由服务层自动生成,此处设为可选
    sample_no: Optional[str] = Field(None, description="样品编号(自动生成)")


class SamplingOrderItemUpdate(SamplingOrderItemBase):
    """更新取样明细"""
    id: Optional[UUID] = None


class SamplingOrderItemResponse(SamplingOrderItemBase):
    """取样明细响应"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    sampling_order_id: UUID
    is_expired: bool
    disposal_date: Optional[datetime] = None
    disposal_method: Optional[str] = None


class SamplingOrderBase(BaseModel):
    """取样单基础Schema"""
    source_type: SourceType = Field(..., description="来源类型")
    source_no: Optional[str] = Field(None, description="关联单号")
    material_code: str = Field(..., description="物料编码")
    material_name: Optional[str] = Field(None, description="物料名称")
    material_category: Optional[str] = Field(None, description="物料类别")
    batch_no: Optional[str] = Field(None, description="批次号")
    specification: Optional[str] = Field(None, description="规格")
    unit: Optional[str] = Field(None, description="单位")
    quantity: Optional[Decimal] = Field(None, description="批量/数量")
    sampling_source: SamplingSource = Field(..., description="取样来源")
    sampling_quantity: Optional[Decimal] = Field(None, description="取样量")
    sampling_location: Optional[str] = Field(None, description="取样地点")
    sampling_date: Optional[datetime] = Field(None, description="取样日期")
    sampler_id: Optional[UUID] = Field(None, description="取样人ID")
    sampler_name: Optional[str] = Field(None, description="取样人姓名")
    sampling_result: Optional[SamplingResult] = Field(None, description="取样判定")
    exception_reasons: Optional[str] = Field(None, description="异常原因(JSON数组)")
    remark: Optional[str] = Field(None, description="备注")


class SamplingOrderCreate(SamplingOrderBase):
    """创建取样单"""
    items: list[SamplingOrderItemCreate] = Field(default_factory=list, description="取样明细")


class SamplingOrderUpdate(BaseModel):
    """更新取样单"""
    source_type: Optional[SourceType] = None
    source_no: Optional[str] = None
    material_code: Optional[str] = None
    material_name: Optional[str] = None
    material_category: Optional[str] = None
    batch_no: Optional[str] = None
    specification: Optional[str] = None
    unit: Optional[str] = None
    quantity: Optional[Decimal] = None
    sampling_source: Optional[SamplingSource] = None
    sampling_quantity: Optional[Decimal] = None
    sampling_location: Optional[str] = None
    sampling_date: Optional[datetime] = None
    sampler_id: Optional[UUID] = None
    sampler_name: Optional[str] = None
    sampling_result: Optional[SamplingResult] = None
    exception_reasons: Optional[str] = None
    remark: Optional[str] = None
    items: Optional[list[SamplingOrderItemCreate]] = None


class SamplingOrderResponse(SamplingOrderBase):
    """取样单响应"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    order_no: str
    status: SamplingStatus
    deviation_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    items: list[SamplingOrderItemResponse] = []


class SamplingOrderListResponse(BaseModel):
    """取样单列表响应"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    order_no: str
    source_type: SourceType
    source_no: Optional[str] = None
    material_code: str
    material_name: Optional[str] = None
    material_category: Optional[str] = None
    batch_no: Optional[str] = None
    sampling_source: SamplingSource
    sampling_date: Optional[datetime] = None
    sampler_name: Optional[str] = None
    status: SamplingStatus
    sampling_result: Optional[SamplingResult] = None
    created_at: datetime


# ========== Approval Schemas ==========
class SamplingApprovalCreate(BaseModel):
    """取样审批"""
    approval_status: ApprovalStatus = Field(..., description="审批状态")
    comments: Optional[str] = Field(None, description="审批意见")


class SamplingApprovalRecordResponse(BaseModel):
    """审批记录响应"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    sampling_order_id: UUID
    approval_level: int
    approval_status: ApprovalStatus
    approver_role: Optional[str] = None
    approver_id: Optional[UUID] = None
    approver_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    comments: Optional[str] = None
    created_at: datetime


# ========== Retention Ledger Schemas ==========
class SampleRetentionLedgerResponse(BaseModel):
    """留样台账响应"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    sampling_item_id: UUID
    sampling_order_id: UUID
    order_no: str
    sample_no: str
    material_code: str
    material_name: Optional[str] = None
    batch_no: Optional[str] = None
    retention_count: Optional[int] = None
    retention_location: Optional[str] = None
    retention_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    retention_status: RetentionStatus
    disposal_date: Optional[datetime] = None
    disposal_method: Optional[str] = None
    disposal_remark: Optional[str] = None
    remark: Optional[str] = None
    created_at: datetime


# ========== Filter Schemas ==========
class SamplingOrderFilter(BaseModel):
    """取样单筛选条件"""
    material_code: Optional[str] = None
    material_name: Optional[str] = None
    sampling_source: Optional[SamplingSource] = None
    status: Optional[SamplingStatus] = None
    sampling_result: Optional[SamplingResult] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    order_no: Optional[str] = None


class RetentionLedgerFilter(BaseModel):
    """留样台账筛选条件"""
    material_code: Optional[str] = None
    material_name: Optional[str] = None
    retention_status: Optional[RetentionStatus] = None
    order_no: Optional[str] = None
    sample_no: Optional[str] = None
