"""HR org read-only browser API (ticket #197)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.response import build_response
from app.modules.hr.org_schemas import (
    OrgDepartmentNode,
    OrgDepartmentTreeApiResponse,
    OrgDepartmentTreeData,
    OrgSyncStatusApiResponse,
    OrgSyncStatusData,
    OrgSyncTriggerApiResponse,
)
from app.modules.hr.org_service import get_org_tree, get_sync_status, run_manual_org_sync

router = APIRouter(prefix="/org", tags=["HR 组织架构"])


@router.get("/departments", response_model=OrgDepartmentTreeApiResponse, summary="部门树（只读）")
async def list_org_departments(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("hr:departments:read")),
    session: AsyncSession = Depends(get_db),
) -> Any:
    """返回珠海保税区丽珠合成制药有限公司下的两级部门树。"""
    items = await get_org_tree(session)
    data = OrgDepartmentTreeData(items=[OrgDepartmentNode.model_validate(item) for item in items])
    return build_response(data=data.model_dump(mode="json"))


@router.get("/sync-status", response_model=OrgSyncStatusApiResponse, summary="组织架构同步状态")
async def get_org_sync_status(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("hr:departments:read")),
    session: AsyncSession = Depends(get_db),
) -> Any:
    """最近一次同步的时间、成功/失败、部门/人员数量与错误。"""
    data = OrgSyncStatusData.model_validate(await get_sync_status(session))
    return build_response(data=data.model_dump(mode="json"))


@router.post("/sync", response_model=OrgSyncTriggerApiResponse, summary="立即同步组织架构")
async def trigger_org_sync(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("hr:departments:sync")),
    session: AsyncSession = Depends(get_db),
) -> Any:
    """立即同步飞书部门数据；同一时间只允许一个同步任务。"""
    data = OrgSyncStatusData.model_validate(await run_manual_org_sync(session))
    return build_response(data=data.model_dump(mode="json"), message="组织架构同步完成")
