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


class ProjectCreate(BaseModel):
    product_name: str = Field(min_length=1, max_length=255)
    market: str = Field(min_length=1, max_length=128)
    registration_type: str | None = Field(None, max_length=64)
    status: ProjectStatus = "draft"
    submitted_at: date | None = None
    accepted_at: date | None = None
    approved_at: date | None = None
    expected_completion_at: date | None = None
    owner: str | None = Field(None, max_length=128)
    latest_progress: str | None = None


class ProjectUpdate(BaseModel):
    product_name: str | None = Field(None, min_length=1, max_length=255)
    market: str | None = Field(None, min_length=1, max_length=128)
    registration_type: str | None = Field(None, max_length=64)
    status: ProjectStatus | None = None
    submitted_at: date | None = None
    accepted_at: date | None = None
    approved_at: date | None = None
    expected_completion_at: date | None = None
    owner: str | None = Field(None, max_length=128)
    latest_progress: str | None = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    product_name: str
    market: str
    registration_type: str | None
    status: str
    submitted_at: date | None
    accepted_at: date | None
    approved_at: date | None
    expected_completion_at: date | None
    owner: str | None
    latest_progress: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
