"""CAPA Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class CapaItem(BaseModel):
    item_type: str
    content: str
    responsible_person: str | None = None
    deadline: str | None = None
    status: str = "pending"


class ExecutionTrack(BaseModel):
    content: str
    executor: str | None = None
    execution_date: str | None = None
    attachments: list[str] | None = None


class DeptHeadConfirmation(BaseModel):
    department: str
    confirmed: bool
    opinion: str | None = None
    confirm_date: str | None = None


class CapaListItem(BaseModel):
    id: uuid.UUID
    capa_code: str
    title: str | None = None
    status: str
    source: str | None = None
    category: str | None = None
    expected_completion_date: datetime | None = None
    created_at: datetime
    status_updated_at: datetime | None = None
    returned_step: str | None = None

    class Config:
        from_attributes = True


class CapaDetail(BaseModel):
    id: uuid.UUID
    capa_code: str
    title: str | None = None
    status: str
    deviation_id: uuid.UUID | None = None
    source: str | None = None
    source_code: str | None = None
    category: str | None = None
    root_cause_category: str | None = None
    non_conformity_description: str | None = None
    root_cause_analysis: str | None = None
    capa_content: str | None = None
    capa_items: list | None = None
    executors: list[str] | None = None
    expected_completion_date: datetime | None = None
    qa_reviewer_id: uuid.UUID | None = None
    qa_review_opinion: str | None = None
    qa_review_time: datetime | None = None
    q_head_approver_id: uuid.UUID | None = None
    q_head_approval_opinion: str | None = None
    q_head_approval_time: datetime | None = None
    execution_status: str | None = None
    execution_tracks: list | None = None
    dept_head_confirmations: list | None = None
    evaluation_result: str | None = None
    evaluation_target: str | None = None
    evaluation_deadline: datetime | None = None
    evaluation_confirmer_id: uuid.UUID | None = None
    evaluation_confirm_date: datetime | None = None
    closure_date: datetime | None = None
    closure_remark: str | None = None
    final_code: str | None = None
    report_content: str | None = None
    report_versions: list | None = None
    returned_step: str | None = None
    status_updated_at: datetime | None = None
    reporter: str | None = None
    reason_category: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CreateCapaRequest(BaseModel):
    title: str | None = None
    deviation_id: uuid.UUID | None = None
    source: str | None = None
    source_code: str | None = None
    category: str | None = None
    root_cause_category: str | None = None
    non_conformity_description: str | None = None
    root_cause_analysis: str | None = None
    capa_content: str | None = None
    capa_items: list[CapaItem] | None = None
    executors: list[str] | None = None
    expected_completion_date: str | None = None
    reporter: str | None = None


class UpdateCapaRequest(BaseModel):
    title: str | None = None
    status: str | None = None
    source: str | None = None
    source_code: str | None = None
    category: str | None = None
    root_cause_category: str | None = None
    non_conformity_description: str | None = None
    root_cause_analysis: str | None = None
    capa_content: str | None = None
    capa_items: list[CapaItem] | None = None
    executors: list[str] | None = None
    expected_completion_date: str | None = None
    qa_reviewer_id: uuid.UUID | None = None
    qa_review_opinion: str | None = None
    q_head_approver_id: uuid.UUID | None = None
    q_head_approval_opinion: str | None = None
    execution_status: str | None = None
    execution_tracks: list[ExecutionTrack] | None = None
    dept_head_confirmations: list[DeptHeadConfirmation] | None = None
    evaluation_result: str | None = None
    evaluation_target: str | None = None
    evaluation_deadline: str | None = None
    evaluation_confirmer_id: uuid.UUID | None = None
    evaluation_confirm_date: str | None = None
    closure_date: str | None = None
    closure_remark: str | None = None
    final_code: str | None = None
    report_content: str | None = None
    report_versions: list | None = None
    returned_step: str | None = None
    reporter: str | None = None
    reason_category: str | None = None


class CapaApprovalRequest(BaseModel):
    step: str
    result: str = "approved"
    opinion: str = ""


class CapaAutoFillFromDeviation(BaseModel):
    title: str | None = None
    non_conformity_description: str | None = None
    root_cause_analysis: str | None = None
    capa_content: str | None = None
    expected_completion_date: str | None = None


class CompletePartRequest(BaseModel):
    part: str  # "a" | "b"


class CapaDeptHeadConfirmRequest(BaseModel):
    department: str
    dept_head_user_id: str
    result: str  # "approved" | "rejected"
    opinion: str


class CapaEvaluationRequest(BaseModel):
    evaluation_target: str
    evaluation_result: str
    evaluation_confirmer: str
    evaluation_confirm_date: str
    closure_date: str


class LinkDeviationRequest(BaseModel):
    deviation_id: str
