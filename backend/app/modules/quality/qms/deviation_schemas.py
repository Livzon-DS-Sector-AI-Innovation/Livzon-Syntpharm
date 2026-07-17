"""偏差管理 Pydantic Schemas"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

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

    occurrence_date: datetime | None = None
    discovering_department: str | None = None
    discoverer: str | None = None
    product_code: str | None = None
    product_name: str | None = None
    production_batch: str | None = None
    material_code: str | None = None
    batch_size: str | None = None
    deviation_type: DeviationType
    deviation_level: DeviationLevel
    # 偏差描述 - 前端使用description，后端数据库存储为abnormal_description
    description: str | None = None
    abnormal_description: str | None = None
    impact_scope: str | None = None
    emergency_measures: str | None = None
    attachments: list[Any] | None = []
    batch_locked: bool = False
    batch_lock_reason: str | None = None


class DeviationUpdate(BaseModel):
    """偏差更新"""

    occurrence_date: datetime | None = None
    discovering_department: str | None = None
    discoverer: str | None = None
    product_code: str | None = None
    product_name: str | None = None
    production_batch: str | None = None
    material_code: str | None = None
    batch_size: str | None = None
    deviation_type: DeviationType | None = None
    deviation_level: DeviationLevel | None = None
    # 偏差描述
    description: str | None = None
    abnormal_description: str | None = None
    impact_scope: str | None = None
    emergency_measures: str | None = None
    attachments: list[Any] | None = None
    batch_locked: bool | None = None
    batch_lock_reason: str | None = None
    # 调查信息
    investigation: dict[str, Any] | None = None
    # 整改信息
    correction: Optional["CorrectionUpdate"] = None
    status: str | None = None


class DeviationResponse(BaseModel):
    """偏差响应"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deviation_no: str
    occurrence_date: datetime | None = None
    discovering_department: str | None = None
    discoverer: str | None = None
    product_code: str | None = None
    product_name: str | None = None
    production_batch: str | None = None
    material_code: str | None = None
    batch_size: str | None = None
    deviation_type: DeviationType
    deviation_level: DeviationLevel
    # 偏差描述
    description: str | None = None
    abnormal_description: str | None = None
    impact_scope: str | None = None
    emergency_measures: str | None = None
    attachments: list[Any] | None = []
    batch_locked: bool = False
    batch_lock_reason: str | None = None
    batch_locked_at: datetime | None = None
    status: DeviationStatus
    created_at: datetime
    updated_at: datetime


class DeviationListItem(BaseModel):
    """偏差列表项"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deviation_no: str
    occurrence_date: datetime | None = None
    discovering_department: str | None = None
    deviation_type: DeviationType
    deviation_level: DeviationLevel
    product_name: str | None = None
    production_batch: str | None = None
    status: DeviationStatus
    batch_locked: bool = False
    has_investigation: bool = False
    has_correction: bool = False
    has_closing: bool = False
    created_at: datetime


class DeviationFilter(BaseModel):
    """偏差筛选条件"""

    deviation_no: str | None = None
    deviation_type: DeviationType | None = None
    deviation_level: DeviationLevel | None = None
    status: DeviationStatus | None = None
    start_date: str | None = None
    end_date: str | None = None
    product_batch: str | None = None
    department: str | None = None


# ============ Investigation Schemas ============


class InvestigationCreate(BaseModel):
    """调查创建"""

    investigation_team: str | None = None
    investigation_start_date: datetime | None = None
    investigation_end_date: datetime | None = None
    investigation_method: str | None = None
    direct_cause: str | None = None
    indirect_cause: str | None = None
    root_cause: str | None = None
    why_analysis: str | None = None
    impact_assessment: str | None = None
    investigation_conclusion: str | None = None
    affected_batches: str | None = None
    temporary_measures: str | None = None
    attachments: list[Any] | None = []


class InvestigationUpdate(BaseModel):
    """调查更新"""

    investigation_team: str | None = None
    investigation_start_date: datetime | None = None
    investigation_end_date: datetime | None = None
    investigation_method: str | None = None
    direct_cause: str | None = None
    indirect_cause: str | None = None
    root_cause: str | None = None
    why_analysis: str | None = None
    impact_assessment: str | None = None
    investigation_conclusion: str | None = None
    affected_batches: str | None = None
    temporary_measures: str | None = None
    attachments: list[Any] | None = None
    status: InvestigationStatus | None = None


class InvestigationResponse(BaseModel):
    """调查响应"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deviation_id: UUID
    investigation_team: str | None = None
    investigation_start_date: datetime | None = None
    investigation_end_date: datetime | None = None
    investigation_method: str | None = None
    direct_cause: str | None = None
    indirect_cause: str | None = None
    root_cause: str | None = None
    why_analysis: str | None = None
    impact_assessment: str | None = None
    investigation_conclusion: str | None = None
    affected_batches: str | None = None
    temporary_measures: str | None = None
    attachments: list[Any] | None = []
    status: InvestigationStatus
    created_at: datetime
    updated_at: datetime


