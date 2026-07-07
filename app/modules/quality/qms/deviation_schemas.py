"""偏差管理 Pydantic Schemas"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.quality.qms.deviation_models import (
    CorrectionStatus,
    DeviationLevel,
    DeviationStatus,
    DeviationType,
    InvestigationStatus,
)


# ============ Deviation Schemas ============

class DeviationCreate(BaseModel):
    """偏差创建"""
    model_config = ConfigDict(use_enum_values=True)
    
    occurrence_date: Optional[datetime] = None
    discovering_department: Optional[str] = None
    discoverer: Optional[str] = None
    product_code: Optional[str] = None
    product_name: Optional[str] = None
    production_batch: Optional[str] = None
    material_code: Optional[str] = None
    batch_size: Optional[str] = None
    deviation_type: DeviationType
    deviation_level: DeviationLevel
    # 偏差描述 - 前端使用description，后端数据库存储为abnormal_description
    description: Optional[str] = None
    abnormal_description: Optional[str] = None
    impact_scope: Optional[str] = None
    emergency_measures: Optional[str] = None
    attachments: Optional[list] = []
    batch_locked: bool = False
    batch_lock_reason: Optional[str] = None


class DeviationUpdate(BaseModel):
    """偏差更新"""
    occurrence_date: Optional[datetime] = None
    discovering_department: Optional[str] = None
    discoverer: Optional[str] = None
    product_code: Optional[str] = None
    product_name: Optional[str] = None
    production_batch: Optional[str] = None
    material_code: Optional[str] = None
    batch_size: Optional[str] = None
    deviation_type: Optional[DeviationType] = None
    deviation_level: Optional[DeviationLevel] = None
    # 偏差描述
    description: Optional[str] = None
    abnormal_description: Optional[str] = None
    impact_scope: Optional[str] = None
    emergency_measures: Optional[str] = None
    attachments: Optional[list] = None
    batch_locked: Optional[bool] = None
    batch_lock_reason: Optional[str] = None
    # 调查信息
    investigation: Optional[dict] = None
    # 整改信息
    correction: Optional["CorrectionUpdate"] = None
    status: Optional[str] = None


class DeviationResponse(BaseModel):
    """偏差响应"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deviation_no: str
    occurrence_date: Optional[datetime] = None
    discovering_department: Optional[str] = None
    discoverer: Optional[str] = None
    product_code: Optional[str] = None
    product_name: Optional[str] = None
    production_batch: Optional[str] = None
    material_code: Optional[str] = None
    batch_size: Optional[str] = None
    deviation_type: DeviationType
    deviation_level: DeviationLevel
    # 偏差描述
    description: Optional[str] = None
    abnormal_description: Optional[str] = None
    impact_scope: Optional[str] = None
    emergency_measures: Optional[str] = None
    attachments: Optional[list] = []
    batch_locked: bool = False
    batch_lock_reason: Optional[str] = None
    batch_locked_at: Optional[datetime] = None
    status: DeviationStatus
    created_at: datetime
    updated_at: datetime


class DeviationListItem(BaseModel):
    """偏差列表项"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deviation_no: str
    occurrence_date: Optional[datetime] = None
    discovering_department: Optional[str] = None
    deviation_type: DeviationType
    deviation_level: DeviationLevel
    product_name: Optional[str] = None
    production_batch: Optional[str] = None
    status: DeviationStatus
    batch_locked: bool = False
    has_investigation: bool = False
    has_correction: bool = False
    has_closing: bool = False
    created_at: datetime


class DeviationFilter(BaseModel):
    """偏差筛选条件"""
    deviation_no: Optional[str] = None
    deviation_type: Optional[DeviationType] = None
    deviation_level: Optional[DeviationLevel] = None
    status: Optional[DeviationStatus] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    product_batch: Optional[str] = None
    department: Optional[str] = None


# ============ Investigation Schemas ============

class InvestigationCreate(BaseModel):
    """调查创建"""
    investigation_team: Optional[str] = None
    investigation_start_date: Optional[datetime] = None
    investigation_end_date: Optional[datetime] = None
    investigation_method: Optional[str] = None
    direct_cause: Optional[str] = None
    indirect_cause: Optional[str] = None
    root_cause: Optional[str] = None
    why_analysis: Optional[str] = None
    impact_assessment: Optional[str] = None
    investigation_conclusion: Optional[str] = None
    affected_batches: Optional[str] = None
    temporary_measures: Optional[str] = None
    attachments: Optional[list] = []


class InvestigationUpdate(BaseModel):
    """调查更新"""
    investigation_team: Optional[str] = None
    investigation_start_date: Optional[datetime] = None
    investigation_end_date: Optional[datetime] = None
    investigation_method: Optional[str] = None
    direct_cause: Optional[str] = None
    indirect_cause: Optional[str] = None
    root_cause: Optional[str] = None
    why_analysis: Optional[str] = None
    impact_assessment: Optional[str] = None
    investigation_conclusion: Optional[str] = None
    affected_batches: Optional[str] = None
    temporary_measures: Optional[str] = None
    attachments: Optional[list] = None
    status: Optional[InvestigationStatus] = None


class InvestigationResponse(BaseModel):
    """调查响应"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deviation_id: UUID
    investigation_team: Optional[str] = None
    investigation_start_date: Optional[datetime] = None
    investigation_end_date: Optional[datetime] = None
    investigation_method: Optional[str] = None
    direct_cause: Optional[str] = None
    indirect_cause: Optional[str] = None
    root_cause: Optional[str] = None
    why_analysis: Optional[str] = None
    impact_assessment: Optional[str] = None
    investigation_conclusion: Optional[str] = None
    affected_batches: Optional[str] = None
    temporary_measures: Optional[str] = None
    attachments: Optional[list] = []
    status: InvestigationStatus
    created_at: datetime
    updated_at: datetime


