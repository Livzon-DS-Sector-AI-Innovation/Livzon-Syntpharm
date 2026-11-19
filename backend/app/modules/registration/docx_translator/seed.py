"""DOCX 翻译 —— 内置术语表种子。

表为空时把 `assets/glossary_cleaned.xlsx` 导入；非空则跳过（幂等），
避免覆盖用户后续维护的术语。
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.core.database import async_session_factory

from .glossary import parse_excel_file
from .models import SOURCE_BUILTIN, DocxTranslationTerm
from .repository import DocxTranslationTermRepository

logger = logging.getLogger(__name__)

_ASSET = Path(__file__).parent / "assets" / "glossary_cleaned.xlsx"


async def run_seed() -> None:
    if not _ASSET.exists():
        logger.warning("docx_translator glossary asset missing: %s", _ASSET.name)
        return

    async with async_session_factory() as session:
        repo = DocxTranslationTermRepository(session)
        if await repo.count() > 0:
            return

        try:
            rows = parse_excel_file(_ASSET)
        except Exception:
            logger.exception("docx_translator builtin glossary parse failed")
            return

        seen: set[str] = set()
        added = 0
        for en, zh in rows:
            key = en.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            session.add(
                DocxTranslationTerm(
                    term_en=en.strip(),
                    term_en_lower=key,
                    term_zh=zh.strip(),
                    is_enabled=True,
                    source=SOURCE_BUILTIN,
                )
            )
            added += 1
        await session.commit()
        logger.info("docx_translator seeded %d builtin glossary terms", added)
