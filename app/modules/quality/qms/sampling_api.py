"""Sampling management API routes"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.core.response import ApiResponse
from app.modules.quality.qms.sampling_schemas import (
    SamplingOrderCreate,
    SamplingOrderUpdate,
    SamplingOrderResponse,
    SamplingOrderListResponse,
    SamplingApprovalCreate,
    SamplingApprovalRecordResponse,
    SampleRetentionLedgerResponse,
    SamplingOrderFilter,
    RetentionLedgerFilter,
)
from app.modules.quality.qms.sampling_service import SamplingService

router = APIRouter(prefix="/sampling", tags=["取样管理"])


def get_sampling_service(session: AsyncSession = Depends(get_db)) -> SamplingService:
    return SamplingService(session)


@router.post("/orders", response_model=ApiResponse, status_code=201)
async def create_sampling_order(
    data: SamplingOrderCreate,
    service: SamplingService = Depends(get_sampling_service),
    current_user: CurrentUser = None,
):
    """创建取样单"""
    try:
        user_id = current_user.id if current_user else None
        order = await service.create_order(data, user_id)
        return ApiResponse(
            message="创建成功",
            data=SamplingOrderResponse.model_validate(order),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/orders", response_model=dict)
async def get_sampling_orders(
    material_code: Optional[str] = Query(None, description="物料编码"),
    material_name: Optional[str] = Query(None, description="物料名称"),
    sampling_source: Optional[str] = Query(None, description="取样来源"),
    status: Optional[str] = Query(None, description="状态"),
    sampling_result: Optional[str] = Query(None, description="取样判定"),
    order_no: Optional[str] = Query(None, description="单号"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: SamplingService = Depends(get_sampling_service),
    current_user: CurrentUser = None,
):
    """获取取样单列表"""
    filters = SamplingOrderFilter(
        material_code=material_code,
        material_name=material_name,
        sampling_source=sampling_source,
        status=status,
        sampling_result=sampling_result,
        order_no=order_no,
        start_date=datetime.fromisoformat(start_date) if start_date else None,
        end_date=datetime.fromisoformat(end_date) if end_date else None,
    )
    items, total = await service.get_order_list(filters, (page - 1) * page_size, page_size)
    return {
        "items": [SamplingOrderListResponse.model_validate(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/orders/{order_id}", response_model=ApiResponse)
async def get_sampling_order(
    order_id: UUID,
    service: SamplingService = Depends(get_sampling_service),
    current_user: CurrentUser = None,
):
    """获取取样单详情"""
    try:
        order = await service.get_order(order_id)
        return ApiResponse(data=SamplingOrderResponse.model_validate(order))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/orders/{order_id}", response_model=ApiResponse)
async def update_sampling_order(
    order_id: UUID,
    data: SamplingOrderUpdate,
    service: SamplingService = Depends(get_sampling_service),
    current_user: CurrentUser = None,
):
    """更新取样单"""
    try:
        user_id = current_user.id if current_user else None
        order = await service.update_order(order_id, data, user_id)
        return ApiResponse(
            message="更新成功",
            data=SamplingOrderResponse.model_validate(order),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/orders/{order_id}")
async def delete_sampling_order(
    order_id: UUID,
    service: SamplingService = Depends(get_sampling_service),
    current_user: CurrentUser = None,
):
    """删除取样单"""
    try:
        user_id = current_user.id if current_user else None
        await service.delete_order(order_id, user_id)
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/orders/{order_id}/submit", response_model=ApiResponse)
async def submit_sampling_order(
    order_id: UUID,
    service: SamplingService = Depends(get_sampling_service),
    current_user: CurrentUser = None,
):
    """提交取样单审批"""
    try:
        user_id = current_user.id if current_user else None
        order = await service.submit_for_approval(order_id, user_id)
        return ApiResponse(
            message="提交成功",
            data=SamplingOrderResponse.model_validate(order),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/orders/{order_id}/approve", response_model=ApiResponse)
async def approve_sampling_order(
    order_id: UUID,
    data: SamplingApprovalCreate,
    service: SamplingService = Depends(get_sampling_service),
    current_user: CurrentUser = None,
):
    """审批取样单"""
    try:
        user_id = current_user.id if current_user else None
        user_name = current_user.name if current_user else ""
        approver_role = "qa"
        order = await service.approve_order(order_id, data, user_id, user_name, approver_role)
        return ApiResponse(
            message="审批完成",
            data=SamplingOrderResponse.model_validate(order),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/orders/{order_id}/approvals", response_model=list[SamplingApprovalRecordResponse])
async def get_sampling_approvals(
    order_id: UUID,
    service: SamplingService = Depends(get_sampling_service),
    current_user: CurrentUser = None,
):
    """获取审批记录"""
    approvals = await service.get_approval_records(order_id)
    return approvals


@router.get("/retention-ledger", response_model=dict)
async def get_retention_ledger(
    material_code: Optional[str] = Query(None, description="物料编码"),
    material_name: Optional[str] = Query(None, description="物料名称"),
    retention_status: Optional[str] = Query(None, description="留样状态"),
    order_no: Optional[str] = Query(None, description="取样单号"),
    sample_no: Optional[str] = Query(None, description="样品编号"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: SamplingService = Depends(get_sampling_service),
    current_user: CurrentUser = None,
):
    """获取留样台账列表"""
    filters = RetentionLedgerFilter(
        material_code=material_code,
        material_name=material_name,
        retention_status=retention_status,
        order_no=order_no,
        sample_no=sample_no,
    )
    items, total = await service.get_retention_ledger(filters, (page - 1) * page_size, page_size)
    return {
        "items": [SampleRetentionLedgerResponse.model_validate(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/retention-ledger/order/{order_id}", response_model=list[SampleRetentionLedgerResponse])
async def get_retention_by_order(
    order_id: UUID,
    service: SamplingService = Depends(get_sampling_service),
    current_user: CurrentUser = None,
):
    """根据取样单ID获取留样记录"""
    records = await service.get_retention_by_order_id(order_id)
    return records
