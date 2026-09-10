"""维护计划管理 API 路由."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, RequiredUser
from app.core.exceptions import AppException
from app.core.response import build_response, paginated_response
from app.modules.equipment import service
from app.modules.equipment.schemas import (
    MaintenancePlanCreate,
    MaintenancePlanResponse,
    MaintenancePlanUpdate,
)
from app.shared.schemas import ApiResponse

router = APIRouter()


def _require_user(current_user: CurrentUser) -> uuid.UUID:
    if not current_user:
        raise AppException(message="需要登录才能执行此操作", status_code=401)
    return current_user.id


@router.post("/", summary="新增维护计划")
async def create_maintenance_plan(
    data: MaintenancePlanCreate,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    _require_user(current_user)
    plan = await service.create_maintenance_plan(db, data)
    return build_response(data=MaintenancePlanResponse.model_validate(plan))


@router.get("/", summary="维护计划列表")
async def list_maintenance_plans(
    current_user: RequiredUser,
    equipment_id: uuid.UUID | None = Query(None, description="设备ID"),
    status: str | None = Query(None, description="状态"),
    keyword: str | None = Query(None, description="关键词搜索"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页数量"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    _require_user(current_user)
    plans, total = await service.get_maintenance_plans(
        db,
        equipment_id=equipment_id,
        status=status,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return paginated_response(
        data=[MaintenancePlanResponse.model_validate(p) for p in plans],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/overdue", summary="查询到期/逾期的维护计划")
async def get_overdue_plans(
    current_user: RequiredUser,
    days: int = Query(0, ge=0, description="提前天数，0=仅逾期"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    _require_user(current_user)
    plans = await service.get_overdue_maintenance_plans(db, days)
    return build_response(data=[MaintenancePlanResponse.model_validate(p) for p in plans])


@router.get("/{plan_id}", summary="维护计划详情")
async def get_maintenance_plan(
    plan_id: uuid.UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    _require_user(current_user)
    plan = await service.get_maintenance_plan_by_id(db, plan_id)
    return build_response(data=MaintenancePlanResponse.model_validate(plan))


@router.put("/{plan_id}", summary="修改维护计划")
async def update_maintenance_plan(
    plan_id: uuid.UUID,
    data: MaintenancePlanUpdate,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    _require_user(current_user)
    plan = await service.update_maintenance_plan(db, plan_id, data)
    return build_response(data=MaintenancePlanResponse.model_validate(plan))


@router.delete("/{plan_id}", summary="删除维护计划")
async def delete_maintenance_plan(
    plan_id: uuid.UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    _require_user(current_user)
    await service.delete_maintenance_plan(db, plan_id)
    return build_response(message="删除成功")
