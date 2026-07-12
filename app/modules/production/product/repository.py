"""Product repository for database operations."""

import uuid

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.production.product.models import Product
from app.modules.production.product.schemas import ProductCreate, ProductUpdate


class ProductRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: ProductCreate) -> Product:
        product = Product(**data.model_dump())
        self.db.add(product)
        await self.db.flush()
        await self.db.refresh(product)
        return product

    async def get_by_id(self, product_id: uuid.UUID) -> Product | None:
        result = await self.db.execute(select(Product).where(Product.id == product_id, ~Product.is_deleted))
        return result.scalar_one_or_none()

    async def get_by_workshop(self, workshop: str) -> list[Product]:
        result = await self.db.execute(
            select(Product).where(Product.workshop == workshop, ~Product.is_deleted).order_by(Product.name)
        )
        return list(result.scalars().all())

    async def get_all(self) -> list[Product]:
        result = await self.db.execute(
            select(Product).where(~Product.is_deleted).order_by(Product.workshop, Product.name)
        )
        return list(result.scalars().all())

    async def update(self, product_id: uuid.UUID, data: ProductUpdate) -> Product | None:
        product = await self.get_by_id(product_id)
        if not product:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(product, key, value)
        await self.db.flush()
        await self.db.refresh(product)
        return product

    async def delete(self, product_id: uuid.UUID) -> bool:
        product = await self.get_by_id(product_id)
        if not product:
            return False
        product.is_deleted = True
        await self.db.flush()
        return True

    async def exists(self, workshop: str, name: str) -> bool:
        result = await self.db.execute(
            select(Product).where(
                and_(
                    Product.workshop == workshop,
                    Product.name == name,
                    ~Product.is_deleted,
                )
            )
        )
        return result.scalar_one_or_none() is not None
