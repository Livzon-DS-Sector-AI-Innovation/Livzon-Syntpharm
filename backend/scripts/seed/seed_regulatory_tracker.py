"""Seed script for regulatory tracker initial data."""

import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app.core.database import async_session_factory
from app.modules.regulatory_tracker.models import DataChannel, DataSource

# Import identity models first to resolve FK references
from app.platform.identity.models import User  # noqa: F401


async def seed_regulatory_tracker():
    """Seed initial data for regulatory tracker."""

    async with async_session_factory() as session:
        # Check if already seeded (check NMPA too)
        result_cde = await session.execute(select(DataSource).where(DataSource.code == "CDE"))
        result_nmpa = await session.execute(select(DataSource).where(DataSource.code == "NMPA"))
        has_cde = result_cde.scalar_one_or_none()
        has_nmpa = result_nmpa.scalar_one_or_none()

        if has_cde and has_nmpa:
            print("⚠️  CDE and NMPA data sources already exist, skipping seed")
            return

        created = []

        # ── CDE ──
        if not has_cde:
            cde_source = DataSource(
                id=uuid.uuid4(),
                code="CDE",
                name="国家药品监督管理局药品审评中心",
                base_url="https://www.cde.org.cn",
                enabled=True,
            )
            session.add(cde_source)
            await session.flush()
            print(f"✅ Created data source: CDE (id={cde_source.id})")

            cde_guideline_channel = DataChannel(
                id=uuid.uuid4(),
                source_id=cde_source.id,
                code="cde_domestic_guideline",
                name="国内药品技术指导原则",
                list_url="https://www.cde.org.cn/zdyz/listpage/9cd8db3b7530c6fa0c86485e563f93c7",
                adapter_name="CdeDomesticGuidelineAdapter",
                enabled=True,
            )
            session.add(cde_guideline_channel)
            print(f"✅ Created data channel: cde_domestic_guideline (id={cde_guideline_channel.id})")
            created.append(f"CDE source={cde_source.id} channel={cde_guideline_channel.id}")

        # ── NMPA ──
        if not has_nmpa:
            nmpa_source = DataSource(
                id=uuid.uuid4(),
                code="NMPA",
                name="国家药品监督管理局",
                base_url="https://www.nmpa.gov.cn",
                enabled=True,
            )
            session.add(nmpa_source)
            await session.flush()
            print(f"✅ Created data source: NMPA (id={nmpa_source.id})")

            nmpa_baxx_channel = DataChannel(
                id=uuid.uuid4(),
                source_id=nmpa_source.id,
                code="nmpa_baxx",
                name="备案信息",
                list_url="https://www.nmpa.gov.cn/datasearch/search-result.html",
                adapter_name="NmpaRecordAdapter",
                enabled=True,
            )
            session.add(nmpa_baxx_channel)
            print(f"✅ Created data channel: nmpa_baxx (id={nmpa_baxx_channel.id})")
            created.append(f"NMPA source={nmpa_source.id} channel={nmpa_baxx_channel.id}")

        await session.commit()
        print("\n✅ Seed completed successfully")
        for c in created:
            print(f"   {c}")


if __name__ == "__main__":
    asyncio.run(seed_regulatory_tracker())
