"""Registration project schemas."""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

ProjectStatus = Literal[
    "draft",
    "preparing",
    "submitted",
    "accepted",
    "under_review",
    "supplementary",
    "approved",
    "withdrawn",
    "terminated",
]

RegistrationType = Literal["新注册", "再注册", "变更", "补充申请"]

# 申报前阶段：受理为界，"accepted" 阶段只能由申报进度查询侧同步置达
PreStage = Literal["initiation", "data_preparation", "internal_review", "submission", "accepted"]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    product_name: str = Field(min_length=1, max_length=255)
    registration_type: RegistrationType
    project_no: str | None = Field(None, max_length=64)
    market: str | None = Field(None, max_length=128)
    owner: str | None = Field(None, max_length=128)
    planned_submission_date: date | None = None
    drug_id: uuid.UUID | None = None


class ProjectUpdate(BaseModel):
    """基本信息可编辑；状态/阶段不在此修改（阶段走 /stage 推进，受理后状态由申报进度查询同步）。"""

    name: str | None = Field(None, min_length=1, max_length=255)
    product_name: str | None = Field(None, min_length=1, max_length=255)
    registration_type: RegistrationType | None = None
    project_no: str | None = Field(None, max_length=64)
    market: str | None = Field(None, max_length=128)
    owner: str | None = Field(None, max_length=128)
    planned_submission_date: date | None = None
    expected_completion_at: date | None = None
    drug_id: uuid.UUID | None = None


class StageAdvanceRequest(BaseModel):
    # 接受全部 5 个阶段值；accepted 由 service 层拒绝并给出业务提示（而非 422）
    stage: PreStage


class ProgressLogCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class ProgressLogResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    log_type: str
    content: str
    created_by: uuid.UUID | None
    created_by_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectResponse(BaseModel):
    id: uuid.UUID
    drug_id: uuid.UUID | None
    project_no: str | None
    name: str | None
    product_name: str
    market: str | None
    registration_type: str | None
    status: str
    pre_stage: str
    stage_completed_at: dict[str, datetime] = Field(default_factory=dict)
    planned_submission_date: date | None
    acceptance_number: str | None
    submitted_at: date | None
    accepted_at: date | None
    approved_at: date | None
    expected_completion_at: date | None
    owner: str | None
    latest_progress: str | None
    latest_log: ProgressLogResponse | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectKpiResponse(BaseModel):
    """注册项目 KPI：申报前 / 已受理·审评中 / 临期未递交 / 已获批"""

    pre_submission: int
    accepted_reviewing: int
    due_soon: int
    approved: int
