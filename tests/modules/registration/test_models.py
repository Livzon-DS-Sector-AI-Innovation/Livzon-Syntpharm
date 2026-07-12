# mypy: ignore-errors
"""Registration module model tests."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select

from app.modules.registration.models.drug import Drug


@pytest.mark.asyncio
async def test_drug_model_creation(db_session, sample_drug_data):
    drug = Drug(**sample_drug_data)
    db_session.add(drug)
    await db_session.commit()

    result = await db_session.execute(select(Drug).where(Drug.id == drug.id))
    fetched = result.scalar_one()
    assert fetched.name == "阿莫西林"
    assert fetched.type == "仿制药"
    assert fetched.acceptance_date == date(2026, 1, 15)
