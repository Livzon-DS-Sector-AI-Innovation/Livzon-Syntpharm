"""HTTP API for the 2026 入职台账 (ticket #199)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.response import build_response, paginated_response
from app.modules.hr.onboarding_schemas import (
    OnboardingRecordApiResponse,
    OnboardingRecordCreate,
    OnboardingRecordDeleteApiResponse,
    OnboardingRecordListApiResponse,
    OnboardingRecordResponse,
    OnboardingRecordUpdate,
)
from app.modules.hr.onboarding_service import OnboardingRecordService

router = APIRouter(prefix="/onboarding-records", tags=["HR 入职台账"])


def get_onboarding_service(session: AsyncSession = Depends(get_db)) -> OnboardingRecordService:
    return OnboardingRecordService(session)


@router.get("", response_model=OnboardingRecordListApiResponse, summary="入职台账列表")
async def list_onboarding_records(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("hr:onboarding-records:read")),
    keyword: str | None = Query(None, description="流水号 / 姓名 / 部门 / 岗位关键词"),
    department: str | None = Query(None, description="一级或二级部门筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    service: OnboardingRecordService = Depends(get_onboarding_service),
) -> Any:
    records, total = await service.list_records(
        keyword=keyword,
        department=department,
        page=page,
        page_size=page_size,
    )
    data = [OnboardingRecordResponse.model_validate(record).model_dump(mode="json") for record in records]
    return paginated_response(data=data, page=page, page_size=page_size, total=total)


@router.post("", response_model=OnboardingRecordApiResponse, summary="新建入职记录")
async def create_onboarding_record(
    payload: OnboardingRecordCreate,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("hr:onboarding-records:create")),
    service: OnboardingRecordService = Depends(get_onboarding_service),
) -> Any:
    record = await service.create_record(payload)
    data = OnboardingRecordResponse.model_validate(record).model_dump(mode="json")
    return build_response(data=data, message="入职记录创建成功")


@router.get("/{record_id}", response_model=OnboardingRecordApiResponse, summary="入职记录详情")
async def get_onboarding_record(
    record_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("hr:onboarding-records:read")),
    service: OnboardingRecordService = Depends(get_onboarding_service),
) -> Any:
    record = await service.get_record(record_id)
    data = OnboardingRecordResponse.model_validate(record).model_dump(mode="json")
    return build_response(data=data)


@router.put("/{record_id}", response_model=OnboardingRecordApiResponse, summary="更新入职记录")
async def update_onboarding_record(
    record_id: UUID,
    payload: OnboardingRecordUpdate,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("hr:onboarding-records:update")),
    service: OnboardingRecordService = Depends(get_onboarding_service),
) -> Any:
    record = await service.update_record(record_id, payload)
    data = OnboardingRecordResponse.model_validate(record).model_dump(mode="json")
    return build_response(data=data, message="入职记录更新成功")


@router.delete("/{record_id}", response_model=OnboardingRecordDeleteApiResponse, summary="删除入职记录")
async def delete_onboarding_record(
    record_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("hr:onboarding-records:delete")),
    service: OnboardingRecordService = Depends(get_onboarding_service),
) -> Any:
    await service.delete_record(record_id)
    return build_response(message="入职记录删除成功")
