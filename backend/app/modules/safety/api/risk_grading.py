"""Safety API — 风险分级管控台账（作业活动危险源，LEC）。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import RequiredUser
from app.modules.safety.schemas.risk_grading import (
    EquipmentFacilityHazardApiResponse,
    EquipmentFacilityHazardCreate,
    EquipmentFacilityHazardListApiResponse,
    EquipmentFacilityHazardListMeta,
    EquipmentFacilityHazardResponse,
    WorkActivityHazardApiResponse,
    WorkActivityHazardCreate,
    WorkActivityHazardListApiResponse,
    WorkActivityHazardListMeta,
    WorkActivityHazardResponse,
    WorkActivityHazardUpdate,
)
from app.modules.safety.service.risk_grading import (
    EquipmentFacilityHazardService,
    WorkActivityHazardService,
)

work_activity_hazards_router = APIRouter()

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@work_activity_hazards_router.get(
    "/work-activity-hazards",
    response_model=WorkActivityHazardListApiResponse,
    summary="获取作业活动危险源台账列表",
)
async def list_work_activity_hazards(
    current_user: RequiredUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    control_level: str | None = Query(None, description="管控层级（部门）"),
    evaluation_grade: int | None = Query(None, ge=1, le=4, description="评价级别 1–4"),
    residual_risk: str | None = Query(None, description="残余风险 key"),
    keyword: str | None = Query(None, description="关键字（覆盖各文本字段）"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """按创建时间倒序返回作业活动危险源台账，支持组合筛选与关键字搜索。"""
    service = WorkActivityHazardService(db)
    skip = (page - 1) * page_size
    items, total = await service.list_hazards(
        skip,
        page_size,
        control_level=control_level,
        evaluation_grade=evaluation_grade,
        residual_risk=residual_risk,
        keyword=keyword,
    )
    return WorkActivityHazardListApiResponse(
        data=[WorkActivityHazardResponse.model_validate(item) for item in items],
        meta=WorkActivityHazardListMeta(page=page, page_size=page_size, total=total),
    )


@work_activity_hazards_router.post(
    "/work-activity-hazards",
    response_model=WorkActivityHazardApiResponse,
    summary="新建作业活动危险源台账记录",
)
async def create_work_activity_hazard(
    current_user: RequiredUser,
    data: WorkActivityHazardCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """创建记录；D 与评价级别由服务端计算，D ≤ 20 直接拒绝。"""
    service = WorkActivityHazardService(db)
    item = await service.create_hazard(data)
    await db.commit()
    return WorkActivityHazardApiResponse(data=WorkActivityHazardResponse.model_validate(item))


@work_activity_hazards_router.get(
    "/work-activity-hazards/export",
    summary="导出作业活动危险源台账 .xlsx",
    response_class=Response,
)
async def export_work_activity_hazards(
    current_user: RequiredUser,
    control_level: str | None = Query(None, description="管控层级（部门）"),
    evaluation_grade: int | None = Query(None, ge=1, le=4, description="评价级别 1–4"),
    residual_risk: str | None = Query(None, description="残余风险 key"),
    keyword: str | None = Query(None, description="关键字（覆盖各文本字段）"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """按与列表相同的筛选条件导出当前结果；导出被视为只读动作。"""
    service = WorkActivityHazardService(db)
    content = await service.export_hazards(
        control_level=control_level,
        evaluation_grade=evaluation_grade,
        residual_risk=residual_risk,
        keyword=keyword,
    )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"作业活动危险源台账_{timestamp}.xlsx"
    ascii_filename = f"work_activity_hazards_{timestamp}.xlsx"
    disposition = f"attachment; filename=\"{ascii_filename}\"; filename*=UTF-8''{quote(filename)}"
    return Response(
        content=content,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": disposition},
    )


@work_activity_hazards_router.get(
    "/work-activity-hazards/{hazard_id}",
    response_model=WorkActivityHazardApiResponse,
    summary="获取作业活动危险源台账详情",
)
async def get_work_activity_hazard(
    current_user: RequiredUser,
    hazard_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = WorkActivityHazardService(db)
    item = await service.get_hazard(hazard_id)
    return WorkActivityHazardApiResponse(data=WorkActivityHazardResponse.model_validate(item))


@work_activity_hazards_router.put(
    "/work-activity-hazards/{hazard_id}",
    response_model=WorkActivityHazardApiResponse,
    summary="完整更新作业活动危险源台账记录",
)
async def replace_work_activity_hazard(
    current_user: RequiredUser,
    hazard_id: uuid.UUID,
    data: WorkActivityHazardCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """完整更新（PUT）：所有创建规则重新生效，D 与评价级别由服务端重算。"""
    service = WorkActivityHazardService(db)
    item = await service.update_hazard(hazard_id, WorkActivityHazardUpdate(**data.model_dump()))
    await db.commit()
    return WorkActivityHazardApiResponse(data=WorkActivityHazardResponse.model_validate(item), message="更新成功")


@work_activity_hazards_router.patch(
    "/work-activity-hazards/{hazard_id}",
    response_model=WorkActivityHazardApiResponse,
    summary="部分更新作业活动危险源台账记录",
)
async def update_work_activity_hazard(
    current_user: RequiredUser,
    hazard_id: uuid.UUID,
    data: WorkActivityHazardUpdate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """部分更新（PATCH）：合并现有值后重新套用全部创建规则，并重算 D 与评价级别。"""
    service = WorkActivityHazardService(db)
    item = await service.update_hazard(hazard_id, data)
    await db.commit()
    return WorkActivityHazardApiResponse(data=WorkActivityHazardResponse.model_validate(item), message="更新成功")


@work_activity_hazards_router.delete(
    "/work-activity-hazards/{hazard_id}",
    response_model=WorkActivityHazardApiResponse,
    summary="删除作业活动危险源台账记录（软删除）",
)
async def delete_work_activity_hazard(
    current_user: RequiredUser,
    hazard_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """软删除记录：列表与详情不再返回，但数据行保留。"""
    service = WorkActivityHazardService(db)
    await service.delete_hazard(hazard_id)
    await db.commit()
    return WorkActivityHazardApiResponse(code=200, message="删除成功", data=None)


equipment_facility_hazards_router = APIRouter()


@equipment_facility_hazards_router.get(
    "/equipment-facility-hazards",
    response_model=EquipmentFacilityHazardListApiResponse,
    summary="获取设备设施危险源台账列表",
)
async def list_equipment_facility_hazards(
    current_user: RequiredUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """按创建时间倒序返回设备设施危险源台账。"""
    service = EquipmentFacilityHazardService(db)
    skip = (page - 1) * page_size
    items, total = await service.list_hazards(skip, page_size)
    return EquipmentFacilityHazardListApiResponse(
        data=[EquipmentFacilityHazardResponse.model_validate(item) for item in items],
        meta=EquipmentFacilityHazardListMeta(page=page, page_size=page_size, total=total),
    )


@equipment_facility_hazards_router.post(
    "/equipment-facility-hazards",
    response_model=EquipmentFacilityHazardApiResponse,
    summary="新建设备设施危险源台账记录",
)
async def create_equipment_facility_hazard(
    current_user: RequiredUser,
    data: EquipmentFacilityHazardCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """创建记录；危险评价 R 由服务端按 L/S 查安全风险矩阵计算。"""
    service = EquipmentFacilityHazardService(db)
    item = await service.create_hazard(data)
    await db.commit()
    return EquipmentFacilityHazardApiResponse(data=EquipmentFacilityHazardResponse.model_validate(item))
