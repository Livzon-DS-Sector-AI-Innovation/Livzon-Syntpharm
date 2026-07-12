"""试剂提醒定时任务

使用 SchedulerEngine 实现每天早上 8:30 自动检查试剂库存并发送飞书提醒。
"""

import logging
from datetime import datetime
from typing import Any

from app.platform.scheduler import ScheduleConfig, ScheduleStrategy, TaskDefinition
from app.platform.scheduler.registry import scheduler_registry  # type: ignore[attr-defined]

logger = logging.getLogger(__name__)

JOB_ID = "reagent_reminder_daily"


async def _run_reminder_check() -> Any:
    logger.info(f"[{datetime.now()}] 开始执行每日试剂库存检查...")
    try:
        from app.modules.quality.qms.reagent_reminder_service import (
            ReagentReminderService,
        )
        from app.platform.database import get_db_session

        async for session in get_db_session():
            try:
                service = ReagentReminderService(session)
                result = await service.check_and_remind()
                logger.info(f"试剂库存检查结果: {result}")
                break
            except Exception as e:
                logger.error(f"试剂库存检查失败: {e}")
                raise
    except Exception as e:
        logger.error(f"定时任务执行失败: {e}")


reagent_reminder_task = TaskDefinition(
    name="试剂库存每日提醒",
    schedule=ScheduleConfig(
        strategy=ScheduleStrategy.CRON,
        expression="30 8 * * *",
        timezone="Asia/Shanghai",
    ),
    coro=_run_reminder_check,
    module="quality",
    settings_toggle_key="",
)


def register() -> Any:
    scheduler_registry.register_task(reagent_reminder_task)
    logger.info("试剂库存提醒任务已注册（每天 08:30）")
