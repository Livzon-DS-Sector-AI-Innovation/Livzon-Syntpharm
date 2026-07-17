"""Auto-seed module — runs during application startup to ensure required
configuration data exists in the database.

All seed functions are idempotent: they check for existing data before
inserting, so re-running is safe.

Module-specific seeds live in their respective modules:
- app/modules/registration/dossier_writer/seed.py
- app/modules/registration/regulatory_tracker/seed.py
"""

import logging

from sqlalchemy import select

from app.core.database import async_session_factory

logger = logging.getLogger(__name__)


# ── 模块运行配置 ─────────────────────────────────────────────────

_DEFAULT_SETTINGS = [
    ("safety", "SAFETY_AI_TEXT_MODEL", "deepseek-v4-flash", "string", "AI model for text analysis"),
    ("safety", "SAFETY_AI_VISION_MODEL", "qwen-vl-max", "string", "AI model for image analysis"),
    ("safety", "SAFETY_FEISHU_BITABLE_APP_TOKEN", "", "string", "Feishu bitable app token for safety module"),
    ("safety", "SAFETY_FEISHU_BITABLE_HAZARD_TABLE_ID", "", "string", "Feishu bitable hazard table ID"),
    ("equipment", "EQUIPMENT_FEISHU_WS_ENABLED", "false", "bool", "Enable Feishu WebSocket for equipment module"),
    ("equipment", "MAINTENANCE_PLAN_AUTO_ENABLED", "true", "bool", "Auto-generate maintenance plans"),
    ("energy", "ENERGY_AUTO_COLLECT_ENABLED", "false", "bool", "Enable automatic energy data collection"),
    ("hr", "FEISHU_BOT_NAME", "", "string", "Feishu bot name for HR module"),
    ("hr", "AI_MODEL", "kimi-k2.5", "string", "AI model for HR analysis"),
    (
        "hr",
        "AI_SYSTEM_PROMPT",
        "你是「小H」，原料药工厂人事管理助手。"
        "只基于查询结果回答人事问题，禁止编造。"
        "回答极其简洁，只陈述事实，不分析、不解释、不推理。",
        "string",
        "System prompt for HR AI assistant",
    ),
    ("regulatory_tracker", "DAILY_SYNC_CRON", "0 2 * * *", "string", "Cron schedule for daily regulatory sync"),
    ("regulatory_tracker", "CRAWLER_HEADLESS", "true", "bool", "Run crawler in headless mode"),
    ("regulatory_tracker", "CRAWLER_BROWSERS_PATH", "", "string", "Playwright browsers path (empty = default)"),
    (
        "regulatory_tracker",
        "CDE_GUIDELINE_URL",
        "https://www.cde.org.cn/zdyz/listpage/9cd8db3b7530c6fa0c86485e563f93c7",
        "string",
        "CDE guideline URL to track",
    ),
]


async def _seed_module_settings() -> None:
    """确保默认模块配置项存在。"""
    from app.core.config_model import ModuleSetting

    async with async_session_factory() as session:
        result = await session.execute(select(ModuleSetting.module, ModuleSetting.key))
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


# ── 统一入口 ─────────────────────────────────────────────────────


async def run_seeds() -> None:
    """执行所有种子数据初始化。任何一项失败不阻塞启动。"""
    from app.modules.registration.dossier_writer.seed import run_seed as run_dossier_writer_seed
    from app.modules.registration.regulatory_tracker.seed import run_seed as run_regulatory_tracker_seed

    seeds = [
        ("module_settings", _seed_module_settings),
        ("regulatory_tracker", run_regulatory_tracker_seed),
        ("dossier_writer", run_dossier_writer_seed),
    ]

    logger.info("Running auto-seeds...")
    for name, fn in seeds:
        try:
            await fn()
        except Exception:
            logger.exception("Seed '%s' failed (non-fatal)", name)
    logger.info("Auto-seeds complete")
