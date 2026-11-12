"""Nightly 00:00 Asia/Shanghai org sync registration (ticket #197)."""

from __future__ import annotations

import logging

from app.modules.hr.org_service import run_scheduled_org_sync
from app.platform.scheduler import ScheduleConfig, ScheduleStrategy, TaskDefinition
from app.platform.scheduler.registry import scheduler_registry

logger = logging.getLogger(__name__)

TASK_NAME = "hr.org_sync_departments"

hr_org_sync_task = TaskDefinition(
    name=TASK_NAME,
    schedule=ScheduleConfig(
        strategy=ScheduleStrategy.CRON,
        expression="0 0 * * *",
        timezone="Asia/Shanghai",
    ),
    coro=run_scheduled_org_sync,
    module="hr",
    timeout_seconds=900,
)


def register() -> None:
    """Register the HR org sync task; safe to call more than once."""
    if TASK_NAME in scheduler_registry.tasks:
        return
    scheduler_registry.register_task(hr_org_sync_task)
    logger.info("HR org sync scheduler registered (daily 00:00 Asia/Shanghai)")
