"""Regulatory tracker seed data — ensures CDE/NMPA data sources and initial documents exist."""

import json
import logging
import os
import uuid

from sqlalchemy import select

from app.core.database import async_session_factory

logger = logging.getLogger(__name__)


async def _seed_regulatory_tracker() -> None:
    """确保 CDE / NMPA 数据源和频道存在。"""
    from app.modules.registration.regulatory_tracker.models import DataChannel, DataSource

    async with async_session_factory() as session:
        result = await session.execute(select(DataSource).where(DataSource.code == "CDE"))
        if result.scalar_one_or_none() is None:
            cde_source = DataSource(
                id=uuid.uuid4(),
                code="CDE",
                name="国家药品监督管理局药品审评中心",
                base_url="https://www.cde.org.cn",
                enabled=True,
            )
            session.add(cde_source)
            await session.flush()
            session.add(
                DataChannel(
                    id=uuid.uuid4(),
                    source_id=cde_source.id,
                    code="cde_domestic_guideline",
                    name="国内药品技术指导原则",
                    list_url="https://www.cde.org.cn/zdyz/listpage/9cd8db3b7530c6fa0c86485e563f93c7",
                    adapter_name="CdeDomesticGuidelineAdapter",
                    enabled=True,
                )
            )
            logger.info("Created CDE data source and channel")
        else:
            logger.info("CDE data source already exists, skipping")

        result = await session.execute(select(DataSource).where(DataSource.code == "NMPA"))
        if result.scalar_one_or_none() is None:
            nmpa_source = DataSource(
                id=uuid.uuid4(),
                code="NMPA",
                name="国家药品监督管理局",
                base_url="https://www.nmpa.gov.cn",
                enabled=True,
            )
            session.add(nmpa_source)
            await session.flush()
            session.add(
                DataChannel(
                    id=uuid.uuid4(),
                    source_id=nmpa_source.id,
                    code="nmpa_baxx",
                    name="备案信息",
                    list_url="https://www.nmpa.gov.cn/datasearch/search-result.html",
                    adapter_name="NmpaRecordAdapter",
                    enabled=True,
                )
            )
            logger.info("Created NMPA data source and channel")
        else:
            logger.info("NMPA data source already exists, skipping")

        await session.commit()


async def _seed_regulatory_documents() -> None:
    """从 seed/cde_guidelines.json 导入初始法规文档（文件不存在则跳过）。"""
    from app.modules.registration.regulatory_tracker.models import (
        DataChannel,
        DataSource,
        RegulatoryDocument,
    )

    json_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "seed",
        "cde_guidelines.json",
    )
    if not os.path.exists(json_path):
        logger.info("seed/cde_guidelines.json not found, skipping regulatory documents seed")
        return

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    source_id = data["source_id"]
    channel_id = data["channel_id"]
    documents = data["documents"]

    async with async_session_factory() as session:
        source = await session.execute(select(DataSource).where(DataSource.id == source_id))
        if source.scalar_one_or_none() is None:
            logger.warning("DataSource %s not found, skipping regulatory documents seed", source_id)
            return

        channel = await session.execute(select(DataChannel).where(DataChannel.id == channel_id))
        if channel.scalar_one_or_none() is None:
            logger.warning("DataChannel %s not found, skipping regulatory documents seed", channel_id)
            return

        added = 0
        for doc_data in documents:
            existing = await session.execute(
                select(RegulatoryDocument).where(
                    RegulatoryDocument.source_id == source_id,
                    RegulatoryDocument.channel_id == channel_id,
                    RegulatoryDocument.document_id == doc_data["document_id"],
                )
            )
            if existing.scalar_one_or_none() is not None:
                continue

            doc = RegulatoryDocument(
                id=uuid.uuid4(),
                source_id=source_id,
                channel_id=channel_id,
                document_id=doc_data["document_id"],
                title=doc_data["title"],
                publish_date=doc_data.get("publish_date"),
                status_text=doc_data.get("status_text"),
                classification=doc_data.get("classification"),
                original_url=doc_data.get("original_url"),
                raw_data=doc_data.get("raw_data"),
            )
            session.add(doc)
            added += 1

        await session.commit()
        if added:
            logger.info("Seeded %d regulatory documents", added)


async def run_seed() -> None:
    """Run all regulatory tracker seed functions. Any failure is non-fatal."""
    for name, fn in [
        ("regulatory_tracker", _seed_regulatory_tracker),
        ("regulatory_documents", _seed_regulatory_documents),
    ]:
        try:
            await fn()
        except Exception:
            logger.exception("Regulatory tracker seed '%s' failed (non-fatal)", name)
