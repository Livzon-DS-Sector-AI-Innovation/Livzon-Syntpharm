"""SOP AI 模块定时任务调度器

使用 SchedulerEngine 的 TaskGenerator 模式替代 APScheduler，
实现定时文件巡检任务的动态管理。
"""

import logging
from datetime import datetime, timezone

from app.modules.quality.sop_ai.scheduler_models import ScheduledJob
from app.platform.scheduler import ScheduleConfig, ScheduleStrategy, TaskGenerator
from app.platform.scheduler.registry import scheduler_registry

logger = logging.getLogger(__name__)

_CST = timezone(__import__("datetime").timedelta(hours=8))


def _cron_matches(cron_expr: str, now: datetime) -> bool:
    """检查 cron 表达式是否匹配当前时间（精确到分钟）"""
    try:
        import croniter

        cron = croniter.croniter(cron_expr, now.replace(second=0, microsecond=0))
        prev = cron.get_prev(datetime)
        return prev == now.replace(second=0, microsecond=0)
    except Exception:
        return False


class SopAiSchedulerGenerator(TaskGenerator):
    """SOP AI 定时任务扫描器

    每隔 60 秒扫描内存中的定时任务，执行匹配 cron 表达式的任务。
    """

    name = "quality.sop_ai_jobs"
    schedule = ScheduleConfig(
        strategy=ScheduleStrategy.INTERVAL,
        interval_seconds=60,
    )

    def __init__(self):
        super().__init__()
        self._jobs: dict[str, ScheduledJob] = {}
        self._callbacks: dict[str, object] = {}

    async def find_due(self, session):
        return []

    async def execute_one(self, session, item) -> None:
        pass

    async def execute_all(self, session) -> None:
        now = datetime.now(_CST)
        for job in list(self._jobs.values()):
            if not job.enabled:
                continue
            if _cron_matches(job.cron_expression, now):
                callback = self._callbacks.get(job.job_id)
                if callback:
                    try:
                        await callback()
                        job.last_run_time = now
                        job.run_count += 1
                        logger.info(f"定时任务执行完成: {job.job_id}")
                    except Exception as e:
                        logger.error(f"定时任务执行失败: {job.job_id}, error={e}")

    def add_job(
        self,
        job_id: str,
        job_name: str,
        cron_expression: str,
        file_pattern: str,
        callback,
        enabled: bool = True,
    ) -> ScheduledJob | None:
        if job_id in self._jobs:
            logger.warning(f"任务已存在: {job_id}")
            return None

        try:
            import croniter

            croniter.croniter(cron_expression)
        except Exception as e:
            logger.error(f"无效的 Cron 表达式: {cron_expression}, error={e}")
            return None

        job = ScheduledJob(
            job_id=job_id,
            job_name=job_name,
            cron_expression=cron_expression,
            file_pattern=file_pattern,
            enabled=enabled,
        )
        self._jobs[job_id] = job
        self._callbacks[job_id] = callback
        logger.info(f"定时任务已添加: {job_id}")
        return job

    def remove_job(self, job_id: str) -> bool:
        if job_id not in self._jobs:
            return False
        del self._jobs[job_id]
        self._callbacks.pop(job_id, None)
        logger.info(f"定时任务已删除: {job_id}")
        return True

    def pause_job(self, job_id: str) -> bool:
        if job_id in self._jobs:
            self._jobs[job_id].enabled = False
            logger.info(f"定时任务已暂停: {job_id}")
            return True
        return False

    def resume_job(self, job_id: str) -> bool:
        if job_id in self._jobs:
            self._jobs[job_id].enabled = True
            logger.info(f"定时任务已恢复: {job_id}")
            return True
        return False

    def get_job(self, job_id: str) -> ScheduledJob | None:
        return self._jobs.get(job_id)

    def list_jobs(self) -> list[ScheduledJob]:
        return list(self._jobs.values())


_generator: SopAiSchedulerGenerator | None = None


def get_sop_ai_scheduler() -> SopAiSchedulerGenerator:
    global _generator
    if _generator is None:
        _generator = SopAiSchedulerGenerator()
    return _generator


def register():
    scheduler_registry.register_generator(get_sop_ai_scheduler())
    logger.info("SOP AI 定时任务生成器已注册")
