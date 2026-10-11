"""设备模块通用验证工具。

提供可复用的验证函数，减少 service 层的重复代码。
"""

import uuid
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateException, NotFoundException
from app.modules.equipment import repository as repo

T = TypeVar("T")


async def validate_category_exists(db: AsyncSession, category_id: uuid.UUID) -> None:
    """验证设备分类是否存在，不存在则抛出异常。"""
    category = await repo.get_equipment_category_by_id(db, category_id)
    if not category:
        raise NotFoundException("设备分类", str(category_id))


async def validate_location_exists(db: AsyncSession, location_id: uuid.UUID) -> None:
    """验证位置是否存在，不存在则抛出异常。"""
    location = await repo.get_location_by_id(db, location_id)
    if not location:
        raise NotFoundException("位置", str(location_id))


async def validate_equipment_exists(db: AsyncSession, equipment_id: uuid.UUID) -> None:
    """验证设备是否存在，不存在则抛出异常。"""
    equipment = await repo.get_equipment_by_id(db, equipment_id)
    if not equipment:
        raise NotFoundException("设备", str(equipment_id))


async def validate_unique_category_code(db: AsyncSession, code: str, exclude_id: uuid.UUID | None = None) -> None:
    """验证分类代码唯一性。"""
    if await repo.exists_category_by_code(db, code, exclude_id=exclude_id):
        raise DuplicateException("分类代码", code)


async def validate_unique_location_code(db: AsyncSession, code: str, exclude_id: uuid.UUID | None = None) -> None:
    """验证位置代码唯一性。"""
    if await repo.exists_location_by_code(db, code, exclude_id=exclude_id):
        raise DuplicateException("位置代码", code)


async def validate_categories_exist(db: AsyncSession, category_ids: list[uuid.UUID]) -> None:
    """批量验证多个分类是否存在。"""
    for cid in category_ids:
        await validate_category_exists(db, cid)


async def validate_asset_no_unique(db: AsyncSession, asset_no: str) -> None:
    """验证资产编号唯一性。"""
    existing = await repo.get_equipment_by_asset_no(db, asset_no)
    if existing:
        raise DuplicateException("资产编号", asset_no)
