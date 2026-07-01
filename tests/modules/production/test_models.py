"""Production module model tests."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.modules.production.models import Batch, ProductionPlan


@pytest.mark.asyncio
async def test_batch_model_creation(db_session, sample_batch_data):
    batch = Batch(**sample_batch_data)
    db_session.add(batch)
    await db_session.commit()

    result = await db_session.execute(select(Batch).where(Batch.id == batch.id))
    fetched = result.scalar_one()
    assert fetched.batch_no == sample_batch_data["batch_no"]
    assert fetched.status == "draft"


@pytest.mark.asyncio
async def test_production_plan_model_creation(db_session, sample_production_plan_data):
    plan = ProductionPlan(**sample_production_plan_data)
    db_session.add(plan)
    await db_session.commit()

    result = await db_session.execute(
        select(ProductionPlan).where(ProductionPlan.id == plan.id)
    )
    fetched = result.scalar_one()
    assert fetched.plan_no == sample_production_plan_data["plan_no"]
    assert fetched.total_batches == 10
