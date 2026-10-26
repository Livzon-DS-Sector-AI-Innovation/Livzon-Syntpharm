"""Registration project API endpoints."""

import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, PermissionContext, require_permission
from app.core.exceptions import AppException
from app.core.response import success_response
from app.modules.registration.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)
from app.modules.registration.service import project as project_service

router = APIRouter()


@router.get("/", summary="获取注册项目列表")
async def list_projects(
    current_user: CurrentUser,
    ctx: PermissionContext = Depends(require_permission("registration:project:read")),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    projects = await project_service.get_projects(db)
    data = [ProjectResponse.model_validate(p) for p in projects]
    return success_response(data=data)


@router.post("/", summary="创建注册项目")
async def create_project(
    current_user: CurrentUser,
    data: ProjectCreate,
    ctx: PermissionContext = Depends(require_permission("registration:project:create")),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    project = await project_service.create_project(db, data)
    return success_response(data=ProjectResponse.model_validate(project))


@router.get("/{project_id}", summary="获取注册项目详情")
async def get_project(
    current_user: CurrentUser,
    project_id: uuid.UUID,
    ctx: PermissionContext = Depends(require_permission("registration:project:read")),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    try:
        project = await project_service.get_project(db, project_id)
    except ValueError as exc:
        raise AppException(status_code=404, message=str(exc)) from exc
    return success_response(data=ProjectResponse.model_validate(project))


@router.put("/{project_id}", summary="更新注册项目")
async def update_project(
    current_user: CurrentUser,
    project_id: uuid.UUID,
    data: ProjectUpdate,
    ctx: PermissionContext = Depends(require_permission("registration:project:update")),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    try:
        project = await project_service.update_project(db, project_id, data)
    except ValueError as exc:
        raise AppException(status_code=404, message=str(exc)) from exc
    return success_response(data=ProjectResponse.model_validate(project))


@router.delete("/{project_id}", summary="删除注册项目")
async def delete_project(
    current_user: CurrentUser,
    project_id: uuid.UUID,
    ctx: PermissionContext = Depends(require_permission("registration:project:delete")),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    try:
        await project_service.delete_project(db, project_id)
    except ValueError as exc:
        raise AppException(status_code=404, message=str(exc)) from exc
    return success_response(message="删除成功")
