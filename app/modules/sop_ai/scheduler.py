"""SOP AI 模块定时任务调度器

使用 APScheduler 实现定时文件巡检任务。
"""

import logging
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore

from app.modules.sop_ai.scheduler_models import ScheduledJob

logger = logging.getLogger(__name__)


class SopAiScheduler:
    """SOP AI 定时任务调度器

    管理定时文件巡检任务的创建、删除和执行。
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler(
            jobstores={"default": MemoryJobStore()},
            job_defaults={"coalesce": True, "max_instances": 1},
        )
        self._jobs: dict[str, ScheduledJob] = {}

    def start(self):
        """启动调度器"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("SOP AI 调度器已启动")

    def shutdown(self):
        """关闭调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("SOP AI 调度器已关闭")

    def add_job(
        self,
        job_id: str,
        job_name: str,
        cron_expression: str,
        file_pattern: str,
        callback,
        enabled: bool = True,
    ) -> Optional[ScheduledJob]:
        """添加定时任务

        Args:
            job_id: 任务ID
            job_name: 任务名称
            cron_expression: Cron 表达式（如 "0 2 * * *" 表示每天凌晨2点）
            file_pattern: 文件匹配模式
            callback: 回调函数
            enabled: 是否启用

        Returns:
            ScheduledJob 对象
        """
        if job_id in self._jobs:
            logger.warning(f"任务已存在: {job_id}")
            return None

        # 解析 Cron 表达式
        try:
            parts = cron_expression.split()
            if len(parts) != 5:
                raise ValueError(f"无效的 Cron 表达式: {cron_expression}")

            trigger = CronTrigger(
                minute=parts[0],
                hour=parts[1],
                day=parts[2],
                month=parts[3],
                day_of_week=parts[4],
            )
        except Exception as e:
            logger.error(f"解析 Cron 表达式失败: {e}")
            return None

        # 创建任务
        job = ScheduledJob(
            job_id=job_id,
            job_name=job_name,
            cron_expression=cron_expression,
            file_pattern=file_pattern,
            enabled=enabled,
        )

        # 添加到调度器
        try:
            self.scheduler.add_job(
                callback,
                trigger=trigger,
                id=job_id,
                name=job_name,
                replace_existing=True,
            )
            self._jobs[job_id] = job
            logger.info(f"定时任务已添加: {job_id}")
            return job
        except Exception as e:
            logger.error(f"添加定时任务失败: {e}")
            return None

    def remove_job(self, job_id: str) -> bool:
        """删除定时任务

        Args:
            job_id: 任务ID

        Returns:
            是否成功
        """
        if job_id not in self._jobs:
            return False

        try:
            self.scheduler.remove_job(job_id)
            del self._jobs[job_id]
            logger.info(f"定时任务已删除: {job_id}")
            return True
        except Exception as e:
            logger.error(f"删除定时任务失败: {e}")
            return False

    def pause_job(self, job_id: str) -> bool:
        """暂停定时任务

        Args:
            job_id: 任务ID

        Returns:
            是否成功
        """
        try:
            self.scheduler.pause_job(job_id)
            if job_id in self._jobs:
                self._jobs[job_id].enabled = False
            logger.info(f"定时任务已暂停: {job_id}")
            return True
        except Exception as e:
            logger.error(f"暂停定时任务失败: {e}")
            return False

    def resume_job(self, job_id: str) -> bool:
        """恢复定时任务

        Args:
            job_id: 任务ID

        Returns:
            是否成功
        """
        try:
            self.scheduler.resume_job(job_id)
            if job_id in self._jobs:
                self._jobs[job_id].enabled = True
            logger.info(f"定时任务已恢复: {job_id}")
            return True
        except Exception as e:
            logger.error(f"恢复定时任务失败: {e}")
            return False

    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        """获取任务信息

        Args:
            job_id: 任务ID

        Returns:
            ScheduledJob 对象
        """
        return self._jobs.get(job_id)

    def list_jobs(self) -> list[ScheduledJob]:
        """获取所有任务"""
        return list(self._jobs.values())

    def get_next_run_time(self, job_id: str) -> Optional[datetime]:
        """获取下次运行时间

        Args:
            job_id: 任务ID

        Returns:
            下次运行时间
        """
        job = self.scheduler.get_job(job_id)
        if job:
            return job.next_run_time
        return None


# 全局调度器实例
_scheduler: Optional[SopAiScheduler] = None


def get_sop_ai_scheduler() -> SopAiScheduler:
    """获取全局调度器实例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = SopAiScheduler()
    return _scheduler