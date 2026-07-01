"""Department contacts Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DepartmentContactOut(BaseModel):
    id: uuid.UUID
    department: str
    dept_head_id: uuid.UUID | None = None
    qa_staff_ids: list[str] | None = None
    gmp_staff_ids: list[str] | None = None
    production_head_id: uuid.UUID | None = None
    quality_head_id: uuid.UUID | None = None
    additional_contacts: list[str] | None = None
    is_production_workshop: bool | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreateDepartmentContactRequest(BaseModel):
    department: str
    dept_head_id: uuid.UUID | None = None
    qa_staff_ids: list[str] | None = None
    gmp_staff_ids: list[str] | None = None
    production_head_id: uuid.UUID | None = None
    quality_head_id: uuid.UUID | None = None
    additional_contacts: list[str] | None = None
    is_production_workshop: bool | None = None


class UpdateDepartmentContactRequest(BaseModel):
    dept_head_id: uuid.UUID | None = None
    qa_staff_ids: list[str] | None = None
    gmp_staff_ids: list[str] | None = None
    production_head_id: uuid.UUID | None = None
    quality_head_id: uuid.UUID | None = None
    additional_contacts: list[str] | None = None
    is_production_workshop: bool | None = None


class DepartmentWeeklyConfirmationOut(BaseModel):
    id: uuid.UUID
    department: str
    week_key: str
    production_status: str
    deviation_status: str
    confirmed_by_id: uuid.UUID | None = None
    confirmed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConfirmProductionStatusRequest(BaseModel):
    department: str
    week_key: str
    production_status: str
    deviation_status: str = "unsubmitted"
