"""维护计划管理 API 路由."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.response import build_response, paginated_response
from app.modules.equipment import service
from app.modules.equipment.models import MaintenancePlan
from app.modules.equipment.schemas import (
    MaintenancePlanCreate,
    MaintenancePlanResponse,
    MaintenancePlanUpdate,
)
from app.platform.identity.public_api import resolve_user_names
from app.shared.schemas import ApiResponse

router = APIRouter()


async def _to_responses(db: AsyncSession, plans: list[MaintenancePlan]) -> list[MaintenancePlanResponse]:
    """批量补责任人姓名；一页只多查一次 identity.users。

    姓名不是持久化列，写入通道仍只认 ``responsible_person_id``。
    """
    user_ids = {plan.responsible_person_id for plan in plans if plan.responsible_person_id}
    names = await resolve_user_names(db, user_ids) if user_ids else {}
    responses = [MaintenancePlanResponse.model_validate(plan) for plan in plans]
    for response in responses:
        person_id = response.responsible_person_id
        response.responsible_person_name = names.get(person_id) if person_id else None
    return responses


async def _to_response(db: AsyncSession, plan: MaintenancePlan) -> MaintenancePlanResponse:
    return (await _to_responses(db, [plan]))[0]


@router.post("/", summary="新增维护计划")
async def create_maintenance_plan(
    data: MaintenancePlanCreate,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("equipment:maintenance-plan:create")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    plan = await service.create_maintenance_plan(db, data)
    return build_response(data=await _to_response(db, plan))


@router.get("/", summary="维护计划列表")
async def list_maintenance_plans(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("equipment:maintenance-plan:read")),
    equipment_id: uuid.UUID | None = Query(None, description="设备ID"),
    status: str | None = Query(None, description="状态"),
    keyword: str | None = Query(None, description="关键词搜索"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页数量"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    plans, total = await service.get_maintenance_plans(
        db,
        equipment_id=equipment_id,
        status=status,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return paginated_response(
        data=await _to_responses(db, plans),
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/overdue", summary="查询到期/逾期的维护计划")
async def get_overdue_plans(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("equipment:maintenance-plan:read")),
    days: int = Query(0, ge=0, description="提前天数，0=仅逾期"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    plans = await service.get_overdue_maintenance_plans(db, days)
    return build_response(data=await _to_responses(db, plans))


@router.get("/{plan_id}", summary="维护计划详情")
async def get_maintenance_plan(
    plan_id: uuid.UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("equipment:maintenance-plan:read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    plan = await service.get_maintenance_plan_by_id(db, plan_id)
    return build_response(data=await _to_response(db, plan))


@router.put("/{plan_id}", summary="修改维护计划")
async def update_maintenance_plan(
    plan_id: uuid.UUID,
    data: MaintenancePlanUpdate,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("equipment:maintenance-plan:update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    plan = await service.update_maintenance_plan(db, plan_id, data)
    return build_response(data=await _to_response(db, plan))


@router.delete("/{plan_id}", summary="删除维护计划")
async def delete_maintenance_plan(
    plan_id: uuid.UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("equipment:maintenance-plan:delete")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    await service.delete_maintenance_plan(db, plan_id)
    return build_response(message="删除成功")
