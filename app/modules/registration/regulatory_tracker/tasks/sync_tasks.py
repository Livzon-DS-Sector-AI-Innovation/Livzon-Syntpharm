"""Background sync tasks — SchedulerEngine integration."""

import logging

from app.core.database import async_session_factory
from app.modules.registration.regulatory_tracker import repository as repo
from app.modules.registration.regulatory_tracker.services.ai_analysis_service import (
    analyze_new_documents,
)
from app.modules.registration.regulatory_tracker.services.sync_service import run_sync_job
from app.platform.scheduler import ScheduleConfig, ScheduleStrategy, TaskDefinition
from app.shared.config_reader import get_module_setting_bool

logger = logging.getLogger(__name__)


async def daily_sync_job():
    """每日定时同步任务：同步 CDE 国内药品技术指导原则前 1-3 页。"""
    logger.info("⏰ 开始每日同步任务 (daily_sync, pages 1-3)")

    try:
        async with async_session_factory() as db:
            source = await repo.get_data_source_by_code(db, "CDE")
            if not source:
                logger.error("CDE 数据源不存在，跳过同步")
                return

            channel = await repo.get_channel_by_code(
                db, source.id, "cde_domestic_guideline"
            )
            if not channel:
                logger.error("cde_domestic_guideline 栏目不存在，跳过同步")
                return

            if not source.enabled or not channel.enabled:
                logger.info("数据源或栏目已禁用，跳过同步")
                return

            headless = await get_module_setting_bool(
                "regulatory_tracker", "CRAWLER_HEADLESS", True
            )
            result = await run_sync_job(
                db=db,
                source=source,
                channel=channel,
                job_type="daily_sync",
                start_page=1,
                end_page=3,
                headless=headless,
            )

            logger.info(
                "✅ 每日同步完成: status=%s checked=%d new=%d updated=%d failed=%d error=%s",
                result["status"],
                result["checked"],
                result["new"],
                result["updated"],
                result["failed"],
                result.get("error"),
            )

    except Exception:
        logger.exception("❌ 每日同步任务异常")


async def daily_ai_analysis_job():
    """每日 AI 分析任务：分析新采集的法规文档。"""
    logger.info("⏰ 开始每日 AI 分析任务")

    try:
        async with async_session_factory() as db:
            stats = await analyze_new_documents(db, limit=20)
            logger.info(
                "✅ AI 分析完成: analyzed=%d failed=%d skipped=%d",
                stats["analyzed"],
                stats["failed"],
                stats["skipped"],
            )
    except Exception:
        logger.exception("❌ AI 分析任务异常")


# Task definitions for SchedulerEngine
daily_sync_task = TaskDefinition(
    name="regulatory_tracker.daily_sync",
    schedule=ScheduleConfig(
        strategy=ScheduleStrategy.CRON,
        expression="0 2 * * *",  # 每天凌晨 2 点
        timezone="Asia/Shanghai",
    ),
    coro=daily_sync_job,
    module="regulatory_tracker",
    timeout_seconds=600,
)

daily_ai_analysis_task = TaskDefinition(
    name="regulatory_tracker.daily_ai_analysis",
    schedule=ScheduleConfig(
        strategy=ScheduleStrategy.CRON,
        expression="0 3 * * *",  # 每天凌晨 3 点（同步后 1 小时）
        timezone="Asia/Shanghai",
    ),
    coro=daily_ai_analysis_job,
    module="regulatory_tracker",
    timeout_seconds=600,
)


# ── Scheduler startup ──────────────────────────────────────────

_scheduler_engine = None


def start_scheduler():
    """Initialize and start the scheduler engine with all registered tasks."""
    global _scheduler_engine

    from app.platform.scheduler import SchedulerEngine, SchedulerRegistry
    from app.modules.equipment.public_api import get_inspection_schedule_generator

    registry = SchedulerRegistry()

    # Register regulatory_tracker tasks
    registry.register_task(daily_sync_task)
    registry.register_task(daily_ai_analysis_task)

    # Register equipment generators
    registry.register_generator(get_inspection_schedule_generator())

    # Create and start engine
    _scheduler_engine = SchedulerEngine(registry)
    import asyncio
    asyncio.create_task(_scheduler_engine.run())
    logger.info("Scheduler engine started with %d tasks", len(registry.tasks))
