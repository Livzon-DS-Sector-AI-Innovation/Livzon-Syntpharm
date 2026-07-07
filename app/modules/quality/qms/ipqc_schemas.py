"""IPQC (In-Process Quality Control) inspection schemas"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ========== Enums ==========
class IPQCInspectionStatus(str, Enum):
    """IPQC检验单状态"""
    DRAFT = "draft"  # 草稿
    SUBMITTED = "submitted"  # 已提交（等待车间工艺负责人审核）
    WORKSHOP_APPROVED = "workshop_approved"  # 车间工艺负责人已审核
    QC_SUPERVISOR_APPROVED = "qc_supervisor_approved"  # QC主管已复核
    QA_FINAL_APPROVED = "qa_final_approved"  # QA终审通过
    REJECTED = "rejected"  # 驳回


class IPQCInspectionConclusion(str, Enum):
    """IPQC检验结论"""
    QUALIFIED = "qualified"  # 合格
    UNQUALIFIED = "unqualified"  # 不合格
    CONDITIONAL = "conditional"  # 条件合格


class IPQCItemResult(str, Enum):
    """IPQC单项判定"""
    PASS = "pass"  # 合格
    FAIL = "fail"  # 不合格
    NA = "na"  # 不适用


class IPQCApprovalStatus(str, Enum):
    """IPQC审批状态"""
    PENDING = "pending"  # 待审批
    APPROVED = "approved"  # 已批准
    REJECTED = "rejected"  # 驳回


# ========== IPQC Inspection Item Schemas ==========
class IPQCInspectionItemBase(BaseModel):
    """IPQC检验明细基础Schema"""
    item_no: int = Field(..., description="项次")
    inspection_item: str = Field(..., description="检验项目名称")
    inspection_method: Optional[str] = Field(None, description="检验方法")
    standard_value: Optional[str] = Field(None, description="标准值")
    upper_limit: Optional[str] = Field(None, description="上限")
    lower_limit: Optional[str] = Field(None, description="下限")
    unit: Optional[str] = Field(None, description="单位")
    measured_value: Optional[str] = Field(None, description="实测值")
    result: Optional[IPQCItemResult] = Field(None, description="单项判定")
    is_repeat_test: bool = Field(False, description="是否复测")
    repeat_times: int = Field(0, description="复测次数")
    raw_data: Optional[str] = Field(None, description="原始数据记录")
    remark: Optional[str] = Field(None, description="备注")


class IPQCInspectionItemCreate(IPQCInspectionItemBase):
    """创建IPQC检验明细"""
    pass


class IPQCInspectionItemUpdate(IPQCInspectionItemBase):
    """更新IPQC检验明细"""
    id: Optional[UUID] = None


class IPQCInspectionItemResponse(IPQCInspectionItemBase):
    """IPQC检验明细响应"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    ipqc_inspection_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None


# ========== IPQC Inspection Schemas ==========
class IPQCInspectionBase(BaseModel):
    """IPQC检验基础Schema"""
    # 批次关联信息
    batch_record_id: Optional[UUID] = Field(None, description="关联批次生产记录ID")
    batch_record_no: Optional[str] = Field(None, description="批次生产记录单号")
    batch_no: Optional[str] = Field(None, description="批次号")
    product_code: str = Field(..., description="产品编码")
    product_name: Optional[str] = Field(None, description="产品名称")
    product_specification: Optional[str] = Field(None, description="产品规格")

    # 工序信息
    process_stage: Optional[str] = Field(None, description="工序/工段")
    sampling_point: Optional[str] = Field(None, description="取样点")
    sampling_no: Optional[str] = Field(None, description="取样单号")
    sampling_time: Optional[datetime] = Field(None, description="取样时间")
    sampling_quantity: Optional[Decimal] = Field(None, description="取样数量")
    sampling_unit: Optional[str] = Field(None, description="取样单位")
    sampling_location: Optional[str] = Field(None, description="取样位置")
    production_date: Optional[datetime] = Field(None, description="生产日期")

    # 检验信息
    inspection_date: Optional[datetime] = Field(None, description="检验日期")
    inspector_id: Optional[UUID] = Field(None, description="检验员ID")
    inspector_name: Optional[str] = Field(None, description="检验员姓名")

    # 质量标准
    standard_id: Optional[UUID] = Field(None, description="检验标准ID")
    standard_name: Optional[str] = Field(None, description="检验标准名称")
    standard_version: Optional[str] = Field(None, description="标准版本")

    # 检验结论
    inspection_conclusion: Optional[IPQCInspectionConclusion] = Field(None, description="检验结论")
    conclusion_reason: Optional[str] = Field(None, description="结论说明")
    remark: Optional[str] = Field(None, description="备注")
    oos_report_no: Optional[str] = Field(None, description="OOS报告编号")


