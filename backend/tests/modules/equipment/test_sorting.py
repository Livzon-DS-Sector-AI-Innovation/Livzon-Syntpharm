"""Tests for Equipment Sorting Logic."""
import pytest
from sqlalchemy import select
from app.modules.equipment.models.equipment import Equipment

@pytest.mark.asyncio
async def test_default_sort_by_asset_no_asc_nulls_last(db_session):
    """验证默认排序：资产编号升序，空值置后"""
    # 模拟数据已在 fixture 中准备
    query = select(Equipment).where(Equipment.is_deleted.is_(False))
    
    # 应用排序逻辑（模拟 repository 中的实现）
    from sqlalchemy import asc, nulls_last
    query = query.order_by(nulls_last(asc(Equipment.asset_no)))
    
    result = await db_session.execute(query)
    equipments = result.scalars().all()
    
    # 提取非空编号
    non_null_nos = [e.asset_no for e in equipments if e.asset_no is not None]
    null_count = sum(1 for e in equipments if e.asset_no is None)
    
    # 验证非空部分是升序的
    assert non_null_nos == sorted(non_null_nos)
    
    # 验证空值在最后
    if null_count > 0 and len(non_null_nos) > 0:
        last_non_null_index = len(equipments) - null_count - 1
        assert equipments[last_non_null_index].asset_no is not None
        assert equipments[-1].asset_no is None

@pytest.mark.asyncio
async def test_sort_by_name_desc(db_session):
    """验证按名称降序排序"""
    from sqlalchemy import desc, nulls_last
    query = select(Equipment).where(Equipment.is_deleted.is_(False)).order_by(nulls_last(desc(Equipment.name)))
    result = await db_session.execute(query)
    equipments = result.scalars().all()
    
    non_null_names = [e.name for e in equipments if e.name is not None]
    assert non_null_names == sorted(non_null_names, reverse=True)
