"""Product API routes."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.core.response import ApiResponse
from app.modules.production.product.schemas import (
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)
from app.modules.production.product.service import ProductService

router = APIRouter()


@router.get("/products", summary="获取所有产品列表")
async def get(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:
    """获取所有产品，按车间分组"""
    service = ProductService(db)
    products = await service.get_all_products()
    return ApiResponse(data=[ProductResponse.model_validate(p) for p in products])


@router.get("/products/workshop/{workshop}", summary="获取指定车间的产品列表")  # type: ignore[no-redef]
async def get(  # noqa: F811
    workshop: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:
    """获取指定车间的所有产品"""
    service = ProductService(db)
    products = await service.get_products_by_workshop(workshop)
    return ApiResponse(data=[ProductResponse.model_validate(p) for p in products])


@router.get("/products/{product_id}", summary="获取产品详情")  # type: ignore[no-redef]
async def get(  # noqa: F811
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:
    """获取产品详情"""
    service = ProductService(db)
    product = await service.get_product(product_id)
    if not product:
        return ApiResponse(code=404, message="产品不存在")
    return ApiResponse(data=ProductResponse.model_validate(product))


@router.post("/products", summary="创建产品")
async def post(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:
    """创建新产品"""
    service = ProductService(db)
    product, error = await service.create_product(data)
    if error:
        return ApiResponse(code=400, message=error)
    return ApiResponse(data=ProductResponse.model_validate(product))


@router.put("/products/{product_id}", summary="更新产品")
async def put(
    product_id: uuid.UUID,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:
    """更新产品信息"""
    service = ProductService(db)
    product = await service.update_product(product_id, data)
    if not product:
        return ApiResponse(code=404, message="产品不存在")
    return ApiResponse(data=ProductResponse.model_validate(product))


@router.delete("/products/{product_id}", summary="删除产品")
async def delete(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:
    """删除产品"""
    service = ProductService(db)
    result = await service.delete_product(product_id)
    if not result:
        return ApiResponse(code=404, message="产品不存在")
    return ApiResponse(message="删除成功")
