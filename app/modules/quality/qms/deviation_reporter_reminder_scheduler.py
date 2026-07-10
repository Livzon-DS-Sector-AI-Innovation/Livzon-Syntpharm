"""偏差填报人提醒定时任务

使用 SchedulerEngine 实现每天早上 8:00 自动检查未完成的偏差任务并发送飞书提醒。
"""

import logging
from datetime import datetime

from app.platform.scheduler import ScheduleConfig, ScheduleStrategy, TaskDefinition
from app.platform.scheduler.registry import scheduler_registry

logger = logging.getLogger(__name__)

JOB_ID = "deviation_reporter_reminder_daily"


async def _run_reminder_check():
    logger.info(f"[{datetime.now()}] 开始执行偏差填报人提醒检查...")
    try:
        from app.modules.quality.qms.deviation_reporter_reminder_service import (
            DeviationReporterReminderService,
        )
        from app.platform.database import get_db_session

        async for session in get_db_session():
            try:
                service = DeviationReporterReminderService(session)
                result = await service.check_and_remind()
                logger.info(f"偏差填报人提醒检查结果: {result}")
                break
            except Exception as e:
                logger.error(f"偏差填报人提醒检查失败: {e}")
                raise
    except Exception as e:
        logger.error(f"定时任务执行失败: {e}")


deviation_reporter_reminder_task = TaskDefinition(
    name="偏差任务填报人每日提醒",
    schedule=ScheduleConfig(
        strategy=ScheduleStrategy.CRON,
        expression="0 8 * * *",
        timezone="Asia/Shanghai",
    ),
    coro=_run_reminder_check,
    module="quality",
    settings_toggle_key="",
)


def register():
    scheduler_registry.register_task(deviation_reporter_reminder_task)
    logger.info("偏差填报人提醒任务已注册（每天 08:00）")
