# mypy: ignore-errors
"""Safety API — special_ops_permits endpoints."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.core.exceptions import NotFoundException
from app.modules.safety.schemas import (
    SpecialOperationPermitApiResponse,
    SpecialOperationPermitCreate,
    SpecialOperationPermitListApiResponse,
    SpecialOperationPermitResponse,
    SpecialOperationPermitUpdate,
)
from app.modules.safety.service import (
    SpecialOperationService,
)

special_ops_permits_router = APIRouter()


@special_ops_permits_router.get(
    "/special-operation-permits",
    response_model=SpecialOperationPermitListApiResponse,
    summary="获取特殊作业票列表",
)
async def handler(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    status: str | None = None,
    operation_type: str | None = None,
    operation_level: str | None = None,
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """获取特殊作业票列表"""
    service = SpecialOperationService(db)
    skip = (page - 1) * page_size
    items, total = await service.get_permits(skip, page_size, status, operation_type, operation_level, keyword)
    return SpecialOperationPermitListApiResponse(
        data=[SpecialOperationPermitResponse.model_validate(p) for p in items],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@special_ops_permits_router.post(  # type: ignore[no-redef]
    "/special-operation-permits",
    response_model=SpecialOperationPermitApiResponse,
    summary="创建特殊作业票",
)
async def handler(  # noqa: F811
    data: SpecialOperationPermitCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """创建特殊作业票"""
    service = SpecialOperationService(db)
    item = await service.create_permit(data)
    await db.commit()
    return SpecialOperationPermitApiResponse(data=SpecialOperationPermitResponse.model_validate(item))


@special_ops_permits_router.get(  # type: ignore[no-redef]
    "/special-operation-permits/{permit_id}",
    response_model=SpecialOperationPermitApiResponse,
    summary="获取特殊作业票详情",
)
async def handler(  # noqa: F811
    permit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """获取特殊作业票详情"""
    service = SpecialOperationService(db)
    item = await service.get_permit(permit_id)
    if not item:
        raise NotFoundException(resource="作业票")
    return SpecialOperationPermitApiResponse(data=SpecialOperationPermitResponse.model_validate(item))


@special_ops_permits_router.put(  # type: ignore[no-redef]
    "/special-operation-permits/{permit_id}",
    response_model=SpecialOperationPermitApiResponse,
    summary="更新特殊作业票",
)
async def handler(  # noqa: F811
    permit_id: uuid.UUID,
    data: SpecialOperationPermitUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """更新特殊作业票"""
    service = SpecialOperationService(db)
    item = await service.update_permit(permit_id, data)
    if not item:
        raise NotFoundException(resource="作业票")
    await db.commit()
    return SpecialOperationPermitApiResponse(data=SpecialOperationPermitResponse.model_validate(item))


@special_ops_permits_router.delete(  # type: ignore[no-redef]
    "/special-operation-permits/{permit_id}",
    response_model=SpecialOperationPermitApiResponse,
    summary="删除特殊作业票",
)
async def handler(  # noqa: F811
    permit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """删除特殊作业票"""
    service = SpecialOperationService(db)
    result = await service.delete_permit(permit_id)
    if not result:
        raise NotFoundException(resource="作业票")
    await db.commit()
    return SpecialOperationPermitApiResponse(code=200, message="删除成功", data=None)


# ==================== 特殊作业票工作流 Routes ====================


@special_ops_permits_router.post(  # type: ignore[no-redef]
    "/special-operation-permits/{permit_id}/submit",
    response_model=SpecialOperationPermitApiResponse,
    summary="提交作业票",
)
async def handler(  # noqa: F811
    permit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """提交作业票（草稿→已提交）"""
    service = SpecialOperationService(db)
    item = await service.submit_permit(permit_id)
    if not item:
        raise ValueError("无法提交，当前状态不允许")
    await db.commit()
    return SpecialOperationPermitApiResponse(data=SpecialOperationPermitResponse.model_validate(item))


@special_ops_permits_router.post(  # type: ignore[no-redef]
    "/special-operation-permits/{permit_id}/approve",
    response_model=SpecialOperationPermitApiResponse,
    summary="审批作业票",
)
async def handler(  # noqa: F811
    permit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """审批作业票（已提交→已审批）"""
    service = SpecialOperationService(db)
    item = await service.approve_permit(permit_id)
    if not item:
        raise ValueError("无法审批，当前状态不允许")
    await db.commit()
    return SpecialOperationPermitApiResponse(data=SpecialOperationPermitResponse.model_validate(item))


@special_ops_permits_router.post(  # type: ignore[no-redef]
    "/special-operation-permits/{permit_id}/reject",
    response_model=SpecialOperationPermitApiResponse,
    summary="驳回作业票",
)
async def handler(  # noqa: F811
    permit_id: uuid.UUID,
    reason: str = Query(..., description="驳回原因"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """驳回作业票（已提交→已驳回）"""
    service = SpecialOperationService(db)
    item = await service.reject_permit(permit_id, reason)
    if not item:
        raise ValueError("无法驳回，当前状态不允许")
    await db.commit()
    return SpecialOperationPermitApiResponse(data=SpecialOperationPermitResponse.model_validate(item))


@special_ops_permits_router.post(  # type: ignore[no-redef]
    "/special-operation-permits/{permit_id}/start",
    response_model=SpecialOperationPermitApiResponse,
    summary="开始作业",
)
async def handler(  # noqa: F811
    permit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """开始作业（已审批→作业中）"""
    service = SpecialOperationService(db)
    item = await service.start_permit(permit_id)
    if not item:
        raise ValueError("无法开始作业，当前状态不允许")
    await db.commit()
    return SpecialOperationPermitApiResponse(data=SpecialOperationPermitResponse.model_validate(item))


@special_ops_permits_router.post(  # type: ignore[no-redef]
    "/special-operation-permits/{permit_id}/complete",
    response_model=SpecialOperationPermitApiResponse,
    summary="完工验收",
)
async def handler(  # noqa: F811
    permit_id: uuid.UUID,
    method: str = Query(..., description="完工方式: normal/early_termination"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """完工验收（作业中→已完工）"""
    service = SpecialOperationService(db)
    item = await service.complete_permit(permit_id, method)
    if not item:
        raise ValueError("无法完工，当前状态不允许")
    await db.commit()
    return SpecialOperationPermitApiResponse(data=SpecialOperationPermitResponse.model_validate(item))


@special_ops_permits_router.post(  # type: ignore[no-redef]
    "/special-operation-permits/{permit_id}/archive",
    response_model=SpecialOperationPermitApiResponse,
    summary="归档作业票",
)
async def handler(  # noqa: F811
    permit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """归档作业票（已完工→已归档）"""
    service = SpecialOperationService(db)
    item = await service.archive_permit(permit_id)
    if not item:
        raise ValueError("无法归档，当前状态不允许")
    await db.commit()
    return SpecialOperationPermitApiResponse(data=SpecialOperationPermitResponse.model_validate(item))
