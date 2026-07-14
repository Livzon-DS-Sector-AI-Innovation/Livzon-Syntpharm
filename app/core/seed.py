"""Auto-seed module — runs during application startup to ensure required
configuration data exists in the database.

All seed functions are idempotent: they check for existing data before
inserting, so re-running is safe.
"""

import json
import logging
import os
import uuid

from sqlalchemy import select

from app.core.database import async_session_factory

logger = logging.getLogger(__name__)


# ── S.6 包装系统 AI 配置 ─────────────────────────────────────────


async def _seed_s6_ai_config():
    """确保 S.6 章节的 FieldMapping + AssetCategory 存在。"""
    from app.modules.registration.dossier_writer.field_models import (
        AssetCategory,
        FieldMapping,
    )
    from app.modules.registration.dossier_writer.seed_data import (
        S6_ASSET_CATEGORIES,
        S6_FIELD_MAPPINGS,
    )

    async with async_session_factory() as session:
        # 检查是否已有 S.6 配置
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


# ── 模块运行配置 ─────────────────────────────────────────────────


_DEFAULT_SETTINGS = [
    # Safety module
    ("safety", "SAFETY_AI_TEXT_MODEL", "deepseek-v4-flash", "string", "AI model for text analysis"),
    ("safety", "SAFETY_AI_VISION_MODEL", "qwen-vl-max", "string", "AI model for image analysis"),
    ("safety", "SAFETY_FEISHU_BITABLE_APP_TOKEN", "", "string", "Feishu bitable app token for safety module"),
    ("safety", "SAFETY_FEISHU_BITABLE_HAZARD_TABLE_ID", "", "string", "Feishu bitable hazard table ID"),
    # Equipment module
    ("equipment", "EQUIPMENT_FEISHU_WS_ENABLED", "false", "bool", "Enable Feishu WebSocket for equipment module"),
    ("equipment", "MAINTENANCE_PLAN_AUTO_ENABLED", "true", "bool", "Auto-generate maintenance plans"),
    # Energy module
    ("energy", "ENERGY_AUTO_COLLECT_ENABLED", "false", "bool", "Enable automatic energy data collection"),
    # HR module
    ("hr", "FEISHU_BOT_NAME", "", "string", "Feishu bot name for HR module"),
    ("hr", "AI_MODEL", "kimi-k2.5", "string", "AI model for HR analysis"),
    ("hr", "AI_SYSTEM_PROMPT", "你是「小H」，原料药工厂人事管理助手。只基于查询结果回答人事问题，禁止编造。回答极其简洁，只陈述事实，不分析、不解释、不推理。", "string", "System prompt for HR AI assistant"),
    # Regulatory tracker module
    ("regulatory_tracker", "DAILY_SYNC_CRON", "0 2 * * *", "string", "Cron schedule for daily regulatory sync"),
    ("regulatory_tracker", "CRAWLER_HEADLESS", "true", "bool", "Run crawler in headless mode"),
    ("regulatory_tracker", "CRAWLER_BROWSERS_PATH", "", "string", "Playwright browsers path (empty = default)"),
    ("regulatory_tracker", "CDE_GUIDELINE_URL", "https://www.cde.org.cn/zdyz/listpage/9cd8db3b7530c6fa0c86485e563f93c7", "string", "CDE guideline URL to track"),
]


async def _seed_module_settings():
    """确保默认模块配置项存在。"""
    from app.core.config_model import ModuleSetting

    async with async_session_factory() as session:
        result = await session.execute(
            select(ModuleSetting.module, ModuleSetting.key)
        )
        existing = {(row.module, row.key) for row in result.fetchall()}

        added = 0
        for module, key, value, value_type, description in _DEFAULT_SETTINGS:
            if (module, key) in existing:
                continue
            session.add(
                ModuleSetting(
                    module=module,
                    key=key,
                    value=value,
                    value_type=value_type,
                    description=description,
                )
            )
            added += 1

        await session.commit()
        if added:
            logger.info("Seeded %d new module settings", added)


# ── 法规追踪数据源 ───────────────────────────────────────────────


async def _seed_regulatory_tracker():
    """确保 CDE / NMPA 数据源和频道存在。"""
    from app.modules.registration.regulatory_tracker.models import DataChannel, DataSource

    async with async_session_factory() as session:
        # CDE
        result = await session.execute(
            select(DataSource).where(DataSource.code == "CDE")
        )
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

        # NMPA
        result = await session.execute(
            select(DataSource).where(DataSource.code == "NMPA")
        )
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


# ── 法规文档初始数据 ─────────────────────────────────────────────


async def _seed_regulatory_documents():
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
        # 验证 source 和 channel 存在
        source = await session.execute(
            select(DataSource).where(DataSource.id == source_id)
        )
        if source.scalar_one_or_none() is None:
            logger.warning("DataSource %s not found, skipping regulatory documents seed", source_id)
            return

        channel = await session.execute(
            select(DataChannel).where(DataChannel.id == channel_id)
        )
        if channel.scalar_one_or_none() is None:
            logger.warning("DataChannel %s not found, skipping regulatory documents seed", channel_id)
            return

        added = 0
        for doc_data in documents:
            # 按唯一约束检查是否已存在
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


# ── 统一入口 ─────────────────────────────────────────────────────


async def run_seeds():
    """执行所有种子数据初始化。任何一项失败不阻塞启动。"""
    seeds = [
        ("module_settings", _seed_module_settings),
        ("regulatory_tracker", _seed_regulatory_tracker),
        ("regulatory_documents", _seed_regulatory_documents),
        ("s6_ai_config", _seed_s6_ai_config),
    ]

    logger.info("Running auto-seeds...")
    for name, fn in seeds:
        try:
            await fn()
        except Exception:
            logger.exception("Seed '%s' failed (non-fatal)", name)
    logger.info("Auto-seeds complete")
