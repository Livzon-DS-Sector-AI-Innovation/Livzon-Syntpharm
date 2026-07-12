# mypy: ignore-errors
"""IPQC (In-Process Quality Control) inspection API routes"""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.core.response import ApiResponse  # type: ignore[attr-defined]
from app.modules.quality.qms.ipqc_schemas import (
    IPQCApprovalCreate,
    IPQCApprovalRecordResponse,
    IPQCInspectionCreate,
    IPQCInspectionFilter,
    IPQCInspectionListResponse,
    IPQCInspectionResponse,
    IPQCInspectionUpdate,
)
from app.modules.quality.qms.ipqc_service import IPQCInspectionService

router = APIRouter(prefix="/ipqc", tags=["IPQC检验"])


def get_ipqc_service(session: AsyncSession = Depends(get_db)) -> IPQCInspectionService:
    return IPQCInspectionService(session)


@router.post("/inspections", response_model=ApiResponse, status_code=201)
async def post(
    data: IPQCInspectionCreate,
    service: IPQCInspectionService = Depends(get_ipqc_service),
    current_user: CurrentUser = None,
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """创建IPQC检验单"""
    try:
        user_id = current_user.id if current_user else None
        inspection = await service.create_inspection(data, user_id)
        return ApiResponse(
            message="创建成功",
            data=IPQCInspectionResponse.model_validate(inspection),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/inspections", response_model=dict)
async def get(
    inspection_no: str | None = Query(None, description="检验单号"),
    batch_no: str | None = Query(None, description="批次号"),
    product_code: str | None = Query(None, description="产品编码"),
    product_name: str | None = Query(None, description="产品名称"),
    process_stage: str | None = Query(None, description="工序/工段"),
    status: str | None = Query(None, description="状态"),
    inspection_conclusion: str | None = Query(None, description="检验结论"),
    batch_locked: bool | None = Query(None, description="批次是否锁定"),
    start_date: str | None = Query(None, description="开始日期"),
    end_date: str | None = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: IPQCInspectionService = Depends(get_ipqc_service),
    current_user: CurrentUser = None,
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """获取IPQC检验单列表"""
    filters = IPQCInspectionFilter(
        inspection_no=inspection_no,
        batch_no=batch_no,
        product_code=product_code,
        product_name=product_name,
        process_stage=process_stage,
        status=status,
        inspection_conclusion=inspection_conclusion,
        batch_locked=batch_locked,
        start_date=datetime.fromisoformat(start_date) if start_date else None,
        end_date=datetime.fromisoformat(end_date) if end_date else None,
    )
    items, total = await service.get_inspection_list(filters, (page - 1) * page_size, page_size)
    return {
        "items": [IPQCInspectionListResponse.model_validate(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/inspections/{inspection_id}", response_model=ApiResponse)  # type: ignore[no-redef]
async def get(  # noqa: F811
    inspection_id: UUID,
    service: IPQCInspectionService = Depends(get_ipqc_service),
    current_user: CurrentUser = None,
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """获取IPQC检验单详情"""
    try:
        inspection = await service.get_inspection(inspection_id)
        return ApiResponse(data=IPQCInspectionResponse.model_validate(inspection))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/inspections/{inspection_id}", response_model=ApiResponse)
async def put(
    inspection_id: UUID,
    data: IPQCInspectionUpdate,
    service: IPQCInspectionService = Depends(get_ipqc_service),
    current_user: CurrentUser = None,
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """更新IPQC检验单"""
    try:
        user_id = current_user.id if current_user else None
        inspection = await service.update_inspection(inspection_id, data, user_id)
        return ApiResponse(
            message="更新成功",
            data=IPQCInspectionResponse.model_validate(inspection),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/inspections/{inspection_id}")
async def delete(
    inspection_id: UUID,
    service: IPQCInspectionService = Depends(get_ipqc_service),
    current_user: CurrentUser = None,
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """删除IPQC检验单"""
    try:
        user_id = current_user.id if current_user else None
        await service.delete_inspection(inspection_id, user_id)
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/inspections/{inspection_id}/submit", response_model=ApiResponse)  # type: ignore[no-redef]
async def post(  # noqa: F811
    inspection_id: UUID,
    service: IPQCInspectionService = Depends(get_ipqc_service),
    current_user: CurrentUser = None,
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """提交IPQC检验单审批"""
    try:
        user_id = current_user.id if current_user else None
        inspection = await service.submit_for_approval(inspection_id, user_id)
        return ApiResponse(
            message="提交成功",
            data=IPQCInspectionResponse.model_validate(inspection),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/inspections/{inspection_id}/approve", response_model=ApiResponse)  # type: ignore[no-redef]
async def post(  # noqa: F811
    inspection_id: UUID,
    data: IPQCApprovalCreate,
    service: IPQCInspectionService = Depends(get_ipqc_service),
    current_user: CurrentUser = None,
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """审批IPQC检验单"""
    try:
        user_id = current_user.id if current_user else None
        user_name = current_user.name if current_user else ""
        approver_role = "approver"
        inspection = await service.approve_inspection(inspection_id, data, user_id, user_name, approver_role)
        return ApiResponse(
            message="审批完成",
            data=IPQCInspectionResponse.model_validate(inspection),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/inspections/{inspection_id}/approvals",
    response_model=list[IPQCApprovalRecordResponse],
)
async def handler(
    inspection_id: UUID,
    service: IPQCInspectionService = Depends(get_ipqc_service),
    current_user: CurrentUser = None,
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """获取审批记录"""
    approvals = await service.get_approval_records(inspection_id)
    return approvals


@router.post("/inspections/{inspection_id}/lock-batch", response_model=ApiResponse)  # type: ignore[no-redef]
async def post(  # noqa: F811
    inspection_id: UUID,
    reason: str = Query(..., description="锁定原因"),
    service: IPQCInspectionService = Depends(get_ipqc_service),
    current_user: CurrentUser = None,
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """锁定批次"""
    try:
        user_id = current_user.id if current_user else None
        inspection = await service.lock_batch(inspection_id, reason, user_id)
        return ApiResponse(
            message="批次已锁定",
            data=IPQCInspectionResponse.model_validate(inspection),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/inspections/{inspection_id}/unlock-batch", response_model=ApiResponse)  # type: ignore[no-redef]
async def post(  # noqa: F811
    inspection_id: UUID,
    service: IPQCInspectionService = Depends(get_ipqc_service),
    current_user: CurrentUser = None,
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """解锁批次"""
    try:
        user_id = current_user.id if current_user else None
        inspection = await service.unlock_batch(inspection_id, user_id)
        return ApiResponse(
            message="批次已解锁",
            data=IPQCInspectionResponse.model_validate(inspection),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
