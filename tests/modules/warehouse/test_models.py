"""Warehouse module model tests."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.modules.warehouse.models import RawMaterialInventory


@pytest.mark.asyncio
async def test_inventory_model_creation(db_session, sample_inventory_data):
    inventory = RawMaterialInventory(**sample_inventory_data)
    db_session.add(inventory)
    await db_session.commit()

    result = await db_session.execute(
        select(RawMaterialInventory).where(RawMaterialInventory.id == inventory.id)
    )
    fetched = result.scalar_one()
    assert fetched.code == sample_inventory_data["code"]
    assert fetched.available == 100.0
