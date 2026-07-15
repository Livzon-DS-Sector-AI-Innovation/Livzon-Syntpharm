"""Dossier writer seed data — ensures S.6 AI configuration exists on startup."""

import logging

from sqlalchemy import select

from app.core.database import async_session_factory

logger = logging.getLogger(__name__)


async def run_seed() -> None:
    """Ensure S.6 chapter's FieldMapping + AssetCategory exist."""
    from app.modules.registration.dossier_writer.field_models import (
        AssetCategory,
        FieldMapping,
    )
    from app.modules.registration.dossier_writer.seed_data import (
        S6_ASSET_CATEGORIES,
        S6_FIELD_MAPPINGS,
    )

    async with async_session_factory() as session:
        result = await session.execute(
            select(FieldMapping).where(
                FieldMapping.chapter_code == "3.2.S.6",
                ~FieldMapping.is_deleted,
            )
        )
        if result.scalars().first() is not None:
            logger.info("S.6 field mappings already exist, skipping")
            return

        for cat_data in S6_ASSET_CATEGORIES:
            session.add(AssetCategory(**cat_data))

        for fm_data in S6_FIELD_MAPPINGS:
            session.add(FieldMapping(**fm_data))

        await session.commit()
        logger.info(
            "Seeded S.6: %d asset categories, %d field mappings",
            len(S6_ASSET_CATEGORIES),
            len(S6_FIELD_MAPPINGS),
        )
