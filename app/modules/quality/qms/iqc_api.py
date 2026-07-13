# mypy: ignore-errors
"""IQC (Incoming Quality Control) inspection API routes"""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.core.response import ApiResponse, success_response
from app.modules.quality.qms.iqc_schemas import (
    IQCApprovalCreate,
    IQCApprovalRecordResponse,
    IQCInspectionCreate,
    IQCInspectionFilter,
    IQCInspectionListResponse,
    IQCInspectionResponse,
    IQCInspectionUpdate,
)
from app.modules.quality.qms.iqc_service import IQCInspectionService

router = APIRouter(prefix="/iqc", tags=["IQC检验"])


def get_iqc_service(session: AsyncSession = Depends(get_db)) -> IQCInspectionService:
    return IQCInspectionService(session)


@router.post("/inspections", response_model=ApiResponse, status_code=201)
async def post(
    data: IQCInspectionCreate,
    service: IQCInspectionService = Depends(get_iqc_service),
    current_user: CurrentUser = None,
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """创建IQC检验单"""
    try:
        user_id = current_user.id if current_user else None
        inspection = await service.create_inspection(data, user_id)
        return ApiResponse(
            message="创建成功",
            data=IQCInspectionResponse.model_validate(inspection),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/inspections", response_model=dict)
async def get(
    inspection_no: str | None = Query(None, description="检验单号"),
    material_code: str | None = Query(None, description="物料编码"),
    material_name: str | None = Query(None, description="物料名称"),
    material_category: str | None = Query(None, description="物料类别"),
    supplier_name: str | None = Query(None, description="供应商名称"),
    status: str | None = Query(None, description="状态"),
    inspection_conclusion: str | None = Query(None, description="检验结论"),
    start_date: str | None = Query(None, description="开始日期"),
    end_date: str | None = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: IQCInspectionService = Depends(get_iqc_service),
    current_user: CurrentUser = None,
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """获取IQC检验单列表"""
    filters = IQCInspectionFilter(
        inspection_no=inspection_no,
        material_code=material_code,
        material_name=material_name,
        material_category=material_category,
        supplier_name=supplier_name,
        status=status,
        inspection_conclusion=inspection_conclusion,
        start_date=datetime.fromisoformat(start_date) if start_date else None,
        end_date=datetime.fromisoformat(end_date) if end_date else None,
    )
    items, total = await service.get_inspection_list(filters, (page - 1) * page_size, page_size)
    return {
        "items": [IQCInspectionListResponse.model_validate(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/inspections/{inspection_id}", response_model=ApiResponse)  # type: ignore[no-redef]
async def get(  # noqa: F811
    inspection_id: UUID,
    service: IQCInspectionService = Depends(get_iqc_service),
    current_user: CurrentUser = None,
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """获取IQC检验单详情"""
    try:
        inspection = await service.get_inspection(inspection_id)
        return ApiResponse(data=IQCInspectionResponse.model_validate(inspection))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/inspections/{inspection_id}", response_model=ApiResponse)
async def put(
    inspection_id: UUID,
    data: IQCInspectionUpdate,
    service: IQCInspectionService = Depends(get_iqc_service),
    current_user: CurrentUser = None,
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """更新IQC检验单"""
    try:
        user_id = current_user.id if current_user else None
        inspection = await service.update_inspection(inspection_id, data, user_id)
        return ApiResponse(
            message="更新成功",
            data=IQCInspectionResponse.model_validate(inspection),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/inspections/{inspection_id}")
async def delete(
    inspection_id: UUID,
    service: IQCInspectionService = Depends(get_iqc_service),
    current_user: CurrentUser = None,
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """删除IQC检验单"""
    try:
        user_id = current_user.id if current_user else None
        await service.delete_inspection(inspection_id, user_id)
        return success_response(message="删除成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/inspections/{inspection_id}/submit", response_model=ApiResponse)  # type: ignore[no-redef]
async def post(  # noqa: F811
    inspection_id: UUID,
    service: IQCInspectionService = Depends(get_iqc_service),
    current_user: CurrentUser = None,
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """提交IQC检验单审批"""
    try:
        user_id = current_user.id if current_user else None
        inspection = await service.submit_for_approval(inspection_id, user_id)
        return ApiResponse(
            message="提交成功",
            data=IQCInspectionResponse.model_validate(inspection),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/inspections/{inspection_id}/approve", response_model=ApiResponse)  # type: ignore[no-redef]
async def post(  # noqa: F811
    inspection_id: UUID,
    data: IQCApprovalCreate,
    service: IQCInspectionService = Depends(get_iqc_service),
    current_user: CurrentUser = None,
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """审批IQC检验单"""
    try:
        user_id = current_user.id if current_user else None
        user_name = current_user.name if current_user else ""
        approver_role = "qa"
        inspection = await service.approve_inspection(inspection_id, data, user_id, user_name, approver_role)
        return ApiResponse(
            message="审批完成",
            data=IQCInspectionResponse.model_validate(inspection),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/inspections/{inspection_id}/approvals",
    response_model=list[IQCApprovalRecordResponse],
)
async def handler(
    inspection_id: UUID,
    service: IQCInspectionService = Depends(get_iqc_service),
    current_user: CurrentUser = None,
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """获取审批记录"""
    approvals = await service.get_approval_records(inspection_id)
    return approvals
