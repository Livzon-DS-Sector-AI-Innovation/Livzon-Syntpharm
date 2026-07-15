"""Product sync config service."""

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.production.product.feishu.sync import ProductSyncService
from app.modules.production.product.sync_config_models import ProductSyncConfig
from app.modules.production.product.sync_config_repository import ProductSyncConfigRepository
from app.modules.production.product.sync_config_schemas import (
    ProductSyncConfigCreate,
    ProductSyncConfigUpdate,
    SyncResult,
)


class ProductSyncConfigService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ProductSyncConfigRepository(session)

    async def get_config(self, product_id: uuid.UUID) -> ProductSyncConfig | None:
        return await self.repo.get_by_product_id(product_id)

    async def create_config(self, data: ProductSyncConfigCreate) -> ProductSyncConfig:
        return await self.repo.create(data.model_dump())

    async def update_config(self, config_id: uuid.UUID, data: ProductSyncConfigUpdate) -> ProductSyncConfig | None:
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return await self.repo.get_by_product_id(
                (
                    await self.session.execute(
                        __import__("sqlalchemy").select(ProductSyncConfig.id).where(ProductSyncConfig.id == config_id)
                    )
                ).scalar_one()
            )
        return await self.repo.update(config_id, update_data)

    async def delete_config(self, config_id: uuid.UUID) -> bool:
        return await self.repo.delete(config_id)

    async def sync_push(self, product_id: uuid.UUID) -> SyncResult:
        config = await self.repo.get_by_product_id(product_id)
        if not config:
            return SyncResult(errors=["未找到同步配置"], message="请先配置同步")

        field_mapping = json.loads(config.field_mapping) if config.field_mapping else None
        service = ProductSyncService(self.session, config.app_token, config.table_id, field_mapping)
        result = await service.push_to_feishu(str(product_id))

        await self.repo.update_last_sync(
            config.id,
            datetime.now(UTC).isoformat(),
        )
        await self.session.commit()

        return SyncResult(**result)

    async def sync_pull(self, product_id: uuid.UUID) -> SyncResult:
        config = await self.repo.get_by_product_id(product_id)
        if not config:
            return SyncResult(errors=["未找到同步配置"], message="请先配置同步")

        field_mapping = json.loads(config.field_mapping) if config.field_mapping else None
        service = ProductSyncService(self.session, config.app_token, config.table_id, field_mapping)
        result = await service.pull_from_feishu(str(product_id))

        await self.repo.update_last_sync(
            config.id,
            datetime.now(UTC).isoformat(),
        )
        await self.session.commit()

        return SyncResult(**result)

    async def sync_bidirectional(self, product_id: uuid.UUID) -> dict[str, Any]:
        config = await self.repo.get_by_product_id(product_id)
        if not config:
            return {"error": "未找到同步配置"}

        field_mapping = json.loads(config.field_mapping) if config.field_mapping else None
        service = ProductSyncService(self.session, config.app_token, config.table_id, field_mapping)
        result = await service.bidirectional_sync(str(product_id))

        await self.repo.update_last_sync(
            config.id,
            datetime.now(UTC).isoformat(),
        )
        await self.session.commit()

        return result
