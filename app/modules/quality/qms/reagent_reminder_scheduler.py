"""试剂提醒定时任务调度器

使用 APScheduler 实现每天早上 8:30 自动检查试剂库存并发送飞书提醒。
"""

import logging
from datetime import datetime

from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# 全局调度器实例
_scheduler: AsyncIOScheduler | None = None


class ReagentReminderScheduler:
    """试剂提醒定时任务调度器"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler(
            jobstores={"default": MemoryJobStore()},
            job_defaults={"coalesce": True, "max_instances": 1},
        )
        self._job_id = "reagent_reminder_daily"

    def start(self):
        """启动调度器并添加每日提醒任务"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("试剂提醒调度器已启动")

        # 添加每天早上 8:30 的定时任务
        self.add_daily_reminder_job()

    def shutdown(self):
        """关闭调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("试剂提醒调度器已关闭")

    def add_daily_reminder_job(self):
        """添加每日提醒任务（每天早上 8:30）"""
        # 检查是否已存在该任务
        existing_job = self.scheduler.get_job(self._job_id)
        if existing_job:
            logger.info("试剂提醒任务已存在，跳过添加")
            return

        self.scheduler.add_job(
            func=self._run_reminder_check,
            trigger=CronTrigger(hour=8, minute=30, timezone="Asia/Shanghai"),
            id=self._job_id,
            name="试剂库存每日提醒",
            replace_existing=True,
        )
        logger.info("已添加每日试剂库存提醒任务（每天 08:30）")

    def remove_daily_reminder_job(self):
        """移除每日提醒任务"""
        self.scheduler.remove_job(self._job_id)
        logger.info("已移除每日试剂库存提醒任务")

    async def _run_reminder_check(self):
        """执行提醒检查"""
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

    def get_next_run_time(self) -> datetime | None:
        """获取下次执行时间"""
        job = self.scheduler.get_job(self._job_id)
        if job:
            return job.next_run_time
        return None


def get_reagent_reminder_scheduler() -> ReagentReminderScheduler:
    """获取或创建调度器实例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = ReagentReminderScheduler()
    return _scheduler


def start_reagent_reminder_scheduler():
    """启动调度器（供应用启动时调用）"""
    scheduler = get_reagent_reminder_scheduler()
    scheduler.start()
    return scheduler


def stop_reagent_reminder_scheduler():
    """停止调度器（供应用关闭时调用）"""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown()
        _scheduler = None
