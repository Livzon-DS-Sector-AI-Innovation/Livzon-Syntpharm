"""Deviation Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class AiAnalysis(BaseModel):
    description: str | None = None
    reason: str | None = None
    riskAssessment: str | None = None
    capaSuggestion: str | None = None


class InvestigationRecord(BaseModel):
    nonconformityDescription: str | None = None
    rootCauseAnalysis: str | None = None
    riskAssessment: str | None = None
    urgentMeasures: str | None = None
    content: str | None = None
    author: str = ""
    department: str | None = None
    createTime: str = ""
    attachments: list[str] | None = None
    isModified: bool = False
    modifyTime: str | None = None
    capaProposals: list[dict] | None = None


class ReviewOpinion(BaseModel):
    content: str = ""
    author: str = ""
    step: str = ""
    result: str = "approved"
    createTime: str = ""


class CrossDeptReviewer(BaseModel):
    department: str = ""
    investigators: list[str] = []


class DeviationListItem(BaseModel):
    id: uuid.UUID
    deviation_code: str
    final_code: str | None = None
    title: str
    department: str | None = None
    discovery_date: datetime | None = None
    status: str
    level: str | None = None
    root_cause_category: str | None = None
    reporter_id: uuid.UUID | None = None
    handler: str | None = None
    created_at: datetime
    status_updated_at: datetime | None = None
    returned_step: str | None = None

    class Config:
        from_attributes = True


class DeviationDetail(BaseModel):
    id: uuid.UUID
    deviation_code: str
    final_code: str | None = None
    title: str
    department: str | None = None
    discovery_date: datetime | None = None
    discovery_time: str | None = None
    discovery_location: str | None = None
    status: str
    level: str | None = None
    root_cause_category: str | None = None
    description: str | None = None
    immediate_actions: str | None = None
    reporter_id: uuid.UUID | None = None
    handler: str | None = None
    discoverer: str | None = None
    ai_analysis: dict | None = None
    investigation_records: list | None = None
    review_opinions: list | None = None
    attachments: list[str] | None = None
    needs_cross_dept_review: bool | None = True
    cross_dept_reviewers: list | None = None
    affected_items: str | None = None
    batch_number: str | None = None
    returned_step: str | None = None
    status_updated_at: datetime | None = None
    report_content: str | None = None
    report_versions: list | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CreateDeviationRequest(BaseModel):
    title: str
    department: str | None = None
    discovery_date: str | None = None
    discovery_time: str | None = None
    discovery_location: str | None = None
    level: str | None = None
    root_cause_category: str | None = None
    description: str | None = None
    immediate_actions: str | None = None
    attachments: list[str] | None = None
    affected_items: str | None = None
    batch_number: str | None = None
    handler: str | None = None
    needs_cross_dept_review: bool | None = True
    cross_dept_reviewers: list[CrossDeptReviewer] | None = None


class UpdateDeviationRequest(BaseModel):
    title: str | None = None
    status: str | None = None
    level: str | None = None
    department: str | None = None
    discovery_date: str | None = None
    discovery_time: str | None = None
    discovery_location: str | None = None
    root_cause_category: str | None = None
    description: str | None = None
    immediate_actions: str | None = None
    ai_analysis: dict | None = None
    investigation_records: list | None = None
    review_opinions: list | None = None
    attachments: list[str] | None = None
    final_code: str | None = None
    handler: str | None = None
    discoverer: str | None = None
    needs_cross_dept_review: bool | None = None
    cross_dept_reviewers: list[CrossDeptReviewer] | None = None
    affected_items: str | None = None
    batch_number: str | None = None
    returned_step: str | None = None
    report_content: str | None = None
    report_versions: list | None = None


class SubmitReviewRequest(BaseModel):
    step: str
    result: str = "approved"
    content: str = ""
    reason_category: str | None = None
    deviation_level: str | None = None


class SubmitInvestigationRequest(BaseModel):
    description: str | None = None
    investigation_records: list | None = None
    nonconformity_description: str | None = None
    root_cause_analysis: str | None = None
    risk_assessment: str | None = None
    urgent_measures: str | None = None
    capa_proposals: list[dict] | None = None


class CompleteAiAnalysisRequest(BaseModel):
    ai_analysis: dict | None = None


class BatchUpdateStatusRequest(BaseModel):
    deviation_ids: list[uuid.UUID]
    target_status: str


class BatchUpdateStatusResponse(BaseModel):
    updated_count: int
    failed_count: int
    failures: list[dict]

    class Config:
        from_attributes = True
