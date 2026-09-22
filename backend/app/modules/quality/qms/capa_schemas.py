"""CAPA Pydantic Schemas"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.quality.qms.capa_models import (
    CapaCategory,
    CapaSource,
    CapaWorkflowStatus,
)


# ============ Base Schemas ============


class CapaItemBase(BaseModel):
    """CAPA 项目基础模式"""

    description: str = Field(..., description="项目描述")
    content: str | None = Field(None, description="项目内容")
    responsible_user_id: str = Field(..., description="责任人ID")
    responsible_person: str | None = Field(None, description="责任人姓名")
    due_date: str = Field(..., description="截止日期")
    deadline: str | None = Field(None, description="截止日期（备选）")
    status: str = Field("pending", description="状态")


class CapaItemCreate(CapaItemBase):
    """创建 CAPA 项目"""

    pass


class CapaItemResponse(CapaItemBase):
    """CAPA 项目响应"""

    id: str

    class Config:
        from_attributes = True


class ExecutionTrackBase(BaseModel):
    """执行跟踪基础模式"""

    executionStatus: str = Field(..., description="执行状态")
    execution_date: str | None = Field(None, description="执行日期")
    execution_notes: str | None = Field(None, description="执行备注")
    qaConfirmer: str | None = Field(None, description="QA确认人")
    qaConfirmDate: str | None = Field(None, description="QA确认日期")


class ExecutionTrackCreate(ExecutionTrackBase):
    """创建执行跟踪"""

    pass


class ExecutionTrackResponse(ExecutionTrackBase):
    """执行跟踪响应"""

    id: str

    class Config:
        from_attributes = True


class DeptHeadConfirmationBase(BaseModel):
    """部门负责人确认基础模式"""

    department: str = Field(..., description="部门")
    deptHeadUserId: str = Field(..., description="部门负责人用户ID")
    result: str = Field(..., description="确认结果")
    opinion: str = Field(..., description="确认意见")
    confirmTime: str = Field(..., description="确认时间")


class DeptHeadConfirmationCreate(DeptHeadConfirmationBase):
    """创建部门负责人确认"""

    pass


class DeptHeadConfirmationResponse(DeptHeadConfirmationBase):
    """部门负责人确认响应"""

    class Config:
        from_attributes = True


# ============ CAPA Schemas ============


class CapaBase(BaseModel):
    """CAPA 基础模式"""

    model_config = ConfigDict(use_enum_values=True)

    title: str | None = Field(None, description="标题")
    source: CapaSource | None = Field(None, description="来源")
    source_code: str | None = Field(None, description="来源编号")
    category: CapaCategory | None = Field(None, description="类别")
    root_cause_category: str | None = Field(None, description="根本原因类别")
    non_conformity_description: str | None = Field(None, description="不符合描述")
    root_cause_analysis: str | None = Field(None, description="根本原因分析")
    capa_content: str | None = Field(None, description="CAPA内容")
    capa_items: list[CapaItemCreate] | None = Field(None, description="CAPA项目列表")
    executors: list[str] | None = Field(None, description="执行人列表")
    expected_completion_date: datetime | None = Field(None, description="预期完成日期")
    deviation_id: UUID | None = Field(None, description="关联偏差ID")


class CapaCreate(CapaBase):
    """创建 CAPA"""

    pass


class CapaUpdate(BaseModel):
    """更新 CAPA"""

    model_config = ConfigDict(use_enum_values=True)

    title: str | None = None
    source: CapaSource | None = None
    source_code: str | None = None
    category: CapaCategory | None = None
    root_cause_category: str | None = None
    non_conformity_description: str | None = None
    root_cause_analysis: str | None = None
    capa_content: str | None = None
    capa_items: list[CapaItemCreate] | None = None
    executors: list[str] | None = None
    expected_completion_date: datetime | None = None
    status: CapaWorkflowStatus | None = None


class CapaResponse(BaseModel):
    """CAPA 响应"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    capa_code: str
    final_code: str | None = None
    title: str | None = None
    status: CapaWorkflowStatus
    deviation_id: UUID | None = None
    source: str | None = None
    source_code: str | None = None
    category: str | None = None
    root_cause_category: str | None = None
    non_conformity_description: str | None = None
    root_cause_analysis: str | None = None
    capa_content: str | None = None
    capa_items: list[dict[str, Any]] | None = None
    executors: list[str] | None = None
    expected_completion_date: datetime | None = None
    qa_reviewer_id: UUID | None = None
    qa_review_opinion: str | None = None
    qa_review_time: datetime | None = None
    q_head_approver_id: UUID | None = None
    q_head_approval_opinion: str | None = None
    q_head_approval_time: datetime | None = None
    execution_status: str | None = None
    execution_tracks: list[dict[str, Any]] | None = None
    dept_head_confirmations: list[dict[str, Any]] | None = None
    evaluation_result: str | None = None
    evaluation_target: str | None = None
    evaluation_deadline: datetime | None = None
    evaluation_confirmer_id: UUID | None = None
    evaluation_confirm_date: datetime | None = None
    closure_date: datetime | None = None
    closure_remark: str | None = None
    report_content: str | None = None
    report_versions: list[dict[str, Any]] | None = None
    returned_step: str | None = None
    status_updated_at: datetime | None = None
    reporter: str | None = None
    reason_category: str | None = None
    created_at: datetime
    updated_at: datetime


# ============ Workflow Schemas ============


class ExecutionTrackSubmit(BaseModel):
    """提交执行跟踪"""

    executionStatus: str = Field(..., description="执行状态")
    execution_date: str | None = Field(None, description="执行日期")
    execution_notes: str | None = Field(None, description="执行备注")


class ExecutionConfirm(BaseModel):
    """确认执行"""

    qaConfirmer: str = Field(..., description="QA确认人")
    qaConfirmDate: str = Field(..., description="QA确认日期")


class EvaluationSubmit(BaseModel):
    """提交评估"""

    evaluation_result: str = Field(..., description="评估结果")
    evaluation_target: str = Field(..., description="评估目标")
    evaluation_deadline: datetime = Field(..., description="评估截止日期")


class PartComplete(BaseModel):
    """完成部分"""

    part: str = Field(..., description="部分名称")


class DeptHeadConfirm(BaseModel):
    """部门负责人确认"""

    department: str = Field(..., description="部门")
    deptHeadUserId: str = Field(..., description="部门负责人用户ID")
    result: str = Field(..., description="确认结果")
    opinion: str = Field(..., description="确认意见")


# ============ API Response Wrappers ============


class CapaApiResponse(BaseModel):
    """Single CAPA response wrapper"""
    code: int = 200
    message: str = "success"
    data: CapaResponse


class CapaListApiResponse(BaseModel):
    """CAPA list response wrapper"""
    code: int = 200
    message: str = "success"
    data: list[CapaResponse]
    meta: dict[str, Any] | None = None
