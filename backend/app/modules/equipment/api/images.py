"""工单图片 API 路由."""

import os
import uuid
from io import BytesIO
from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.exceptions import NotFoundException
from app.core.response import build_response
from app.modules.equipment import repository as repo
from app.modules.equipment import service
from app.modules.equipment.schemas import (
    WorkOrderImageDeleteApiResponse,
    WorkOrderImageListApiResponse,
    WorkOrderImageResponse,
)

router = APIRouter()


@router.post(
    "/{work_order_id}/images",
    response_model=WorkOrderImageListApiResponse,
    summary="上传工单图片",
)
async def upload_work_order_images(
    work_order_id: uuid.UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("equipment:work-order:create")),
    files: list[UploadFile] = File(..., description="图片文件"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    images = await service.upload_images(db, work_order_id, files)
    return build_response(data=[WorkOrderImageResponse.model_validate(img) for img in images])


@router.get(
    "/{work_order_id}/images",
    response_model=WorkOrderImageListApiResponse,
    summary="获取工单图片列表",
)
async def list_work_order_images(
    work_order_id: uuid.UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("equipment:work-order:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    images = await service.get_work_order_images(db, work_order_id)
    return build_response(data=[WorkOrderImageResponse.model_validate(img) for img in images])


@router.get("/{work_order_id}/images/{image_id}/file", summary="查看工单图片文件")
async def serve_work_order_image(
    work_order_id: uuid.UUID,
    image_id: uuid.UUID,
    ctx: PermissionContext = Depends(require_permission("equipment:work-order:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    from app.core.storage import get_object
    from app.core.storage import is_enabled as minio_enabled

    image = await repo.get_image_by_id(db, image_id)
    if not image or str(image.work_order_id) != str(work_order_id):
        raise NotFoundException("图片", str(image_id))

    if minio_enabled():
        result = get_object("equipment", image.file_path)
        if result is None:
            raise NotFoundException("图片文件")
        data, content_type = result
        return StreamingResponse(BytesIO(data), media_type=content_type)

    if not os.path.exists(image.file_path):
        raise NotFoundException("图片文件")
    return FileResponse(image.file_path)


@router.delete(
    "/{work_order_id}/images/{image_id}",
    response_model=WorkOrderImageDeleteApiResponse,
    summary="删除工单图片",
)
async def remove_work_order_image(
    work_order_id: uuid.UUID,
    image_id: uuid.UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("equipment:work-order:delete")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    await service.delete_work_order_image(db, image_id)
    return build_response(message="图片已删除")
