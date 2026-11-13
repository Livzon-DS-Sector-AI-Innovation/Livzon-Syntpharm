"""Request/response schemas for the 2026 离职台账 (ticket #200).

The selected person is the only source of the frozen snapshot fields
(一级/二级部门, 姓名, 性别, 岗位, 入职日期). 学历 and 年龄 are prefilled from
the profile when available, but the form also sends them because the Feishu
employee sync does not supply those two fields.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.modules.hr.departure_domain import LeaveCategory
from app.modules.hr.onboarding_domain import (
    EducationLevel,
    Gender,
    GroupClassification,
    PersonnelIdentity,
    PositionLevel,
)

Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
Age = Annotated[int, Field(ge=16, le=100)]


class DepartureRecordCreate(BaseModel):
    """Create payload: person reference plus the editable ledger fields."""

    model_config = ConfigDict(extra="forbid")

    person_id: UUID | None = Field(None, description="员工档案人员 id；不在档案中时留空并手工填写快照字段")
    department_level1: str | None = Field(None, max_length=64, description="一级部门（手动录入时必填）")
    department_level2: str | None = Field(None, max_length=64, description="二级部门（手动录入时必填）")
    name: str | None = Field(None, max_length=64, description="姓名（手动录入时必填）")
    gender: Gender | None = Field(None, description="性别（手动录入时必填）")
    position: str | None = Field(None, max_length=64, description="岗位（手动录入时必填）")
    hire_date: date | None = Field(None, description="入职日期（手动录入时必填）")
    position_level: PositionLevel = Field(..., description="岗位层级")
    personnel_identity: PersonnelIdentity = Field(..., description="人员身份")
    leave_date: date = Field(..., description="离职日期")
    leave_category: LeaveCategory = Field(..., description="离职类别")
    leave_reason: Reason = Field(..., description="离职原因")
    education: EducationLevel | None = Field(None, description="学历；不传时取员工档案")
    age: Age | None = Field(None, description="年龄；不传时取员工档案")
    group_classification: GroupClassification = Field(..., description="集团月报表人员分类")

    @model_validator(mode="after")
    def _require_manual_snapshot(self) -> DepartureRecordCreate:
        if self.person_id is not None:
            return self
        missing = [
            label
            for label, value in (
                ("一级部门", self.department_level1),
                ("二级部门", self.department_level2),
                ("姓名", self.name),
                ("性别", self.gender),
                ("岗位", self.position),
                ("入职日期", self.hire_date),
            )
            if not value
        ]
        if missing:
            raise ValueError("手动录入时必须填写：" + "、".join(missing))
        return self


class DepartureRecordUpdate(BaseModel):
    """Partial update of editable fields; snapshot fields are rejected."""

    model_config = ConfigDict(extra="forbid")

    position_level: PositionLevel | None = None
    personnel_identity: PersonnelIdentity | None = None
    leave_date: date | None = None
    leave_category: LeaveCategory | None = None
    leave_reason: Reason | None = None
    education: EducationLevel | None = None
    age: Age | None = None
    group_classification: GroupClassification | None = None


class DepartureRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    person_id: UUID | None
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
