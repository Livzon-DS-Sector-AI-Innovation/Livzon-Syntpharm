"""Quality module model tests."""

from __future__ import annotations

import pytest
from app.modules.quality.models.capa import CAPA
from app.modules.quality.models.deviations import Deviation
from sqlalchemy import select


@pytest.mark.asyncio
async def test_deviation_model_creation(db_session, sample_deviation_data):
    deviation = Deviation(**sample_deviation_data)
    db_session.add(deviation)
    await db_session.commit()

    result = await db_session.execute(
        select(Deviation).where(Deviation.id == deviation.id)
    )
    fetched = result.scalar_one()
    assert fetched.deviation_code == sample_deviation_data["deviation_code"]
    assert fetched.status == "draft"


@pytest.mark.asyncio
async def test_capa_model_creation(db_session, sample_capa_data):
    capa = CAPA(**sample_capa_data)
    db_session.add(capa)
    await db_session.commit()

    result = await db_session.execute(select(CAPA).where(CAPA.id == capa.id))
    fetched = result.scalar_one()
    assert fetched.capa_code == sample_capa_data["capa_code"]
    assert fetched.category == "corrective"
