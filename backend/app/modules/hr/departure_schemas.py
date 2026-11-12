"""Request/response schemas for the 2026 离职台账 (ticket #200).

The selected person is the only source of the snapshot fields
(一级/二级部门, 姓名, 性别, 岗位, 入职日期, 学历, 年龄); clients cannot send
them on create or update.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.modules.hr.departure_domain import LeaveCategory
from app.modules.hr.onboarding_domain import Gender, GroupClassification, PersonnelIdentity, PositionLevel

Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class DepartureRecordCreate(BaseModel):
    """Create payload: person reference plus the editable ledger fields."""

    model_config = ConfigDict(extra="forbid")

    person_id: UUID = Field(..., description="员工档案人员 id")
    position_level: PositionLevel = Field(..., description="岗位层级")
    personnel_identity: PersonnelIdentity = Field(..., description="人员身份")
    leave_date: date = Field(..., description="离职日期")
    leave_category: LeaveCategory = Field(..., description="离职类别")
    leave_reason: Reason = Field(..., description="离职原因")
    group_classification: GroupClassification = Field(..., description="集团月报表人员分类")


class DepartureRecordUpdate(BaseModel):
    """Partial update of editable fields; snapshot fields are rejected."""

    model_config = ConfigDict(extra="forbid")

    position_level: PositionLevel | None = None
    personnel_identity: PersonnelIdentity | None = None
    leave_date: date | None = None
    leave_category: LeaveCategory | None = None
    leave_reason: Reason | None = None
    group_classification: GroupClassification | None = None


class DepartureRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    person_id: UUID
    department_level1: str
    department_level2: str
    name: str
    gender: Gender
    position: str
    position_level: str
    personnel_identity: str
    hire_date: date
    leave_date: date
    leave_category: str
    leave_reason: str
    education: str
    age: int
    tenure_years: float
    group_classification: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DepartureRecordListApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: list[DepartureRecordResponse]
    meta: dict[str, Any] | None = None


class DepartureRecordApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: DepartureRecordResponse
    meta: dict[str, Any] | None = None


class DepartureRecordDeleteApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: None = None
    meta: dict[str, Any] | None = None
