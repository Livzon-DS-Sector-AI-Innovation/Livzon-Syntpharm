"""Quality API routes."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.core.response import ApiResponse
from app.modules.quality.qms.schemas import (
    ApprovalRecordResponse,
    InspectionStandardCopy,
    InspectionStandardCreate,
    InspectionStandardItemResponse,
    InspectionStandardResponse,
    InspectionStandardUpdate,
    ObsoleteSubmit,
)
from app.modules.quality.qms.service import QualityService

router = APIRouter()


# ============ InspectionStandard Routes ============


@router.get("/standards", response_model=ApiResponse, summary="获取检验标准列表")
async def get_standards(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    status: str | None = None,
    material_code: str | None = None,
    material_name: str | None = None,
    material_category: str | None = None,
    pharmacopeia: str | None = None,
    version: str | None = None,
    is_effective: bool | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取检验标准列表"""
    service = QualityService(db)
    skip = (page - 1) * page_size
    standards, total = await service.get_standards(
        skip=skip,
        limit=page_size,
        status=status,
        material_code=material_code,
        material_name=material_name,
        material_category=material_category,
        pharmacopeia=pharmacopeia,
        version=version,
        is_effective=is_effective,
    )
    return ApiResponse(
        data=[InspectionStandardResponse.model_validate(s) for s in standards],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.get(
    "/standards/effective", response_model=ApiResponse, summary="获取已生效的标准列表"
)
async def get_effective_standards(
    material_code: str | None = None,
    material_category: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取已生效的标准列表(用于检验任务选择)"""
    service = QualityService(db)
    standards = await service.get_effective_standards(
        material_code=material_code,
        material_category=material_category,
    )
    return ApiResponse(
        data=[InspectionStandardResponse.model_validate(s) for s in standards]
    )


@router.get(
    "/standards/{standard_id}", response_model=ApiResponse, summary="获取检验标准详情"
)
async def get_standard(
    standard_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取检验标准详情"""
    service = QualityService(db)
    standard = await service.get_standard(standard_id)
    if not standard:
        return ApiResponse(code=404, message="检验标准不存在")
    return ApiResponse(data=InspectionStandardResponse.model_validate(standard))


@router.post("/standards", response_model=ApiResponse, summary="创建检验标准")
async def create_standard(
    data: InspectionStandardCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """创建检验标准"""
    service = QualityService(db)
    standard = await service.create_standard(data)
    await db.commit()
    return ApiResponse(data=InspectionStandardResponse.model_validate(standard))


@router.put(
    "/standards/{standard_id}", response_model=ApiResponse, summary="更新检验标准"
)
async def update_standard(
    standard_id: uuid.UUID,
    data: InspectionStandardUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """更新检验标准"""
    service = QualityService(db)
    try:
        standard = await service.update_standard(standard_id, data)
        if not standard:
            return ApiResponse(code=404, message="检验标准不存在")
        await db.commit()
        return ApiResponse(data=InspectionStandardResponse.model_validate(standard))
    except ValueError as e:
        return ApiResponse(code=400, message=str(e))


@router.delete(
    "/standards/{standard_id}", response_model=ApiResponse, summary="删除检验标准"
)
async def delete_standard(
    standard_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """删除检验标准"""
    service = QualityService(db)
    try:
        result = await service.delete_standard(standard_id)
        if not result:
            return ApiResponse(code=404, message="检验标准不存在")
        await db.commit()
        return ApiResponse(message="删除成功")
    except ValueError as e:
        return ApiResponse(code=400, message=str(e))


@router.post(
    "/standards/{standard_id}/submit", response_model=ApiResponse, summary="提交审批"
)
async def submit_for_approval(
    standard_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """提交审批"""
    service = QualityService(db)
    try:
        standard = await service.submit_for_approval(standard_id)
        if not standard:
            return ApiResponse(code=404, message="检验标准不存在")
        await db.commit()
        return ApiResponse(data=InspectionStandardResponse.model_validate(standard))
    except ValueError as e:
        return ApiResponse(code=400, message=str(e))


@router.post(
    "/standards/{standard_id}/approve", response_model=ApiResponse, summary="审批通过"
)
async def approve_standard(
    standard_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """审批通过"""
    service = QualityService(db)
    try:
        user_id = uuid.UUID(current_user.id) if current_user else None
        user_name = current_user.display_name if current_user else "未知"
        standard = await service.approve_standard(standard_id, user_id, user_name)
        if not standard:
            return ApiResponse(code=404, message="检验标准不存在")
        await db.commit()
        return ApiResponse(data=InspectionStandardResponse.model_validate(standard))
    except ValueError as e:
        return ApiResponse(code=400, message=str(e))


@router.post(
    "/standards/{standard_id}/reject", response_model=ApiResponse, summary="驳回标准"
)
async def reject_standard(
    standard_id: uuid.UUID,
    comments: str = Query(..., description="驳回原因"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """驳回标准"""
    service = QualityService(db)
    try:
        user_id = uuid.UUID(current_user.id) if current_user else None
        standard = await service.reject_standard(standard_id, user_id, comments)
        if not standard:
            return ApiResponse(code=404, message="检验标准不存在")
        await db.commit()
        return ApiResponse(data=InspectionStandardResponse.model_validate(standard))
    except ValueError as e:
        return ApiResponse(code=400, message=str(e))


@router.post(
    "/standards/{standard_id}/obsolete", response_model=ApiResponse, summary="提交作废"
)
async def obsolete_standard(
    standard_id: uuid.UUID,
    data: ObsoleteSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """提交作废"""
    service = QualityService(db)
    try:
        standard = await service.obsolete_standard(standard_id, data)
        if not standard:
            return ApiResponse(code=404, message="检验标准不存在")
        await db.commit()
        return ApiResponse(data=InspectionStandardResponse.model_validate(standard))
    except ValueError as e:
        return ApiResponse(code=400, message=str(e))


@router.post("/standards/copy", response_model=ApiResponse, summary="复制标准")
async def copy_standard(
    data: InspectionStandardCopy,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """复制标准(基于旧版快速新建新标准)"""
    service = QualityService(db)
    standard = await service.copy_standard(data)
    if not standard:
        return ApiResponse(code=404, message="源标准不存在")
    await db.commit()
    return ApiResponse(data=InspectionStandardResponse.model_validate(standard))


# ============ InspectionStandardItem Routes ============


@router.get(
    "/standards/{standard_id}/items",
    response_model=ApiResponse,
    summary="获取检验项目列表",
)
async def get_standard_items(
    standard_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取检验项目列表"""
    from app.modules.quality.qms.repository import QualityRepository

    repo = QualityRepository(db)
    items = await repo.get_items_by_standard(standard_id)
    return ApiResponse(
        data=[InspectionStandardItemResponse.model_validate(i) for i in items]
    )


# ============ ApprovalRecord Routes ============


@router.get(
    "/standards/{standard_id}/approvals",
    response_model=ApiResponse,
    summary="获取审批记录",
)
async def get_approval_records(
    standard_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取审批记录"""
    from app.modules.quality.qms.repository import QualityRepository

    repo = QualityRepository(db)
    records = await repo.get_approval_records(standard_id)
    return ApiResponse(data=[ApprovalRecordResponse.model_validate(r) for r in records])
