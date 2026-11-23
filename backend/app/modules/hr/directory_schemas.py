"""Response schemas for the HR public directory (ticket #219).

The directory is the single read seam every module uses to pick a department or
a person. It is open to any authenticated user (no ``hr:*`` permission code), so
that quality / safety / equipment pages can load the org tree and the personnel
list without holding HR module permissions.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DirectoryDepartmentNode(BaseModel):
    id: str = Field(..., description="hr.departments.id（业务引用键）")
    code: str = Field("", description="部门编码；供权限数据范围使用")
    name: str
    parent_id: str | None = Field(None, description="父部门 hr.departments.id")
    level: int = Field(0, description="0 = 公司，N = 第 N 级部门")
    path_names: list[str] = Field(default_factory=list, description="根 → 自身的部门名称路径")
    order: int = 0
    children: list[DirectoryDepartmentNode] = Field(default_factory=list)


class DirectoryDepartmentTreeData(BaseModel):
    items: list[DirectoryDepartmentNode] = Field(default_factory=list)


class DirectoryDepartmentTreeApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: DirectoryDepartmentTreeData
    meta: dict[str, Any] | None = None


class DirectoryPersonItem(BaseModel):
    id: str = Field(..., description="hr.employee_profiles.id（业务引用键）")
    name: str
    employee_no: str = ""
    job_title_name: str = ""
    department_names: list[str] = Field(default_factory=list)
    department_path: list[dict[str, str]] = Field(default_factory=list)
    avatar_url: str = ""


class DirectoryPeopleListData(BaseModel):
    items: list[DirectoryPersonItem] = Field(default_factory=list)
    total: int = 0


class DirectoryPeopleListApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: DirectoryPeopleListData
    meta: dict[str, Any] | None = None
