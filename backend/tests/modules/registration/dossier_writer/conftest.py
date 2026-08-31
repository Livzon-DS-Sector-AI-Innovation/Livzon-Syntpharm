# mypy: ignore-errors
"""Dossier writer module test fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_dossier_data():
    return {
        "product_name": "阿莫西林",
        "sterile_type": "无菌",
        "manufacturer": "某制药有限公司",
    }


@pytest.fixture
async def sample_chapter(db_session, sample_dossier_data):
    """Create a sample chapter for testing."""
    from app.modules.registration.dossier_writer.models import ProductDossier, DossierChapter
    from uuid import uuid4
    
    # Create dossier first
    dossier = ProductDossier(**sample_dossier_data)
    db_session.add(dossier)
    await db_session.flush()
    
    # Create chapter
    chapter = DossierChapter(
        product_dossier_id=dossier.id,
        chapter_title="Test Chapter",
        level=1,
        sort_order=1,
    )
    db_session.add(chapter)
    await db_session.flush()
    
    return chapter


@pytest.fixture
async def sample_asset(db_session, sample_chapter):
    """Create a sample asset for testing."""
    from app.modules.registration.dossier_writer.models import ChapterAsset
    from pathlib import Path
    
    asset = ChapterAsset(
        chapter_id=sample_chapter.id,
        original_filename="test_document.pdf",
        file_path="/tmp/test_document.pdf",
        file_type="pdf",
        file_size=1024,
    )
    db_session.add(asset)
    await db_session.flush()
    
    return asset
