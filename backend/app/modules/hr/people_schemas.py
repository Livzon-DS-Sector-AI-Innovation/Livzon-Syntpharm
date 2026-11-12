"""Response schemas for the read-only 员工档案 personnel browser (ticket #198)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.modules.hr.org_schemas import OrgPathNode


class EmployeeProfileListItem(BaseModel):
    id: str
    open_id: str
    name: str
    avatar_url: str = ""
    department_ids: list[str] = Field(default_factory=list)
    department_names: list[str] = Field(default_factory=list)
    department_path: list[OrgPathNode] = Field(default_factory=list)
    department_level1_name: str = ""
    department_level2_name: str = ""
    job_title_name: str = ""
    staff_status: int | None = None
    staff_status_label: str = "—"
    is_resigned: bool = False
    last_synced_at: datetime | None = None


class EmployeeProfileListData(BaseModel):
    items: list[EmployeeProfileListItem] = Field(default_factory=list)
    last_synced_at: datetime | None = None


class EmployeeProfileListApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: EmployeeProfileListData
    meta: dict[str, Any] | None = None


class EmployeeProfileDetail(BaseModel):
    id: str
    open_id: str
    name: str
    mobile: str = ""
    email: str = ""
    enterprise_email: str = ""
    email_aliases: list[str] = Field(default_factory=list)
    gender: int | None = None
    gender_label: str = "未知"
    description: str = ""
    avatar_72: str = ""
    avatar_240: str = ""
    avatar_640: str = ""
    avatar_origin: str = ""
    avatar_url: str = ""
    background_image: str = ""
    geo_name: str = ""
    active_status: int | None = None
    active_status_label: str = "—"
    is_resigned: bool = False
    resign_time: str = ""
    is_admin: bool = False
    is_primary_admin: bool = False
    data_source: int | None = None
    data_source_label: str = "—"
    employee_no: str = ""
    job_title_id: str = ""
    job_title_name: str = ""
    hire_date: date | None = None
    employment_type: int | None = None
    staff_status: int | None = None
    staff_status_label: str = "—"
    work_country_or_region: str = ""
    work_place_id: str = ""
    work_place_name: str = ""
    work_station: str = ""
    extension_number: str = ""
    dotted_line_leader_ids: list[str] = Field(default_factory=list)
    resign_date: date | None = None
    resign_type: str = ""
    resign_reason: str = ""
    resign_remark: str = ""
    positions: list[dict[str, str]] = Field(default_factory=list)
    job_level_id: str = ""
    job_level_name: str = ""
    job_family_id: str = ""
    job_family_name: str = ""
    department_ids: list[str] = Field(default_factory=list)
    department_names: list[str] = Field(default_factory=list)
    department_path: list[OrgPathNode] = Field(default_factory=list)
    department_level1_name: str = ""
    department_level2_name: str = ""
    last_synced_at: datetime | None = None


class EmployeeProfileDetailApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: EmployeeProfileDetail
    meta: dict[str, Any] | None = None
