"""Read-only 员工档案 personnel API (ticket #198)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.response import build_response
from app.modules.hr.org_schemas import (
    OrgDepartmentNode,
    OrgDepartmentTreeApiResponse,
    OrgDepartmentTreeData,
)
from app.modules.hr.org_service import get_org_tree
from app.modules.hr.org_settings import load_org_scope
from app.modules.hr.people_schemas import (
    EmployeeProfileDetail,
    EmployeeProfileDetailApiResponse,
    EmployeeProfileListApiResponse,
    EmployeeProfileListData,
    EmployeeProfileListItem,
)
from app.modules.hr.people_service import get_person, list_people

router = APIRouter(prefix="/people", tags=["HR 员工档案"])


@router.get("/departments", response_model=OrgDepartmentTreeApiResponse, summary="员工档案部门树（只读）")
async def list_people_departments(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("hr:personnel:read")),
    session: AsyncSession = Depends(get_db),
) -> Any:
    """返回公司根节点下的两级部门树，供员工档案左侧筛选使用。"""
    scope = await load_org_scope(session)
    items = await get_org_tree(session)
    data = OrgDepartmentTreeData(
        company_name=scope.department_name,
        items=[OrgDepartmentNode.model_validate(item) for item in items],
    )
    return build_response(data=data.model_dump(mode="json"))


@router.get("", response_model=EmployeeProfileListApiResponse, summary="员工列表（只读）")
async def list_employee_profiles(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("hr:personnel:read")),
    department_id: str | None = Query(None, description="部门 ID；公司根节点或不传表示全部"),
    status: str | None = Query(None, description="人事状态：在职/离职或飞书枚举值"),
    keyword: str | None = Query(None, description="姓名 / 工号 / 职务 / 部门关键字"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
) -> Any:
    items, total, last_synced_at = await list_people(
        session,
        department_id=department_id,
        status=status,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    data = EmployeeProfileListData(
        items=[EmployeeProfileListItem.model_validate(item) for item in items],
        last_synced_at=last_synced_at,
    )
    return build_response(
        data=data.model_dump(mode="json"),
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/{person_id}", response_model=EmployeeProfileDetailApiResponse, summary="员工详情（只读）")
async def get_employee_profile(
    person_id: str,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("hr:personnel:read")),
    session: AsyncSession = Depends(get_db),
) -> Any:
    """按镜像 id 或飞书 open_id 返回一个人的完整档案。"""
    data = EmployeeProfileDetail.model_validate(await get_person(session, person_id))
    return build_response(data=data.model_dump(mode="json"))
