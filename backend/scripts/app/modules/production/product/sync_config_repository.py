"""Product sync config repository."""

import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.production.product.sync_config_models import ProductSyncConfig


class ProductSyncConfigRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_product_id(self, product_id: uuid.UUID) -> ProductSyncConfig | None:
        query = select(ProductSyncConfig).where(
            ProductSyncConfig.product_id == product_id,
            ProductSyncConfig.is_deleted == False,  # noqa: E712
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, data: dict[str, Any]) -> ProductSyncConfig:
        import json as _json

        if "field_mapping" in data and isinstance(data["field_mapping"], dict):
            data["field_mapping"] = _json.dumps(data["field_mapping"])
        record = ProductSyncConfig(**data)
        self.session.add(record)
        await self.session.flush()
        stmt = select(ProductSyncConfig).where(ProductSyncConfig.id == record.id)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def update(self, config_id: uuid.UUID, data: dict[str, Any]) -> ProductSyncConfig | None:
        import json as _json

        if "field_mapping" in data and isinstance(data["field_mapping"], dict):
            data["field_mapping"] = _json.dumps(data["field_mapping"])
        query = (
            update(ProductSyncConfig)
            .where(
                ProductSyncConfig.id == config_id,
                ProductSyncConfig.is_deleted == False,  # noqa: E712
            )
            .values(**data)
            .returning(ProductSyncConfig)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def delete(self, config_id: uuid.UUID) -> bool:
        query = (
            update(ProductSyncConfig)
            .where(
                ProductSyncConfig.id == config_id,
                ProductSyncConfig.is_deleted == False,  # noqa: E712
            )
            .values(is_deleted=True)
        )
        result = await self.session.execute(query)
        return result.rowcount > 0  # type: ignore[no-any-return,attr-defined]

    async def update_last_sync(self, config_id: uuid.UUID, last_sync_at: str) -> None:
        await self.session.execute(
            update(ProductSyncConfig).where(ProductSyncConfig.id == config_id).values(last_sync_at=last_sync_at)
        )
