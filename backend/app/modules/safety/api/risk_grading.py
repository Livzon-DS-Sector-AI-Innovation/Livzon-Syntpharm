"""Safety API — 风险分级管控台账（作业活动危险源，LEC）。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import RequiredUser
from app.modules.safety.schemas.risk_grading import (
    WorkActivityHazardApiResponse,
    WorkActivityHazardCreate,
    WorkActivityHazardListApiResponse,
    WorkActivityHazardListMeta,
    WorkActivityHazardResponse,
)
from app.modules.safety.service.risk_grading import WorkActivityHazardService

work_activity_hazards_router = APIRouter()


@work_activity_hazards_router.get(
    "/work-activity-hazards",
    response_model=WorkActivityHazardListApiResponse,
    summary="获取作业活动危险源台账列表",
)
async def list_work_activity_hazards(
    current_user: RequiredUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """按创建时间倒序返回作业活动危险源台账。"""
    service = WorkActivityHazardService(db)
    skip = (page - 1) * page_size
    items, total = await service.list_hazards(skip, page_size)
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
