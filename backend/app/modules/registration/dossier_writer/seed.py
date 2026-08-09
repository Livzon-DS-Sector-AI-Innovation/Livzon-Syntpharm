"""Dossier writer seed data — ensures S.6 AI configuration exists on startup."""

import logging

from app.core.database import async_session_factory

logger = logging.getLogger(__name__)


async def run_seed() -> None:
    """Ensure S.6 chapter's FieldMapping + AssetCategory exist."""
    from app.modules.registration.dossier_writer.service import DossierService

    async with async_session_factory() as session:
        service = DossierService(session)
        result = await service.init_chapter_ai_config("3.2.S.6")
        logger.info("S.6 seed: %s", result.get("message", "done"))
