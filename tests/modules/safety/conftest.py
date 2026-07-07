"""Safety module test fixtures."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture
def sample_hazard_data():
    return {
        "hazard_no": "HAZ-2026-001",
        "title": "化学品泄漏风险",
        "description": "存储区域存在泄漏风险",
        "risk_level": 2,
        "location": "化学品仓库A",
        "status": "open",
    }


# Use an in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with engine.begin() as conn:
        from app.shared.base_model import BaseModel

        await conn.run_sync(BaseModel.metadata.create_all)
    async with async_session() as session:
        yield session
    await engine.dispose()
