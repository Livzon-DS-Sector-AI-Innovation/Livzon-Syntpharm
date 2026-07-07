"""偏差填报人提醒定时任务调度器

使用 APScheduler 实现每天早上 8:00 自动检查未完成的偏差任务并发送飞书提醒。
"""

import logging
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore

logger = logging.getLogger(__name__)

# 全局调度器实例
_scheduler: Optional[AsyncIOScheduler] = None


class DeviationReporterReminderScheduler:
    """偏差填报人提醒定时任务调度器"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler(
            jobstores={"default": MemoryJobStore()},
            job_defaults={"coalesce": True, "max_instances": 1},
        )
        self._job_id = "deviation_reporter_reminder_daily"

    def start(self):
        """启动调度器并添加每日提醒任务"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("偏差填报人提醒调度器已启动")

        # 添加每天早上 8:00 的定时任务
        self.add_daily_reminder_job()

    def shutdown(self):
        """关闭调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("偏差填报人提醒调度器已关闭")

    def add_daily_reminder_job(self):
        """添加每日提醒任务（每天早上 8:00）"""
        # 检查是否已存在该任务
        existing_job = self.scheduler.get_job(self._job_id)
        if existing_job:
            logger.info(f"偏差填报人提醒任务已存在，跳过添加")
            return

        self.scheduler.add_job(
            func=self._run_reminder_check,
            trigger=CronTrigger(hour=8, minute=0, timezone="Asia/Shanghai"),
            id=self._job_id,
            name="偏差任务填报人每日提醒",
            replace_existing=True,
        )
        logger.info("已添加每日偏差填报人提醒任务（每天 08:00）")

    def remove_daily_reminder_job(self):
        """移除每日提醒任务"""
        self.scheduler.remove_job(self._job_id)
        logger.info("已移除每日偏差填报人提醒任务")

    async def _run_reminder_check(self):
        """执行提醒检查"""
        logger.info(f"[{datetime.now()}] 开始执行偏差填报人提醒检查...")
        try:
            from app.modules.quality.qms.deviation_reporter_reminder_service import DeviationReporterReminderService
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

    def get_next_run_time(self) -> Optional[datetime]:
        """获取下次执行时间"""
        job = self.scheduler.get_job(self._job_id)
        if job:
            return job.next_run_time
        return None


def get_deviation_reporter_reminder_scheduler() -> DeviationReporterReminderScheduler:
    """获取或创建调度器实例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = DeviationReporterReminderScheduler()
    return _scheduler


def start_deviation_reporter_reminder_scheduler():
    """启动调度器（供应用启动时调用）"""
    scheduler = get_deviation_reporter_reminder_scheduler()
    scheduler.start()
    return scheduler


def stop_deviation_reporter_reminder_scheduler():
    """停止调度器（供应用关闭时调用）"""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown()
        _scheduler = None