class InvestigationListItem(BaseModel):
    """调查列表项"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deviation_id: UUID
    deviation_no: str
    investigation_team: Optional[str] = None
    investigation_start_date: Optional[datetime] = None
    investigation_end_date: Optional[datetime] = None
    status: InvestigationStatus
    created_at: datetime


# ============ Correction Schemas ============

class CorrectiveActionItem(BaseModel):
    """整改措施项"""
    content: str
    department: Optional[str] = None
    responsible_person: Optional[str] = None
    plan_date: Optional[str] = None
    completed: bool = False
    completion_date: Optional[str] = None


class CorrectionCreate(BaseModel):
    """整改创建"""
    responsible_department: Optional[str] = None
    responsible_person: Optional[str] = None
    plan_completion_date: Optional[datetime] = None
    temporary_corrective_actions: Optional[list] = []
    long_term_corrective_actions: Optional[list] = []


class CorrectionUpdate(BaseModel):
    """整改更新"""
    correction_measures: Optional[str] = None
    responsible_department: Optional[str] = None
    responsible_person: Optional[str] = None
    plan_completion_date: Optional[datetime] = None
    temporary_corrective_actions: Optional[list] = None
    long_term_corrective_actions: Optional[list] = None
    progress: Optional[int] = None
    status: Optional[CorrectionStatus] = None
    evidence_attachments: Optional[list] = None


class CorrectionResponse(BaseModel):
    """整改响应"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deviation_id: UUID
    responsible_department: Optional[str] = None
    responsible_person: Optional[str] = None
    plan_completion_date: Optional[datetime] = None
    temporary_corrective_actions: Optional[list] = []
    long_term_corrective_actions: Optional[list] = []
    progress: int = 0
    status: CorrectionStatus
    evidence_attachments: Optional[list] = []
    created_at: datetime
    updated_at: datetime


class CorrectionListItem(BaseModel):
    """整改列表项"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deviation_id: UUID
    deviation_no: str
    responsible_department: Optional[str] = None
    responsible_person: Optional[str] = None
    plan_completion_date: Optional[datetime] = None
    progress: int = 0
    status: CorrectionStatus
    created_at: datetime


# ============ Closing Schemas ============

class ClosingCreate(BaseModel):
    """关闭创建"""
    verification_plan: Optional[str] = None
    verification_data: Optional[str] = None
    verification_result: Optional[str] = None
    is_resolved: bool = False
    conclusion: Optional[str] = None
    attachments: Optional[list] = []


class ClosingUpdate(BaseModel):
    """关闭更新"""
    verification_plan: Optional[str] = None
    verification_data: Optional[str] = None
    verification_result: Optional[str] = None
    is_resolved: Optional[bool] = None
    conclusion: Optional[str] = None
    attachments: Optional[list] = None


class ClosingResponse(BaseModel):
    """关闭响应"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deviation_id: UUID
    verification_plan: Optional[str] = None
    verification_data: Optional[str] = None
    verification_result: Optional[str] = None
    is_resolved: bool = False
    conclusion: Optional[str] = None
    attachments: Optional[list] = []
    batch_unlocked: bool = False
    archived: bool = False
    archived_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ClosingListItem(BaseModel):
    """关闭列表项"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deviation_id: UUID
    deviation_no: str
    is_resolved: bool = False
    conclusion: Optional[str] = None
    archived: bool = False
    created_at: datetime


# ============ Approval Schemas ============

class ApprovalCreate(BaseModel):
    """审批创建"""
    deviation_id: UUID
    approval_type: str
    approved: bool
    comments: Optional[str] = None


class ApprovalResponse(BaseModel):
    """审批响应"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deviation_id: UUID
    approval_type: str
    approver_name: Optional[str] = None
    approver_department: Optional[str] = None
    approval_comments: Optional[str] = None
    approved: bool
    approved_at: Optional[datetime] = None
    created_at: datetime


# ============ Statistics Schemas ============

class DeviationStatistics(BaseModel):
    """偏差统计"""
    total_count: int = 0
    by_type: dict = {}
    by_level: dict = {}
    by_status: dict = {}
    monthly_trend: list = []


class DeviationTypeCount(BaseModel):
    """偏差类型统计"""
    type: str
    count: int
    percentage: float


class DeviationLevelCount(BaseModel):
    """偏差等级统计"""
    level: str
    count: int
    percentage: float


# ============ Batch Lock Schemas ============

class BatchLockRequest(BaseModel):
    """批次锁定请求"""
    deviation_id: UUID
    reason: str = "偏差相关批次锁定"


class BatchUnlockRequest(BaseModel):
    """批次解锁请求"""
    deviation_id: UUID