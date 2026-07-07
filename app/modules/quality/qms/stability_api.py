"""Stability Study (稳定性试验) API routes"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.core.response import ApiResponse
from app.modules.quality.qms.stability_schemas import (
    StabilityApprovalCreate,
    StabilityInspectionCreate,
    StabilityInspectionFilter,
    StabilityInspectionListResponse,
    StabilityInspectionResponse,
    StabilityInspectionUpdate,
    StabilitySampleNodeResponse,
    StabilitySampleNodeUpdate,
    StabilityStudyCreate,
    StabilityStudyFilter,
    StabilityStudyListResponse,
    StabilityStudyResponse,
    StabilityStudyUpdate,
)
from app.modules.quality.qms.stability_service import StabilityStudyService

router = APIRouter(prefix="/stability", tags=["稳定性试验管理"])


def get_stability_service(
    session: AsyncSession = Depends(get_db),
) -> StabilityStudyService:
    return StabilityStudyService(session)


# ========== Stability Study Routes ==========


@router.post("/studies", response_model=ApiResponse, status_code=201)
async def create_stability_study(
    data: StabilityStudyCreate,
    service: StabilityStudyService = Depends(get_stability_service),
    current_user: CurrentUser = None,
):
    """创建稳定性试验方案"""
    try:
        user_id = current_user.id if current_user else None
        study = await service.create_study(data, user_id)
        return ApiResponse(
            message="创建成功",
            data=StabilityStudyResponse.model_validate(study),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/studies", response_model=dict)
async def get_stability_studies(
    study_no: str | None = Query(None, description="方案编号"),
    product_code: str | None = Query(None, description="产品编码"),
    product_name: str | None = Query(None, description="产品名称"),
    study_type: str | None = Query(None, description="试验类型"),
    status: str | None = Query(None, description="状态"),
    batch_no: str | None = Query(None, description="批号"),
    start_date: str | None = Query(None, description="开始日期"),
    end_date: str | None = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: StabilityStudyService = Depends(get_stability_service),
    current_user: CurrentUser = None,
):
    """获取稳定性试验方案列表"""
    filters = StabilityStudyFilter(
        study_no=study_no,
        product_code=product_code,
        product_name=product_name,
        study_type=study_type,
        status=status,
        batch_no=batch_no,
        start_date=datetime.fromisoformat(start_date) if start_date else None,
        end_date=datetime.fromisoformat(end_date) if end_date else None,
    )
    items, total = await service.get_study_list(
        filters, (page - 1) * page_size, page_size
    )
    return {
        "items": [StabilityStudyListResponse.model_validate(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/studies/{study_id}", response_model=ApiResponse)
async def get_stability_study(
    study_id: UUID,
    service: StabilityStudyService = Depends(get_stability_service),
    current_user: CurrentUser = None,
):
    """获取稳定性试验方案详情"""
    try:
        study = await service.get_study(study_id)
        return ApiResponse(data=StabilityStudyResponse.model_validate(study))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/studies/{study_id}", response_model=ApiResponse)
async def update_stability_study(
    study_id: UUID,
    data: StabilityStudyUpdate,
    service: StabilityStudyService = Depends(get_stability_service),
    current_user: CurrentUser = None,
):
    """更新稳定性试验方案"""
    try:
        user_id = current_user.id if current_user else None
        study = await service.update_study(study_id, data, user_id)
        return ApiResponse(
            message="更新成功",
            data=StabilityStudyResponse.model_validate(study),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/studies/{study_id}")
async def delete_stability_study(
    study_id: UUID,
    service: StabilityStudyService = Depends(get_stability_service),
    current_user: CurrentUser = None,
):
    """删除稳定性试验方案"""
    try:
        user_id = current_user.id if current_user else None
        await service.delete_study(study_id, user_id)
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/studies/{study_id}/submit", response_model=ApiResponse)
async def submit_stability_study(
    study_id: UUID,
    service: StabilityStudyService = Depends(get_stability_service),
    current_user: CurrentUser = None,
):
    """提交稳定性试验方案"""
    try:
        user_id = current_user.id if current_user else None
        study = await service.submit_study(study_id, user_id)
        return ApiResponse(
            message="提交成功",
            data=StabilityStudyResponse.model_validate(study),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/studies/{study_id}/approve", response_model=ApiResponse)
async def approve_stability_study(
    study_id: UUID,
    data: StabilityApprovalCreate,
    service: StabilityStudyService = Depends(get_stability_service),
    current_user: CurrentUser = None,
):
    """审批稳定性试验方案"""
    try:
        user_id = current_user.id if current_user else None
        user_name = current_user.name if current_user else ""
        role = "approver"
        study = await service.approve_study(study_id, data, user_id, user_name, role)
        return ApiResponse(
            message="审批完成",
            data=StabilityStudyResponse.model_validate(study),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========== Sample Node Routes ==========


@router.get(
    "/studies/{study_id}/sample-nodes", response_model=list[StabilitySampleNodeResponse]
)
async def get_sample_nodes(
    study_id: UUID,
    service: StabilityStudyService = Depends(get_stability_service),
    current_user: CurrentUser = None,
):
    """获取取样节点列表"""
    nodes = await service.get_sample_nodes(study_id)
    return [StabilitySampleNodeResponse.model_validate(node) for node in nodes]


@router.put("/sample-nodes/{node_id}", response_model=ApiResponse)
async def update_sample_node(
    node_id: UUID,
    data: StabilitySampleNodeUpdate,
    service: StabilityStudyService = Depends(get_stability_service),
    current_user: CurrentUser = None,
):
    """更新取样节点"""
    try:
        user_id = current_user.id if current_user else None
        node = await service.update_sample_node(node_id, data, user_id)
        return ApiResponse(
            message="更新成功",
            data=StabilitySampleNodeResponse.model_validate(node),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========== Stability Inspection Routes ==========


@router.post("/inspections", response_model=ApiResponse, status_code=201)
async def create_stability_inspection(
    data: StabilityInspectionCreate,
    service: StabilityStudyService = Depends(get_stability_service),
    current_user: CurrentUser = None,
):
    """创建稳定性检验记录"""
    try:
        user_id = current_user.id if current_user else None
        inspection = await service.create_inspection(data, user_id)
        return ApiResponse(
            message="创建成功",
            data=StabilityInspectionResponse.model_validate(inspection),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/inspections", response_model=dict)
async def get_stability_inspections(
    study_id: UUID | None = Query(None, description="试验ID"),
    study_no: str | None = Query(None, description="方案编号"),
    inspection_no: str | None = Query(None, description="检验单号"),
    batch_no: str | None = Query(None, description="批号"),
    status: str | None = Query(None, description="状态"),
    start_date: str | None = Query(None, description="开始日期"),
    end_date: str | None = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: StabilityStudyService = Depends(get_stability_service),
    current_user: CurrentUser = None,
):
    """获取稳定性检验记录列表"""
    filters = StabilityInspectionFilter(
        study_id=study_id,
        study_no=study_no,
        inspection_no=inspection_no,
        batch_no=batch_no,
        status=status,
        start_date=datetime.fromisoformat(start_date) if start_date else None,
        end_date=datetime.fromisoformat(end_date) if end_date else None,
    )
    items, total = await service.get_inspection_list(
        study_id, (page - 1) * page_size, page_size
    )
    return {
        "items": [
            StabilityInspectionListResponse.model_validate(item) for item in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/inspections/{inspection_id}", response_model=ApiResponse)
async def get_stability_inspection(
    inspection_id: UUID,
    service: StabilityStudyService = Depends(get_stability_service),
    current_user: CurrentUser = None,
):
    """获取稳定性检验记录详情"""
    try:
        inspection = await service.get_inspection(inspection_id)
        return ApiResponse(data=StabilityInspectionResponse.model_validate(inspection))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/inspections/{inspection_id}", response_model=ApiResponse)
async def update_stability_inspection(
    inspection_id: UUID,
    data: StabilityInspectionUpdate,
    service: StabilityStudyService = Depends(get_stability_service),
    current_user: CurrentUser = None,
):
    """更新稳定性检验记录"""
    try:
        user_id = current_user.id if current_user else None
        inspection = await service.update_inspection(inspection_id, data, user_id)
        return ApiResponse(
            message="更新成功",
            data=StabilityInspectionResponse.model_validate(inspection),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/inspections/{inspection_id}/submit", response_model=ApiResponse)
async def submit_stability_inspection(
    inspection_id: UUID,
    service: StabilityStudyService = Depends(get_stability_service),
    current_user: CurrentUser = None,
):
    """提交稳定性检验记录"""
    try:
        user_id = current_user.id if current_user else None
        inspection = await service.submit_inspection(inspection_id, user_id)
        return ApiResponse(
            message="提交成功",
            data=StabilityInspectionResponse.model_validate(inspection),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========== Trend Analysis Routes ==========


@router.get("/studies/{study_id}/trend", response_model=ApiResponse)
async def get_stability_trend(
    study_id: UUID,
    service: StabilityStudyService = Depends(get_stability_service),
    current_user: CurrentUser = None,
):
    """获取稳定性试验趋势数据"""
    try:
        trend_data = await service.get_trend_data(study_id)
        return ApiResponse(data=trend_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
