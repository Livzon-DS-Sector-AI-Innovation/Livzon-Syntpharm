"""HR public directory API (ticket #219).

Every module picks departments and people through these two endpoints instead of
reading the platform identity tables. They only require an authenticated user:
quality / safety / equipment pages must not need ``hr:*`` permission codes to
fill a picker.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import RequiredUser
from app.core.response import build_response
from app.modules.hr.directory_schemas import (
    DirectoryDepartmentNode,
    DirectoryDepartmentTreeApiResponse,
    DirectoryDepartmentTreeData,
    DirectoryPeopleListApiResponse,
    DirectoryPeopleListData,
    DirectoryPersonItem,
)
from app.modules.hr.directory_service import list_department_tree, list_people

router = APIRouter(prefix="/directory", tags=["HR 公共目录"])


@router.get(
    "/departments",
    response_model=DirectoryDepartmentTreeApiResponse,
    summary="公共部门树（全量展开，任意层级可选）",
)
async def get_directory_departments(
    current_user: RequiredUser,
    session: AsyncSession = Depends(get_db),
) -> Any:
    """Return the whole org tree with ``hr.departments.id`` as the reference key."""
    items = await list_department_tree(session)
    data = DirectoryDepartmentTreeData(items=[DirectoryDepartmentNode.model_validate(item) for item in items])
    return build_response(data=data.model_dump(mode="json"))


@router.get(
    "/people",
    response_model=DirectoryPeopleListApiResponse,
    summary="公共人员列表（在任员工，支持关键词与部门筛选）",
)
async def list_directory_people(
    current_user: RequiredUser,
    keyword: str | None = Query(None, description="姓名 / 工号 / 手机号关键词"),
    department_id: str | None = Query(None, description="部门 hr.departments.id；含下级部门"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
) -> Any:
    """Return current employees; historical (removed) rows stay out of pickers."""
    items, total = await list_people(
        session,
        keyword=keyword,
        department_id=department_id,
        offset=offset,
        limit=limit,
    )
    data = DirectoryPeopleListData(
        items=[DirectoryPersonItem.model_validate(item) for item in items],
        total=total,
    )
    return build_response(data=data.model_dump(mode="json"))
