# mypy: ignore-errors
"""FQC (Finished Product Quality Control) inspection API routes"""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.core.response import ApiResponse, success_response
from app.modules.quality.qms.fqc_schemas import (
    FQCApprovalCreate,
    FQCApprovalRecordResponse,
    FQCInspectionCreate,
    FQCInspectionFilter,
    FQCInspectionListResponse,
    FQCInspectionResponse,
    FQCInspectionUpdate,
)
from app.modules.quality.qms.fqc_service import FQCInspectionService

router = APIRouter(prefix="/fqc", tags=["FQC检验"])


def get_fqc_service(session: AsyncSession = Depends(get_db)) -> FQCInspectionService:
    return FQCInspectionService(session)


@router.post("/inspections", response_model=ApiResponse, status_code=201)
async def post(
    data: FQCInspectionCreate,
    service: FQCInspectionService = Depends(get_fqc_service),
    current_user: CurrentUser = None,
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """创建FQC检验单"""
    try:
        user_id = current_user.id if current_user else None
        inspection = await service.create_inspection(data, user_id)
        return ApiResponse(
            message="创建成功",
            data=FQCInspectionResponse.model_validate(inspection),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/inspections", response_model=dict)
async def get(
    inspection_no: str | None = Query(None, description="检验单号"),
    batch_no: str | None = Query(None, description="成品生产批号"),
    product_code: str | None = Query(None, description="成品物料编码"),
    product_name: str | None = Query(None, description="产品名称"),
    production_workshop: str | None = Query(None, description="生产车间"),
    status: str | None = Query(None, description="状态"),
    inspection_conclusion: str | None = Query(None, description="检验结论"),
    release_status: str | None = Query(None, description="放行状态"),
    batch_locked: bool | None = Query(None, description="批次是否锁定"),
    start_date: str | None = Query(None, description="开始日期"),
    end_date: str | None = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: FQCInspectionService = Depends(get_fqc_service),
    current_user: CurrentUser = None,
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """获取FQC检验单列表"""
    filters = FQCInspectionFilter(
        inspection_no=inspection_no,
        batch_no=batch_no,
        product_code=product_code,
        product_name=product_name,
        production_workshop=production_workshop,
        status=status,
        inspection_conclusion=inspection_conclusion,
        release_status=release_status,
        batch_locked=batch_locked,
        start_date=datetime.fromisoformat(start_date) if start_date else None,
        end_date=datetime.fromisoformat(end_date) if end_date else None,
    )
    items, total = await service.get_inspection_list(filters, (page - 1) * page_size, page_size)
    return {
        "items": [FQCInspectionListResponse.model_validate(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/inspections/{inspection_id}", response_model=ApiResponse)  # type: ignore[no-redef]
async def get(  # noqa: F811
    inspection_id: UUID,
    service: FQCInspectionService = Depends(get_fqc_service),
    current_user: CurrentUser = None,
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """获取FQC检验单详情"""
    try:
        inspection = await service.get_inspection(inspection_id)
        return ApiResponse(data=FQCInspectionResponse.model_validate(inspection))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/inspections/{inspection_id}", response_model=ApiResponse)
async def put(
    inspection_id: UUID,
    data: FQCInspectionUpdate,
    service: FQCInspectionService = Depends(get_fqc_service),
    current_user: CurrentUser = None,
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """更新FQC检验单"""
    try:
        user_id = current_user.id if current_user else None
        inspection = await service.update_inspection(inspection_id, data, user_id)
        return ApiResponse(
            message="更新成功",
            data=FQCInspectionResponse.model_validate(inspection),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/inspections/{inspection_id}")
async def delete(
    inspection_id: UUID,
    service: FQCInspectionService = Depends(get_fqc_service),
    current_user: CurrentUser = None,
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """删除FQC检验单"""
    try:
        user_id = current_user.id if current_user else None
        await service.delete_inspection(inspection_id, user_id)
        return success_response(message="删除成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/inspections/{inspection_id}/submit", response_model=ApiResponse)  # type: ignore[no-redef]
async def post(  # noqa: F811
    inspection_id: UUID,
    service: FQCInspectionService = Depends(get_fqc_service),
    current_user: CurrentUser = None,
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """提交FQC检验单审批"""
    try:
        user_id = current_user.id if current_user else None
        inspection = await service.submit_for_approval(inspection_id, user_id)
        return ApiResponse(
            message="提交成功",
            data=FQCInspectionResponse.model_validate(inspection),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/inspections/{inspection_id}/approve", response_model=ApiResponse)  # type: ignore[no-redef]
async def post(  # noqa: F811
    inspection_id: UUID,
    data: FQCApprovalCreate,
    service: FQCInspectionService = Depends(get_fqc_service),
    current_user: CurrentUser = None,
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """审批FQC检验单"""
    try:
        user_id = current_user.id if current_user else None
        user_name = current_user.name if current_user else ""
        approver_role = "approver"
        inspection = await service.approve_inspection(inspection_id, data, user_id, user_name, approver_role)
        return ApiResponse(
            message="审批完成",
            data=FQCInspectionResponse.model_validate(inspection),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/inspections/{inspection_id}/approvals",
    response_model=list[FQCApprovalRecordResponse],
)
async def handler(
    inspection_id: UUID,
    service: FQCInspectionService = Depends(get_fqc_service),
    current_user: CurrentUser = None,
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """获取审批记录"""
    approvals = await service.get_approval_records(inspection_id)
    return approvals


@router.post("/inspections/{inspection_id}/reinspection", response_model=ApiResponse)  # type: ignore[no-redef]
async def post(  # noqa: F811
    inspection_id: UUID,
    reason: str = Query(..., description="复检原因"),
    service: FQCInspectionService = Depends(get_fqc_service),
    current_user: CurrentUser = None,
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """申请复检"""
    try:
        user_id = current_user.id if current_user else None
        inspection = await service.apply_reinspection(inspection_id, reason, user_id)
        return ApiResponse(
            message="复检申请成功",
            data=FQCInspectionResponse.model_validate(inspection),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/inspections/{inspection_id}/release", response_model=ApiResponse)  # type: ignore[no-redef]
async def post(  # noqa: F811
    inspection_id: UUID,
    release_reason: str | None = Query(None, description="放行说明"),
    service: FQCInspectionService = Depends(get_fqc_service),
    current_user: CurrentUser = None,
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """放行成品"""
    try:
        user_id = current_user.id if current_user else None
        inspection = await service.release_inspection(inspection_id, release_reason, user_id)
        return ApiResponse(
            message="放行成功",
            data=FQCInspectionResponse.model_validate(inspection),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/inspections/{inspection_id}/lock-batch", response_model=ApiResponse)  # type: ignore[no-redef]
async def post(  # noqa: F811
    inspection_id: UUID,
    reason: str = Query(..., description="锁定原因"),
    service: FQCInspectionService = Depends(get_fqc_service),
    current_user: CurrentUser = None,
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """锁定批次"""
    try:
        user_id = current_user.id if current_user else None
        inspection = await service.lock_batch(inspection_id, reason, user_id)
        return ApiResponse(
            message="批次已锁定",
            data=FQCInspectionResponse.model_validate(inspection),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/inspections/{inspection_id}/unlock-batch", response_model=ApiResponse)  # type: ignore[no-redef]
async def post(  # noqa: F811
    inspection_id: UUID,
    service: FQCInspectionService = Depends(get_fqc_service),
    current_user: CurrentUser = None,
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """解锁批次"""
    try:
        user_id = current_user.id if current_user else None
        inspection = await service.unlock_batch(inspection_id, user_id)
        return ApiResponse(
            message="批次已解锁",
            data=FQCInspectionResponse.model_validate(inspection),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
