"""Registration project API endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.exceptions import AppException
from app.core.response import DataResponse
from app.modules.registration.schemas.project import (
    ProgressLogCreate,
    ProgressLogResponse,
    ProjectCreate,
    ProjectKpiResponse,
    ProjectResponse,
    ProjectUpdate,
    StageAdvanceRequest,
)
from app.modules.registration.service import project as project_service

router = APIRouter()


@router.get("/", summary="获取注册项目列表")
async def list_projects(
    current_user: RequiredUser,
    search: str | None = Query(None, description="搜索项目名称/编号/品种"),
    registration_type: str | None = Query(None, description="注册类型筛选"),
    status: str | None = Query(None, description="状态筛选"),
    drug_id: uuid.UUID | None = Query(None, description="按关联审评品种反查"),
    ctx: PermissionContext = Depends(require_permission("registration:project:read")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[list[ProjectResponse]]:
    projects = await project_service.get_projects(
        db, search=search, registration_type=registration_type, status=status, drug_id=drug_id
    )
    return DataResponse[list[ProjectResponse]](data=[ProjectResponse.model_validate(p) for p in projects])


@router.get("/kpi", summary="注册项目 KPI 统计")
async def get_project_kpi(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("registration:project:read")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ProjectKpiResponse]:
    kpi = await project_service.get_kpi(db)
    return DataResponse[ProjectKpiResponse](data=ProjectKpiResponse.model_validate(kpi))


@router.post("/", summary="创建注册项目")
async def create_project(
    current_user: RequiredUser,
    data: ProjectCreate,
    ctx: PermissionContext = Depends(require_permission("registration:project:create")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ProjectResponse]:
    try:
        project = await project_service.create_project(db, data, created_by=current_user.id)
    except ValueError as exc:
        raise AppException(status_code=400, message=str(exc)) from exc
    return DataResponse[ProjectResponse](data=ProjectResponse.model_validate(project))


@router.get("/{project_id}", summary="获取注册项目详情")
async def get_project(
    current_user: RequiredUser,
    project_id: uuid.UUID,
    ctx: PermissionContext = Depends(require_permission("registration:project:read")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ProjectResponse]:
    try:
        detail = await project_service.get_project_detail(db, project_id)
    except ValueError as exc:
        raise AppException(status_code=404, message=str(exc)) from exc
    return DataResponse[ProjectResponse](data=ProjectResponse.model_validate(detail))


@router.put("/{project_id}", summary="更新注册项目基本信息")
async def update_project(
    current_user: RequiredUser,
    project_id: uuid.UUID,
    data: ProjectUpdate,
    ctx: PermissionContext = Depends(require_permission("registration:project:update")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ProjectResponse]:
    try:
        project = await project_service.update_project(db, project_id, data)
    except ValueError as exc:
        raise AppException(status_code=404, message=str(exc)) from exc
    return DataResponse[ProjectResponse](data=ProjectResponse.model_validate(project))


@router.post("/{project_id}/stage", summary="推进申报前阶段")
async def advance_stage(
    current_user: RequiredUser,
    project_id: uuid.UUID,
    data: StageAdvanceRequest,
    ctx: PermissionContext = Depends(require_permission("registration:project:update")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ProjectResponse]:
    """推进/回退申报前阶段（受理为界）：触发状态流转并自动写入 system 进展记录。"""
    try:
        project = await project_service.advance_stage(db, project_id, data.stage)
    except ValueError as exc:
        raise AppException(status_code=400, message=str(exc)) from exc
    return DataResponse[ProjectResponse](data=ProjectResponse.model_validate(project))


@router.get("/{project_id}/logs", summary="获取项目进展记录")
async def list_project_logs(
    current_user: RequiredUser,
    project_id: uuid.UUID,
    ctx: PermissionContext = Depends(require_permission("registration:project:read")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[list[ProgressLogResponse]]:
    """进展记录时间线（新→旧倒序）。审计追踪：只增不删，无更新/删除接口。"""
    try:
        logs = await project_service.get_project_logs(db, project_id)
    except ValueError as exc:
        raise AppException(status_code=404, message=str(exc)) from exc
    return DataResponse[list[ProgressLogResponse]](data=[ProgressLogResponse.model_validate(log) for log in logs])


@router.post("/{project_id}/logs", summary="添加项目进展记录")
async def add_project_log(
    current_user: RequiredUser,
    project_id: uuid.UUID,
    data: ProgressLogCreate,
    ctx: PermissionContext = Depends(require_permission("registration:project:update")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ProgressLogResponse]:
    try:
        log = await project_service.add_progress_log(db, project_id, data.content, created_by=current_user.id)
    except ValueError as exc:
        raise AppException(status_code=404, message=str(exc)) from exc
    return DataResponse[ProgressLogResponse](data=ProgressLogResponse.model_validate(log))


@router.delete("/{project_id}", summary="删除注册项目")
async def delete_project(
    current_user: RequiredUser,
    project_id: uuid.UUID,
    ctx: PermissionContext = Depends(require_permission("registration:project:delete")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[None]:
    try:
        await project_service.delete_project(db, project_id)
    except ValueError as exc:
        raise AppException(status_code=404, message=str(exc)) from exc
    return DataResponse[None](message="删除成功")