class InvestigationListItem(BaseModel):
    """调查列表项"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deviation_id: UUID
    deviation_no: str
    investigation_team: str | None = None
    investigation_start_date: datetime | None = None
    investigation_end_date: datetime | None = None
    status: InvestigationStatus
    created_at: datetime


# ============ Correction Schemas ============


class CorrectiveActionItem(BaseModel):
    """整改措施项"""

    content: str
    department: str | None = None
    responsible_person: str | None = None
    plan_date: str | None = None
    completed: bool = False
    completion_date: str | None = None


class CorrectionCreate(BaseModel):
    """整改创建"""

    responsible_department: str | None = None
    responsible_person: str | None = None
    plan_completion_date: datetime | None = None
    temporary_corrective_actions: list[Any] | None = []
    long_term_corrective_actions: list[Any] | None = []


class CorrectionUpdate(BaseModel):
    """整改更新"""

    correction_measures: str | None = None
    responsible_department: str | None = None
    responsible_person: str | None = None
    plan_completion_date: datetime | None = None
    temporary_corrective_actions: list[Any] | None = None
    long_term_corrective_actions: list[Any] | None = None
    progress: int | None = None
    status: CorrectionStatus | None = None
    evidence_attachments: list[Any] | None = None


class CorrectionResponse(BaseModel):
    """整改响应"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deviation_id: UUID
    responsible_department: str | None = None
    responsible_person: str | None = None
    plan_completion_date: datetime | None = None
    temporary_corrective_actions: list[Any] | None = []
    long_term_corrective_actions: list[Any] | None = []
    progress: int = 0
    status: CorrectionStatus
    evidence_attachments: list[Any] | None = []
    created_at: datetime
    updated_at: datetime


class CorrectionListItem(BaseModel):
    """整改列表项"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deviation_id: UUID
    deviation_no: str
    responsible_department: str | None = None
    responsible_person: str | None = None
    plan_completion_date: datetime | None = None
    progress: int = 0
    status: CorrectionStatus
    created_at: datetime


# ============ Closing Schemas ============


class ClosingCreate(BaseModel):
    """关闭创建"""

    verification_plan: str | None = None
    verification_data: str | None = None
    verification_result: str | None = None
    is_resolved: bool = False
    conclusion: str | None = None
    attachments: list[Any] | None = []


class ClosingUpdate(BaseModel):
    """关闭更新"""

    verification_plan: str | None = None
    verification_data: str | None = None
    verification_result: str | None = None
    is_resolved: bool | None = None
    conclusion: str | None = None
    attachments: list[Any] | None = None


class ClosingResponse(BaseModel):
    """关闭响应"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deviation_id: UUID
    verification_plan: str | None = None
    verification_data: str | None = None
    verification_result: str | None = None
    is_resolved: bool = False
    conclusion: str | None = None
    attachments: list[Any] | None = []
    batch_unlocked: bool = False
    archived: bool = False
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ClosingListItem(BaseModel):
    """关闭列表项"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deviation_id: UUID
    deviation_no: str
    is_resolved: bool = False
    conclusion: str | None = None
    archived: bool = False
    created_at: datetime


# ============ Approval Schemas ============


class ApprovalCreate(BaseModel):
    """审批创建"""

    deviation_id: UUID
    approval_type: str
    approved: bool
    comments: str | None = None


class ApprovalResponse(BaseModel):
    """审批响应"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deviation_id: UUID
    approval_type: str
    approver_name: str | None = None
    approver_department: str | None = None
    approval_comments: str | None = None
    approved: bool
    approved_at: datetime | None = None
    created_at: datetime


# ============ Statistics Schemas ============


class DeviationStatistics(BaseModel):
    """偏差统计"""

    total_count: int = 0
    by_type: dict[str, Any] = {}
    by_level: dict[str, Any] = {}
    by_status: dict[str, Any] = {}
    monthly_trend: list[Any] = []


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
