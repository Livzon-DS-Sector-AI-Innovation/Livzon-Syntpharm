"""HTTP API for the 2026 离职台账 (ticket #200)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.response import build_response, paginated_response
from app.modules.hr.departure_schemas import (
    DepartureRecordApiResponse,
    DepartureRecordCreate,
    DepartureRecordDeleteApiResponse,
    DepartureRecordListApiResponse,
    DepartureRecordResponse,
    DepartureRecordUpdate,
)
from app.modules.hr.departure_service import DepartureRecordService

router = APIRouter(prefix="/departure-records", tags=["HR 离职台账"])


def get_departure_service(session: AsyncSession = Depends(get_db)) -> DepartureRecordService:
    return DepartureRecordService(session)


@router.get("", response_model=DepartureRecordListApiResponse, summary="离职台账列表")
async def list_departure_records(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("hr:departure-records:read")),
    keyword: str | None = Query(None, description="姓名 / 部门 / 岗位关键词"),
    department: str | None = Query(None, description="一级或二级部门筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    service: DepartureRecordService = Depends(get_departure_service),
) -> Any:
    records, total = await service.list_records(
        keyword=keyword,
        department=department,
        page=page,
        page_size=page_size,
    )
    data = [DepartureRecordResponse.model_validate(record).model_dump(mode="json") for record in records]
    return paginated_response(data=data, page=page, page_size=page_size, total=total)


@router.post("", response_model=DepartureRecordApiResponse, summary="新建离职记录")
async def create_departure_record(
    payload: DepartureRecordCreate,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("hr:departure-records:create")),
    service: DepartureRecordService = Depends(get_departure_service),
) -> Any:
    record = await service.create_record(payload)
    data = DepartureRecordResponse.model_validate(record).model_dump(mode="json")
    return build_response(data=data, message="离职记录创建成功")


@router.get("/{record_id}", response_model=DepartureRecordApiResponse, summary="离职记录详情")
async def get_departure_record(
    record_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("hr:departure-records:read")),
    service: DepartureRecordService = Depends(get_departure_service),
) -> Any:
    record = await service.get_record(record_id)
    data = DepartureRecordResponse.model_validate(record).model_dump(mode="json")
    return build_response(data=data)


@router.put("/{record_id}", response_model=DepartureRecordApiResponse, summary="更新离职记录")
async def update_departure_record(
    record_id: UUID,
    payload: DepartureRecordUpdate,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("hr:departure-records:update")),
    service: DepartureRecordService = Depends(get_departure_service),
) -> Any:
    record = await service.update_record(record_id, payload)
    data = DepartureRecordResponse.model_validate(record).model_dump(mode="json")
    return build_response(data=data, message="离职记录更新成功")


@router.delete("/{record_id}", response_model=DepartureRecordDeleteApiResponse, summary="删除离职记录")
async def delete_departure_record(
    record_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("hr:departure-records:delete")),
    service: DepartureRecordService = Depends(get_departure_service),
) -> Any:
    await service.delete_record(record_id)
    return build_response(message="离职记录删除成功")
