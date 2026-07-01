"""Research module model tests."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.modules.research.models import ResearchProject


@pytest.mark.asyncio
async def test_project_model_creation(db_session, sample_project_data):
    project = ResearchProject(**sample_project_data)
    db_session.add(project)
    await db_session.commit()

    result = await db_session.execute(
        select(ResearchProject).where(ResearchProject.id == project.id)
    )
    fetched = result.scalar_one()
    assert fetched.project_no == "PROJ-2026-001"
    assert fetched.status == "进行中"
