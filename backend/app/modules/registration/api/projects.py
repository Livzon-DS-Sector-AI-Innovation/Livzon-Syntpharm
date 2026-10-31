"""Registration project API endpoints."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.exceptions import AppException
from app.core.response import DataResponse
from app.modules.registration.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)
from app.modules.registration.service import project as project_service

router = APIRouter()


@router.get("/", summary="获取注册项目列表")
async def list_projects(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("registration:project:read")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[list[ProjectResponse]]:
    projects = await project_service.get_projects(db)
    data = [ProjectResponse.model_validate(p) for p in projects]
    return DataResponse[list[ProjectResponse]](data=data)


@router.post("/", summary="创建注册项目")
async def create_project(
    current_user: RequiredUser,
    data: ProjectCreate,
    ctx: PermissionContext = Depends(require_permission("registration:project:create")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ProjectResponse]:
    project = await project_service.create_project(db, data)
    return DataResponse[ProjectResponse](data=ProjectResponse.model_validate(project))


@router.get("/{project_id}", summary="获取注册项目详情")
async def get_project(
    current_user: RequiredUser,
    project_id: uuid.UUID,
    ctx: PermissionContext = Depends(require_permission("registration:project:read")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ProjectResponse]:
    try:
        project = await project_service.get_project(db, project_id)
    except ValueError as exc:
        raise AppException(status_code=404, message=str(exc)) from exc
    return DataResponse[ProjectResponse](data=ProjectResponse.model_validate(project))


@router.put("/{project_id}", summary="更新注册项目")
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
