"""Product sync config API routes."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import RequiredUser
from app.core.response import ApiResponse
from app.modules.production.product.sync_config_schemas import (
    ProductSyncConfigCreate,
    ProductSyncConfigResponse,
    ProductSyncConfigUpdate,
)
from app.modules.production.product.sync_config_service import ProductSyncConfigService

router = APIRouter()


@router.get("/product-sync-config/{product_id}", summary="获取产品同步配置")
async def get_sync_config(
    product_id: uuid.UUID,
    current_user: RequiredUser = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = ProductSyncConfigService(db)
    config = await service.get_config(product_id)
    if not config:
        return ApiResponse(data=None, message="未找到同步配置")
    return ApiResponse(data=ProductSyncConfigResponse.model_validate(config))


@router.post("/product-sync-config", summary="创建产品同步配置")
async def create_sync_config(
    data: ProductSyncConfigCreate,
    current_user: RequiredUser = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = ProductSyncConfigService(db)
    existing = await service.get_config(data.product_id)
    if existing:
        return ApiResponse(code=400, message="该产品已有同步配置，请使用更新接口")
    config = await service.create_config(data)
    return ApiResponse(data=ProductSyncConfigResponse.model_validate(config))


@router.put("/product-sync-config/{config_id}", summary="更新产品同步配置")
async def update_sync_config(
    config_id: uuid.UUID,
    data: ProductSyncConfigUpdate,
    current_user: RequiredUser = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = ProductSyncConfigService(db)
    config = await service.update_config(config_id, data)
    if not config:
        return ApiResponse(code=404, message="配置不存在")
    return ApiResponse(data=ProductSyncConfigResponse.model_validate(config))


@router.delete("/product-sync-config/{config_id}", summary="删除产品同步配置")
async def delete_sync_config(
    config_id: uuid.UUID,
    current_user: RequiredUser = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = ProductSyncConfigService(db)
    success = await service.delete_config(config_id)
    if not success:
        return ApiResponse(code=404, message="配置不存在")
    return ApiResponse(message="删除成功")


@router.post("/product-sync-config/{product_id}/push", summary="推送到飞书")
async def push_to_feishu(
    product_id: uuid.UUID,
    current_user: RequiredUser = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = ProductSyncConfigService(db)
    result = await service.sync_push(product_id)
    return ApiResponse(data=result)


@router.post("/product-sync-config/{product_id}/pull", summary="从飞书拉取")
async def pull_from_feishu(
    product_id: uuid.UUID,
    current_user: RequiredUser = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = ProductSyncConfigService(db)
    result = await service.sync_pull(product_id)
    return ApiResponse(data=result)


@router.post("/product-sync-config/{product_id}/sync", summary="双向同步")
async def bidirectional_sync(
    product_id: uuid.UUID,
    current_user: RequiredUser = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = ProductSyncConfigService(db)
    result = await service.sync_bidirectional(product_id)
    return ApiResponse(data=result)
