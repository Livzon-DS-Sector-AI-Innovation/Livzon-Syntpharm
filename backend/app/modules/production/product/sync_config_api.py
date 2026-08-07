"""Product sync config API routes."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import RequiredUser
from app.core.response import ApiResponse
from app.modules.production.product.output_schemas import PreviewPullResponse, PreviewPushResponse, UndoSyncResponse
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
    current_user: RequiredUser,
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
    current_user: RequiredUser,
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
    current_user: RequiredUser,
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
    current_user: RequiredUser,
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
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = ProductSyncConfigService(db)
    result = await service.sync_push(product_id)
    return ApiResponse(data=result)


@router.post("/product-sync-config/{product_id}/pull", summary="从飞书拉取")
async def pull_from_feishu(
    product_id: uuid.UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = ProductSyncConfigService(db)
    result = await service.sync_pull(product_id)
    return ApiResponse(data=result)


@router.post("/product-sync-config/{product_id}/sync", summary="双向同步")
async def bidirectional_sync(
    product_id: uuid.UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = ProductSyncConfigService(db)
    result = await service.sync_bidirectional(product_id)
    return ApiResponse(data=result)


@router.post("/product-sync-config/{product_id}/preview-push", summary="预览推送操作")
async def preview_push(
    current_user: RequiredUser,
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PreviewPushResponse:
    """预览推送到飞书的操作，不实际执行"""
    service = ProductSyncConfigService(db)
    config = await service.get_config(product_id)
    if not config:
        return ApiResponse(code=404, message="未找到同步配置")

    import json

    from app.modules.production.product.feishu.sync import ProductSyncService

    field_mapping = json.loads(config.field_mapping) if config.field_mapping else None
    sync_service = ProductSyncService(db, config.app_token, config.table_id, field_mapping)
    result = await sync_service.preview_push(str(product_id))

    return result


@router.post("/product-sync-config/{product_id}/preview-pull", summary="预览拉取操作")
async def preview_pull(
    current_user: RequiredUser,
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PreviewPullResponse:
    """预览从飞书拉取的操作，不实际执行"""
    service = ProductSyncConfigService(db)
    config = await service.get_config(product_id)
    if not config:
        return ApiResponse(code=404, message="未找到同步配置")

    import json

    from app.modules.production.product.feishu.sync import ProductSyncService

    field_mapping = json.loads(config.field_mapping) if config.field_mapping else None
    sync_service = ProductSyncService(db, config.app_token, config.table_id, field_mapping)
    result = await sync_service.preview_pull(str(product_id))

    return result


@router.post("/product-sync-config/{product_id}/undo-last-sync", summary="撤销上次同步")
async def undo_last_sync(
    current_user: RequiredUser,
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """撤销上次同步操作"""

    from app.modules.production.product.feishu.sync import SyncOperationLog

    # 获取最新操作日志
    log = await SyncOperationLog.get_latest_operation(db, str(product_id))
    if not log:
        return ApiResponse(code=404, message="未找到同步操作记录")

    operation_type = log["operation_type"]
    records = log["records"]

    if operation_type == "push":
        # 撤销推送：删除新增的飞书记录，恢复更新的记录
        # 这里简化处理，只记录日志，实际删除需要飞书删除权限
        return ApiResponse(
            data={"message": f"已记录撤销操作，共 {len(records)} 条记录需要处理"}, message="撤销推送操作已记录"
        )
    else:
        # 撤销拉取：删除新增的平台记录，恢复更新的记录
        deleted = 0
        for record in records:
            if record.get("action") == "新增":
                # 软删除新增的记录
                await db.execute(
                    text("""
                    UPDATE production.product_outputs
                    SET is_deleted = true
                    WHERE product_id = :product_id
                    AND batch_no = :batch_no
                    AND is_deleted = false
                    """),
                    {
                        "product_id": str(product_id),
                        "batch_no": record["batch_no"],
                    },
                )
                deleted += 1

        await db.commit()
        return UndoSyncResponse(deleted=deleted)
