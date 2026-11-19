"""DOCX 翻译 —— 每日过期译文清理任务。

保留天数取模块配置 `DOCX_TRANSLATOR_RETENTION_DAYS`（<=0 不清理）。
任务注册在 `regulatory_tracker/tasks/sync_tasks.py:start_scheduler()`，
那里是全局 SchedulerEngine 的唯一初始化点。
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.core.database import async_session_factory
from app.platform.scheduler import ScheduleConfig, ScheduleStrategy, TaskDefinition

from .retention import cleanup_expired
from .service import resolve_retention_days

logger = logging.getLogger(__name__)


async def expired_cleanup_job() -> None:
    """清理超过保留天数的译文记录与对象文件。"""
    try:
        days = await resolve_retention_days()
        async with async_session_factory() as session:
            stats = await cleanup_expired(session, days=days, now=datetime.now(UTC))
        logger.info(
            "docx translation retention cleanup done: days=%d scanned=%d deleted=%d objects_failed=%d",
            days,
            stats["scanned"],
            stats["deleted"],
            stats["objects_failed"],
            extra={"biz_module": "registration"},
        )
    except Exception:
        logger.exception("docx translation retention cleanup failed", extra={"biz_module": "registration"})


expired_cleanup_task = TaskDefinition(
    name="docx_translator.expired_cleanup",
    schedule=ScheduleConfig(
        strategy=ScheduleStrategy.CRON,
        expression="30 3 * * *",  # 每天 03:30（与法规同步错开）
        timezone="Asia/Shanghai",
    ),
    coro=expired_cleanup_job,
    module="docx_translator",
    timeout_seconds=900,
)
