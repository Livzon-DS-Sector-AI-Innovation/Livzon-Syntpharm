"""Registration certificate schemas."""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

CertificateType = Literal["domestic_approval", "overseas_registration", "wc", "copp", "gmp", "other"]
CertificateStatus = Literal["valid", "expiring", "expired", "pending"]


class CertificateCreate(BaseModel):
    product_name: str = Field(min_length=1, max_length=255)
    market: str = Field(min_length=1, max_length=128)
    certificate_type: CertificateType
    certificate_no: str | None = Field(None, max_length=128)
    approved_at: date | None = None
    valid_until: date | None = None
    status: CertificateStatus = "valid"
    file_path: str | None = Field(None, max_length=512)
    related_project_id: uuid.UUID | None = None


class CertificateUpdate(BaseModel):
    product_name: str | None = Field(None, min_length=1, max_length=255)
    market: str | None = Field(None, min_length=1, max_length=128)
    certificate_type: CertificateType | None = None
    certificate_no: str | None = Field(None, max_length=128)
    approved_at: date | None = None
    valid_until: date | None = None
    status: CertificateStatus | None = None
    file_path: str | None = Field(None, max_length=512)
    related_project_id: uuid.UUID | None = None


class CertificateResponse(BaseModel):
    id: uuid.UUID
    product_name: str
    market: str
    certificate_type: str
    certificate_no: str | None
    approved_at: date | None
    valid_until: date | None
    status: str
    file_path: str | None
    related_project_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
