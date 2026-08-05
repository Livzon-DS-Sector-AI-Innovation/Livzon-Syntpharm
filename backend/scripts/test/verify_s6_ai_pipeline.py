"""Verify S6 AI Pipeline Regression."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.core.database import AsyncSessionLocal
from app.modules.registration.dossier_writer.models import ProductDossier, DossierChapter
from app.modules.registration.dossier_writer.field_models import FieldMapping
from sqlalchemy import select, and_

async def main():
    print("🔍 Starting S6 AI Pipeline Verification...")
    
    async with AsyncSessionLocal() as db:
        # 1. Find a dossier with S6 content
        stmt = select(ProductDossier).limit(1)
        result = await db.execute(stmt)
        dossier = result.scalar_one_or_none()
        
        if not dossier:
            print("❌ No dossier found for testing.")
            return

        # 2. Check S6 Chapter
        s6_stmt = select(DossierChapter).where(
            and_(
                DossierChapter.product_dossier_id == dossier.id,
                DossierChapter.chapter_code == "3.2.S.6"
            )
        )
        s6_result = await db.execute(s6_stmt)
        s6_chapter = s6_result.scalar_one_or_none()

        if not s6_chapter:
            print("❌ S6 chapter not found.")
            return

        print(f"✅ Found S6 Chapter: {s6_chapter.chapter_title}")

        # 3. Check FieldMappings
        fm_stmt = select(FieldMapping).where(
            and_(
                FieldMapping.chapter_code == "3.2.S.6",
                ~FieldMapping.is_deleted
            )
        )
        fm_result = await db.execute(fm_stmt)
        mappings = fm_result.scalars().all()

        print(f"✅ Found {len(mappings)} field mappings for S6.")

        # 4. Verify location_hints are not index-based (if pre-scan was done)
        index_based = [m for m in mappings if m.location_hint and m.location_hint.startswith("第")]
        if index_based:
            print(f"⚠️  Warning: {len(index_based)} mappings still use index-based hints.")
        else:
            print("✅ All location hints are text-based or safe.")

        print("🎉 S6 AI Pipeline Verification Completed.")

if __name__ == "__main__":
    asyncio.run(main())
