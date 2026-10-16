# mypy: ignore-errors
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quality.sop_ai.repository import SopAiConfigRepository


async def test_upsert_and_get_config(db_session: AsyncSession):
    repo = SopAiConfigRepository(session=db_session)
    await repo.upsert("test_key", "test_value", "test description")
    config = await repo.get_by_key("test_key")
    assert config is not None
    assert config.config_value == "test_value"


async def test_get_nonexistent_config(db_session: AsyncSession):
    repo = SopAiConfigRepository(session=db_session)
    config = await repo.get_by_key("nonexistent_key")
    assert config is None


async def test_upsert_updates_existing(db_session: AsyncSession):
    repo = SopAiConfigRepository(session=db_session)
    await repo.upsert("test_update_key", "old_value", "desc")
    await repo.upsert("test_update_key", "new_value", "updated desc")
    config = await repo.get_by_key("test_update_key")
    assert config.config_value == "new_value"


async def test_get_all_configs(db_session: AsyncSession):
    repo = SopAiConfigRepository(session=db_session)
    await repo.upsert("key_a", "val_a", "desc_a")
    await repo.upsert("key_b", "val_b", "desc_b")
    configs = await repo.get_all()
    assert len(configs) >= 2
