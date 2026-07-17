"""Dashboard summary schemas."""

import uuid
from datetime import date

from pydantic import BaseModel


class DashboardProjectItem(BaseModel):
    id: uuid.UUID
    product_name: str
    market: str
    registration_type: str | None
    status: str
    submitted_at: date | None
    accepted_at: date | None
    expected_completion_at: date | None
    owner: str | None
    latest_progress: str | None

    model_config = {"from_attributes": True}


class DashboardCertificateItem(BaseModel):
    id: uuid.UUID
    product_name: str
    market: str
    certificate_no: str | None
    approved_at: date | None
    valid_until: date | None
    certificate_status: str
    file_path: str | None

    model_config = {"from_attributes": True}


class DashboardSummaryResponse(BaseModel):
    approved_product_count: int
    overseas_approval_count: int
    submitted_project_count: int
    active_project_count: int
    recent_projects: list[DashboardProjectItem]
    overseas_approvals: list[DashboardCertificateItem]
