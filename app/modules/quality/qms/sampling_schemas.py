"""Sampling management schemas"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
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
    sampling_count: int | None = Field(None, description="取样份数")
    retention_count: int | None = Field(None, description="留样份数")
    retention_location: str | None = Field(None, description="留样存放位置")
    sample_status: SampleStatus | None = Field(None, description="样品状态")
    retention_date: datetime | None = Field(None, description="留样日期")
    expiry_date: datetime | None = Field(None, description="留样有效期")
    remark: str | None = Field(None, description="备注")


class SamplingOrderItemCreate(SamplingOrderItemBase):
    """创建取样明细"""

    # sample_no 由服务层自动生成,此处设为可选
    sample_no: str | None = Field(None, description="样品编号(自动生成)")


class SamplingOrderItemUpdate(SamplingOrderItemBase):
    """更新取样明细"""

    id: UUID | None = None


class SamplingOrderItemResponse(SamplingOrderItemBase):
    """取样明细响应"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    sampling_order_id: UUID
    is_expired: bool
    disposal_date: datetime | None = None
    disposal_method: str | None = None


class SamplingOrderBase(BaseModel):
    """取样单基础Schema"""

    source_type: SourceType = Field(..., description="来源类型")
    source_no: str | None = Field(None, description="关联单号")
    material_code: str = Field(..., description="物料编码")
    material_name: str | None = Field(None, description="物料名称")
    material_category: str | None = Field(None, description="物料类别")
    batch_no: str | None = Field(None, description="批次号")
    specification: str | None = Field(None, description="规格")
    unit: str | None = Field(None, description="单位")
    quantity: Decimal | None = Field(None, description="批量/数量")
    sampling_source: SamplingSource = Field(..., description="取样来源")
    sampling_quantity: Decimal | None = Field(None, description="取样量")
    sampling_location: str | None = Field(None, description="取样地点")
    sampling_date: datetime | None = Field(None, description="取样日期")
    sampler_id: UUID | None = Field(None, description="取样人ID")
    sampler_name: str | None = Field(None, description="取样人姓名")
    sampling_result: SamplingResult | None = Field(None, description="取样判定")
    exception_reasons: str | None = Field(None, description="异常原因(JSON数组)")
    remark: str | None = Field(None, description="备注")


class SamplingOrderCreate(SamplingOrderBase):
    """创建取样单"""

    items: list[SamplingOrderItemCreate] = Field(
        default_factory=list, description="取样明细"
    )


class SamplingOrderUpdate(BaseModel):
    """更新取样单"""

    source_type: SourceType | None = None
    source_no: str | None = None
    material_code: str | None = None
    material_name: str | None = None
    material_category: str | None = None
    batch_no: str | None = None
    specification: str | None = None
    unit: str | None = None
    quantity: Decimal | None = None
    sampling_source: SamplingSource | None = None
    sampling_quantity: Decimal | None = None
    sampling_location: str | None = None
    sampling_date: datetime | None = None
    sampler_id: UUID | None = None
    sampler_name: str | None = None
    sampling_result: SamplingResult | None = None
    exception_reasons: str | None = None
    remark: str | None = None
    items: list[SamplingOrderItemCreate] | None = None


class SamplingOrderResponse(SamplingOrderBase):
    """取样单响应"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    order_no: str
    status: SamplingStatus
    deviation_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None
    items: list[SamplingOrderItemResponse] = []


class SamplingOrderListResponse(BaseModel):
    """取样单列表响应"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    order_no: str
    source_type: SourceType
    source_no: str | None = None
    material_code: str
    material_name: str | None = None
    material_category: str | None = None
    batch_no: str | None = None
    sampling_source: SamplingSource
    sampling_date: datetime | None = None
    sampler_name: str | None = None
    status: SamplingStatus
    sampling_result: SamplingResult | None = None
    created_at: datetime


# ========== Approval Schemas ==========
class SamplingApprovalCreate(BaseModel):
    """取样审批"""

    approval_status: ApprovalStatus = Field(..., description="审批状态")
    comments: str | None = Field(None, description="审批意见")


class SamplingApprovalRecordResponse(BaseModel):
    """审批记录响应"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    sampling_order_id: UUID
    approval_level: int
    approval_status: ApprovalStatus
    approver_role: str | None = None
    approver_id: UUID | None = None
    approver_name: str | None = None
    approved_at: datetime | None = None
    comments: str | None = None
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
    material_name: str | None = None
    batch_no: str | None = None
    retention_count: int | None = None
    retention_location: str | None = None
    retention_date: datetime | None = None
    expiry_date: datetime | None = None
    retention_status: RetentionStatus
    disposal_date: datetime | None = None
    disposal_method: str | None = None
    disposal_remark: str | None = None
    remark: str | None = None
    created_at: datetime


# ========== Filter Schemas ==========
class SamplingOrderFilter(BaseModel):
    """取样单筛选条件"""

    material_code: str | None = None
    material_name: str | None = None
    sampling_source: SamplingSource | None = None
    status: SamplingStatus | None = None
    sampling_result: SamplingResult | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    order_no: str | None = None


class RetentionLedgerFilter(BaseModel):
    """留样台账筛选条件"""

    material_code: str | None = None
    material_name: str | None = None
    retention_status: RetentionStatus | None = None
    order_no: str | None = None
    sample_no: str | None = None
