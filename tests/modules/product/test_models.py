"""Product module model tests."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.modules.product.models import Product


@pytest.mark.asyncio
async def test_product_model_creation(db_session, sample_product_data):
    product = Product(**sample_product_data)
    db_session.add(product)
    await db_session.commit()

    result = await db_session.execute(select(Product).where(Product.id == product.id))
    fetched = result.scalar_one()
    assert fetched.name == "阿莫西林胶囊"
    assert fetched.major_category == "SM"
