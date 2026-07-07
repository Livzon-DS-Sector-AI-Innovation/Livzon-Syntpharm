"""Product service for business logic."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.production.product.repository import ProductRepository
from app.modules.production.product.schemas import ProductCreate, ProductUpdate


class ProductService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ProductRepository(db)

    async def create_product(self, data: ProductCreate):
        # 检查是否已存在
        if await self.repo.exists(data.workshop, data.name):
            return None, "该产品已存在"
        product = await self.repo.create(data)
        await self.db.commit()
        return product, None

    async def get_product(self, product_id: uuid.UUID):
        return await self.repo.get_by_id(product_id)

    async def get_products_by_workshop(self, workshop: str):
        return await self.repo.get_by_workshop(workshop)

    async def get_all_products(self):
        return await self.repo.get_all()

    async def update_product(self, product_id: uuid.UUID, data: ProductUpdate):
        product = await self.repo.update(product_id, data)
        if product:
            await self.db.commit()
        return product

    async def delete_product(self, product_id: uuid.UUID) -> bool:
        result = await self.repo.delete(product_id)
        if result:
            await self.db.commit()
        return result
