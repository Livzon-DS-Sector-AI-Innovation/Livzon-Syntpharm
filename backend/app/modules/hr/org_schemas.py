"""Response schemas for the 部门管理 org browser (ticket #197)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

SyncStatus = Literal["never", "running", "success", "failed"]


class OrgPathNode(BaseModel):
    id: str
    name: str


class OrgDepartmentNode(BaseModel):
    id: str
    name: str
    level: int = Field(..., description="0 = 公司，N = 第 N 级部门")
    parent_id: str | None = None
    parent_name: str | None = None
    leader_ids: list[str] = Field(default_factory=list)
    leader_names: list[str] = Field(default_factory=list)
    leader_avatars: list[str] = Field(default_factory=list, description="与 leader_names 对齐的头像 URL")
    leader_display: str = Field("—", description="负责人姓名的展示值；未解析时显示 —")
    recursive_members_count: int = 0
    direct_members_count: int = 0
    recursive_departments_count: int = 0
    direct_departments_count: int = 0
    department_path: list[OrgPathNode] = Field(default_factory=list)
    enabled_status: bool | None = None
    order_weight: str | None = None
    data_source: str = "—"
    custom_fields: list[dict[str, Any]] = Field(default_factory=list)
    children: list[OrgDepartmentNode] = Field(default_factory=list)


class OrgDepartmentTreeData(BaseModel):
    companies: list[OrgPathNode] = Field(default_factory=list, description="已配置的同步根公司")
    items: list[OrgDepartmentNode] = Field(default_factory=list)


class OrgDepartmentTreeApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: OrgDepartmentTreeData
    meta: dict[str, Any] | None = None


class OrgSyncStatusData(BaseModel):
    status: SyncStatus = Field("never", description="never / running / success / failed")
    last_synced_at: datetime | None = None
    department_count: int = 0
    people_count: int = 0
    error_message: str | None = None


class OrgSyncStatusApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: OrgSyncStatusData
    meta: dict[str, Any] | None = None


class OrgSyncTriggerApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: OrgSyncStatusData
    meta: dict[str, Any] | None = None