class IPQCInspectionCreate(IPQCInspectionBase):
    """创建IPQC检验单"""
    items: list[IPQCInspectionItemCreate] = Field(default_factory=list, description="检验明细")


class IPQCInspectionUpdate(BaseModel):
    """更新IPQC检验单"""
    batch_record_id: Optional[UUID] = None
    batch_record_no: Optional[str] = None
    batch_no: Optional[str] = None
    product_code: Optional[str] = None
    product_name: Optional[str] = None
    product_specification: Optional[str] = None
    process_stage: Optional[str] = None
    sampling_point: Optional[str] = None
    sampling_no: Optional[str] = None
    sampling_time: Optional[datetime] = None
    sampling_quantity: Optional[Decimal] = None
    sampling_unit: Optional[str] = None
    sampling_location: Optional[str] = None
    production_date: Optional[datetime] = None
    inspection_date: Optional[datetime] = None
    inspector_id: Optional[UUID] = None
    inspector_name: Optional[str] = None
    standard_id: Optional[UUID] = None
    standard_name: Optional[str] = None
    standard_version: Optional[str] = None
    inspection_conclusion: Optional[IPQCInspectionConclusion] = None
    conclusion_reason: Optional[str] = None
    remark: Optional[str] = None
    oos_report_no: Optional[str] = None
    items: Optional[list[IPQCInspectionItemCreate]] = None


class IPQCInspectionResponse(IPQCInspectionBase):
    """IPQC检验单响应"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    inspection_no: str
    status: IPQCInspectionStatus
    batch_locked: bool = False
    batch_lock_reason: Optional[str] = None
    deviation_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    items: list[IPQCInspectionItemResponse] = []


class IPQCInspectionListResponse(BaseModel):
    """IPQC检验单列表响应"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    inspection_no: str
    batch_no: Optional[str] = None
    product_code: str
    product_name: Optional[str] = None
    product_specification: Optional[str] = None
    process_stage: Optional[str] = None
    sampling_point: Optional[str] = None
    sampling_time: Optional[datetime] = None
    inspector_name: Optional[str] = None
    status: IPQCInspectionStatus
    inspection_conclusion: Optional[IPQCInspectionConclusion] = None
    batch_locked: bool = False
    created_at: datetime


# ========== Approval Schemas ==========
class IPQCApprovalCreate(BaseModel):
    """IPQC审批"""
    approval_status: IPQCApprovalStatus = Field(..., description="审批状态")
    comments: Optional[str] = Field(None, description="审批意见")


class IPQCApprovalRecordResponse(BaseModel):
    """IPQC审批记录响应"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    ipqc_inspection_id: UUID
    approval_level: int
    approval_status: IPQCApprovalStatus
    approver_role: Optional[str] = None
    approver_id: Optional[UUID] = None
    approver_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    comments: Optional[str] = None
    created_at: datetime


# ========== Filter Schemas ==========
class IPQCInspectionFilter(BaseModel):
    """IPQC检验单筛选条件"""
    inspection_no: Optional[str] = None
    batch_no: Optional[str] = None
    product_code: Optional[str] = None
    product_name: Optional[str] = None
    process_stage: Optional[str] = None
    status: Optional[IPQCInspectionStatus] = None
    inspection_conclusion: Optional[IPQCInspectionConclusion] = None
    batch_locked: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
