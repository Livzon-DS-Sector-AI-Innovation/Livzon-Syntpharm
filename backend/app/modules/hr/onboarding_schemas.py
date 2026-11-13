"""Request/response schemas for the 2026 入职台账 (ticket #199)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.modules.hr.onboarding_domain import (
    EducationLevel,
    Gender,
    GroupClassification,
    JoinCategory,
    PersonnelIdentity,
    PositionLevel,
)

SerialNo = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]
DepartmentName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
OptionalDepartmentName = Annotated[str, StringConstraints(strip_whitespace=True, max_length=64)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
Position = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
Mobile = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]
Age = Annotated[int, Field(ge=16, le=100)]


class OnboardingRecordCreate(BaseModel):
    """2026 入职台账录入字段；除二级部门可为空外全部必填。"""

    serial_no: SerialNo = Field(..., description="流水号")
    department_level1: DepartmentName = Field(..., description="一级部门")
    department_level2: OptionalDepartmentName = Field("", description="二级部门（可空）")
    name: Name = Field(..., description="姓名")
    position: Position = Field(..., description="岗位")
    position_level: PositionLevel = Field(..., description="岗位层级")
    personnel_identity: PersonnelIdentity = Field(..., description="人员身份")
    hire_date: date = Field(..., description="入职日期")
    join_category: JoinCategory = Field(..., description="入职类别")
    education: EducationLevel = Field(..., description="学历")
    gender: Gender = Field(..., description="性别")
    age: Age = Field(..., description="年龄")
    mobile: Mobile = Field(..., description="手机号码")
    group_classification: GroupClassification = Field(..., description="集团月报表人员分类")


class OnboardingRecordUpdate(BaseModel):
    """部分更新；未传字段不变，传空值或非法选项会被拒绝。"""

    serial_no: SerialNo | None = None
    department_level1: DepartmentName | None = None
    department_level2: DepartmentName | None = None
    name: Name | None = None
    position: Position | None = None
    position_level: PositionLevel | None = None
    personnel_identity: PersonnelIdentity | None = None
    hire_date: date | None = None
    join_category: JoinCategory | None = None
    education: EducationLevel | None = None
    gender: Gender | None = None
    age: Age | None = None
    mobile: Mobile | None = None
    group_classification: GroupClassification | None = None


class OnboardingRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    serial_no: str
    department_level1: str
    department_level2: str
    name: str
    position: str
    position_level: str
    personnel_identity: str
    hire_date: date
    join_category: str
    education: str
    gender: str
    age: int
    mobile: str
    group_classification: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class OnboardingRecordListApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: list[OnboardingRecordResponse]
    meta: dict[str, Any] | None = None


class OnboardingRecordApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: OnboardingRecordResponse
    meta: dict[str, Any] | None = None


class OnboardingRecordDeleteApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: None = None
    meta: dict[str, Any] | None = None
