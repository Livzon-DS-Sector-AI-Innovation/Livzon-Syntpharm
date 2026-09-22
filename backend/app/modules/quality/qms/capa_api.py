"""CAPA API Routes"""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import RequiredUser
from app.modules.quality.qms.capa_schemas import (
    CapaApiResponse,
    CapaCreate,
    CapaListApiResponse,
    CapaResponse,
    CapaUpdate,
    DeptHeadConfirm,
    EvaluationSubmit,
    ExecutionConfirm,
    ExecutionTrackSubmit,
    PartComplete,
)
from app.modules.quality.qms.capa_service import CapaService

capa_router = APIRouter(prefix="/capas", tags=["CAPA管理"])


@capa_router.get("", response_model=CapaListApiResponse, summary="获取 CAPA 列表")
async def list_capas(
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
    capa_code: str | None = Query(None, description="CAPA编号"),
    source: str | None = Query(None, description="来源"),
    category: str | None = Query(None, description="类别"),
    status: str | None = Query(None, description="状态"),
    deviation_id: UUID | None = Query(None, description="关联偏差ID"),
    start_date: datetime | None = Query(None, description="开始日期"),
    end_date: datetime | None = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
) -> Any:
    """获取 CAPA 列表"""
    service = CapaService(db)
    capas, total = await service.list_capas(
        capa_code=capa_code,
        source=source,
        category=category,
        status=status,
        deviation_id=deviation_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )
    
    return CapaListApiResponse(
        data=[CapaResponse(**capa) for capa in capas],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@capa_router.get("/{capa_id}", response_model=CapaApiResponse, summary="获取 CAPA 详情")
async def get_capa(
    capa_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """获取 CAPA 详情"""
    service = CapaService(db)
    capa = await service.get_capa(capa_id)
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found")
    
    return CapaApiResponse(data=CapaResponse(**capa))


@capa_router.post("", response_model=CapaApiResponse, summary="创建 CAPA")
async def create_capa(
    data: CapaCreate,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """创建 CAPA"""
    service = CapaService(db)
    capa = await service.create_capa(data)
    await db.commit()
    
    return CapaApiResponse(data=CapaResponse(**capa))


@capa_router.put("/{capa_id}", response_model=CapaApiResponse, summary="更新 CAPA")
async def update_capa(
    capa_id: UUID,
    data: CapaUpdate,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """更新 CAPA"""
    service = CapaService(db)
    capa = await service.update_capa(capa_id, data)
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found")
    await db.commit()
    
    return CapaApiResponse(data=CapaResponse(**capa))


@capa_router.delete("/{capa_id}", summary="删除 CAPA")
async def delete_capa(
    capa_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """删除 CAPA"""
    service = CapaService(db)
    success = await service.delete_capa(capa_id)
    if not success:
        raise HTTPException(status_code=404, detail="CAPA not found")
    await db.commit()
    
    return {"message": "CAPA deleted successfully"}


@capa_router.post("/{capa_id}/submit", response_model=CapaApiResponse, summary="提交 CAPA")
async def submit_capa(
    capa_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """提交 CAPA"""
    service = CapaService(db)
    try:
        capa = await service.submit_capa(capa_id)
        if not capa:
            raise HTTPException(status_code=404, detail="CAPA not found")
        await db.commit()
        return CapaApiResponse(data=CapaResponse(**capa))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@capa_router.post("/{capa_id}/approve", response_model=CapaApiResponse, summary="审核 CAPA")
async def approve_capa(
    capa_id: UUID,
    current_user: RequiredUser,
    approved: bool = Query(..., description="是否批准"),
    opinion: str = Query(..., description="审核意见"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """审核 CAPA"""
    service = CapaService(db)
    try:
        capa = await service.approve_capa(
            capa_id,
            approver_id=UUID(current_user.id),
            approver_name=current_user.display_name,
            opinion=opinion,
            approved=approved,
        )
        if not capa:
            raise HTTPException(status_code=404, detail="CAPA not found")
        await db.commit()
        return CapaApiResponse(data=CapaResponse(**capa))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@capa_router.post("/{capa_id}/resubmit", response_model=CapaApiResponse, summary="重新提交 CAPA")
async def resubmit_capa(
    capa_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """重新提交 CAPA"""
    service = CapaService(db)
    try:
        capa = await service.resubmit_capa(capa_id)
        if not capa:
            raise HTTPException(status_code=404, detail="CAPA not found")
        await db.commit()
        return CapaApiResponse(data=CapaResponse(**capa))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@capa_router.post("/{capa_id}/execution-tracks", response_model=CapaApiResponse, summary="添加执行跟踪")
async def add_execution_track(
    capa_id: UUID,
    data: ExecutionTrackSubmit,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """添加执行跟踪"""
    service = CapaService(db)
    capa = await service.add_execution_track(
        capa_id,
        execution_status=data.executionStatus,
        execution_date=data.execution_date,
        execution_notes=data.execution_notes,
    )
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found")
    await db.commit()
    
    return CapaApiResponse(data=CapaResponse(**capa))


@capa_router.delete("/{capa_id}/execution-tracks/{track_id}", summary="删除执行跟踪")
async def delete_execution_track(
    capa_id: UUID,
    track_id: str,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """删除执行跟踪"""
    service = CapaService(db)
    capa = await service.delete_execution_track(capa_id, track_id)
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found")
    await db.commit()
    
    return {"message": "Execution track deleted successfully"}


@capa_router.post("/{capa_id}/confirm-execution", response_model=CapaApiResponse, summary="确认执行")
async def confirm_execution(
    capa_id: UUID,
    data: ExecutionConfirm,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """确认执行"""
    service = CapaService(db)
    capa = await service.confirm_execution(
        capa_id,
        qa_confirmer=data.qaConfirmer,
        qa_confirm_date=data.qaConfirmDate,
    )
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found")
    await db.commit()
    
    return CapaApiResponse(data=CapaResponse(**capa))


@capa_router.post("/{capa_id}/evaluate", response_model=CapaApiResponse, summary="评估 CAPA")
async def evaluate_capa(
    capa_id: UUID,
    data: EvaluationSubmit,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """评估 CAPA"""
    service = CapaService(db)
    capa = await service.evaluate_capa(
        capa_id,
        evaluation_result=data.evaluation_result,
        evaluation_target=data.evaluation_target,
        evaluation_deadline=data.evaluation_deadline,
    )
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found")
    await db.commit()
    
    return CapaApiResponse(data=CapaResponse(**capa))


@capa_router.post("/{capa_id}/complete-part", response_model=CapaApiResponse, summary="完成部分")
async def complete_part(
    capa_id: UUID,
    data: PartComplete,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """完成部分"""
    service = CapaService(db)
    try:
        capa = await service.complete_part(capa_id, data.part)
        if not capa:
            raise HTTPException(status_code=404, detail="CAPA not found")
        await db.commit()
        return CapaApiResponse(data=CapaResponse(**capa))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@capa_router.post("/{capa_id}/confirm-dept-head", response_model=CapaApiResponse, summary="部门负责人确认")
async def confirm_dept_head(
    capa_id: UUID,
    data: DeptHeadConfirm,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """部门负责人确认"""
    service = CapaService(db)
    capa = await service.confirm_dept_head(
        capa_id,
        department=data.department,
        dept_head_user_id=data.deptHeadUserId,
        result=data.result,
        opinion=data.opinion,
    )
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found")
    await db.commit()
    
    return CapaApiResponse(data=CapaResponse(**capa))
