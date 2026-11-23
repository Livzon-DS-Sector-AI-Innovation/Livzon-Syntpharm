"""校准管理 API 路由."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.modules.equipment import service
from app.modules.equipment.models import CalibrationPlan
from app.modules.equipment.schemas import (
    CalibrationPlanCreate,
    CalibrationPlanResponse,
    CalibrationPlanUpdate,
    CalibrationRecordCreate,
    CalibrationRecordResponse,
)
from app.platform.identity.public_api import resolve_user_names
from app.shared.schemas import DataResponse

router = APIRouter()


async def _to_responses(db: AsyncSession, plans: list[CalibrationPlan]) -> list[CalibrationPlanResponse]:
    """批量补责任人姓名；一页只多查一次 identity.users。

    姓名不是持久化列，写入通道仍只认 ``responsible_person_id``。
    """
    user_ids = {plan.responsible_person_id for plan in plans if plan.responsible_person_id}
    names = await resolve_user_names(db, user_ids) if user_ids else {}
    responses = [CalibrationPlanResponse.model_validate(plan) for plan in plans]
    for response in responses:
        person_id = response.responsible_person_id
        response.responsible_person_name = names.get(person_id) if person_id else None
    return responses


async def _to_response(db: AsyncSession, plan: CalibrationPlan) -> CalibrationPlanResponse:
    return (await _to_responses(db, [plan]))[0]


# ---------- 校准计划 ----------
@router.post("/plans", summary="新增校准计划")
async def create_calibration_plan(
    data: CalibrationPlanCreate,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("equipment:calibration:create")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[CalibrationPlanResponse]:
    plan = await service.create_calibration_plan(db, data)
    return DataResponse[CalibrationPlanResponse](data=(await _to_response(db, plan)).model_dump(mode="json"))


@router.get("/plans", summary="校准计划列表")
async def list_calibration_plans(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("equipment:calibration:read")),
    equipment_id: uuid.UUID | None = Query(None, description="设备ID"),
    status: str | None = Query(None, description="状态"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页数量"),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[list[CalibrationPlanResponse]]:
    plans, total = await service.get_calibration_plans(
        db,
        equipment_id=equipment_id,
        status=status,
        page=page,
        page_size=page_size,
    )
    return DataResponse[list[CalibrationPlanResponse]](
        data=[plan.model_dump(mode="json") for plan in await _to_responses(db, plans)],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/plans/overdue", summary="查询到期/逾期的校准计划")
async def get_overdue_plans(
    current_user: RequiredUser,
    days: int = Query(30, ge=1, description="提前天数"),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[list[CalibrationPlanResponse]]:
    plans = await service.get_overdue_calibration_plans(db, days)
    return DataResponse[list[CalibrationPlanResponse]](
        data=[plan.model_dump(mode="json") for plan in await _to_responses(db, plans)]
    )


@router.get("/plans/{plan_id}", summary="校准计划详情")
async def get_calibration_plan(
    plan_id: uuid.UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("equipment:calibration:read")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[CalibrationPlanResponse]:
    plan = await service.get_calibration_plan_by_id(db, plan_id)
    return DataResponse[CalibrationPlanResponse](data=(await _to_response(db, plan)).model_dump(mode="json"))


@router.put("/plans/{plan_id}", summary="修改校准计划")
async def update_calibration_plan(
    plan_id: uuid.UUID,
    data: CalibrationPlanUpdate,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("equipment:calibration:update")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[CalibrationPlanResponse]:
    plan = await service.update_calibration_plan(db, plan_id, data)
    return DataResponse[CalibrationPlanResponse](data=(await _to_response(db, plan)).model_dump(mode="json"))


@router.delete("/plans/{plan_id}", summary="删除校准计划")
async def delete_calibration_plan(
    plan_id: uuid.UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("equipment:calibration:delete")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[None]:
    await service.delete_calibration_plan(db, plan_id)
    return DataResponse[None](message="删除成功")


# ---------- 校准记录 ----------
@router.post("/records", summary="新增校准记录")
async def create_calibration_record(
    data: CalibrationRecordCreate,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("equipment:calibration:create")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[CalibrationRecordResponse]:
    record = await service.create_calibration_record(db, data)
    return DataResponse[CalibrationRecordResponse](
        data=CalibrationRecordResponse.model_validate(record).model_dump(mode="json")
    )


@router.get("/records", summary="校准记录列表")
async def list_calibration_records(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("equipment:calibration:read")),
    equipment_id: uuid.UUID | None = Query(None, description="设备ID"),
    plan_id: uuid.UUID | None = Query(None, description="计划ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页数量"),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[list[CalibrationRecordResponse]]:
    records, total = await service.get_calibration_records(
        db,
        equipment_id=equipment_id,
        plan_id=plan_id,
        page=page,
        page_size=page_size,
    )
    return DataResponse[list[CalibrationRecordResponse]](
        data=[CalibrationRecordResponse.model_validate(r).model_dump(mode="json") for r in records],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/records/{record_id}", summary="校准记录详情")
async def get_calibration_record(
    record_id: uuid.UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("equipment:calibration:read")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[CalibrationRecordResponse]:
    record = await service.get_calibration_record_by_id(db, record_id)
    return DataResponse[CalibrationRecordResponse](
        data=CalibrationRecordResponse.model_validate(record).model_dump(mode="json")
    )
