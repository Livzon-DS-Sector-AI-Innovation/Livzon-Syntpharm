"""Holiday API endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.response import ApiResponse, build_response
from app.modules.registration import service
from app.modules.registration.schemas.holiday import (
    HolidayCreate,
    HolidayResponse,
)

router = APIRouter()


@router.get("/", summary="获取节假日列表")
async def list_holidays(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("registration:holiday:read")),
    year: int | None = Query(None, description="年份筛选"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """获取节假日列表"""
    holidays = await service.get_holidays(db, year)
    data = [HolidayResponse.model_validate(h) for h in holidays]
    return build_response(data=data)


@router.post("/", summary="创建节假日")
async def create_holiday(
    current_user: RequiredUser,
    data: HolidayCreate,
    ctx: PermissionContext = Depends(require_permission("registration:holiday:create")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """创建节假日"""
    holiday = await service.create_holiday(db, data)
    return build_response(data=HolidayResponse.model_validate(holiday))


@router.put("/{holiday_id}", summary="更新节假日")
async def update_holiday(
    current_user: RequiredUser,
    holiday_id: uuid.UUID,
    data: HolidayCreate,
    ctx: PermissionContext = Depends(require_permission("registration:holiday:update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """更新节假日"""
    holiday = await service.update_holiday(db, holiday_id, data)
    return build_response(data=HolidayResponse.model_validate(holiday))


@router.delete("/{holiday_id}", summary="删除节假日")
async def delete_holiday(
    current_user: RequiredUser,
    holiday_id: uuid.UUID,
    ctx: PermissionContext = Depends(require_permission("registration:holiday:delete")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """删除节假日"""
    await service.delete_holiday(db, holiday_id)
    return build_response(message="删除成功")
