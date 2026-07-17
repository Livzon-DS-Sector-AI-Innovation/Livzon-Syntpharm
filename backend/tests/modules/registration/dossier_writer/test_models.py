# mypy: ignore-errors
"""Dossier writer module model tests."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.modules.registration.dossier_writer.models import ProductDossier


@pytest.mark.asyncio
async def test_dossier_model_creation(db_session, sample_dossier_data):
    dossier = ProductDossier(**sample_dossier_data)
    db_session.add(dossier)
    await db_session.commit()

    result = await db_session.execute(select(ProductDossier).where(ProductDossier.id == dossier.id))
    fetched = result.scalar_one()
    assert fetched.product_name == "阿莫西林"
    assert fetched.sterile_type == "无菌"
