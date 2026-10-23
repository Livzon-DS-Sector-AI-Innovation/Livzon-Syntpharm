"""审计日志过期清理定时任务。

``audit.logs`` 为 append-only 表（无软删除，过期即物理清理）。按
``AUDIT_RETENTION_DAYS``（默认 7 天）每天凌晨 04:00 清理一次过期记录，
分批删除避免长事务锁表。

调度走 SchedulerEngine（`TaskDefinition` + `scheduler_registry`），
不再由 main.py 手写 ``asyncio`` 循环：这样任务会出现在「系统运维 → 定时任务」里，
可被运行时开关（``AUDIT_CLEANUP_ENABLED``）与手动触发统一管理。
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.platform.audit.models import AuditLog
from app.platform.scheduler import ScheduleConfig, ScheduleStrategy, TaskDefinition
from app.platform.scheduler.registry import scheduler_registry

logger = logging.getLogger(__name__)

# 每批删除条数：避免单条 DELETE 长事务锁住大表
_BATCH_SIZE = 5000

JOB_ID = "audit_cleanup_daily"


async def cleanup_expired_audit_logs(retention_days: int | None = None) -> int:
    """删除超过保留期的审计日志，返回删除总条数。

    ``retention_days`` 为 None 时读取 ``AUDIT_RETENTION_DAYS``；<=0 时跳过清理。
    """
    if retention_days is None:
        retention_days = get_settings().AUDIT_RETENTION_DAYS
    if retention_days <= 0:
        logger.warning("AUDIT_RETENTION_DAYS=%d，跳过清理（保留期须为正数）", retention_days)
        return 0

    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    total_deleted = 0

    async with async_session_factory() as session:
        while True:
            ids = (
                (await session.execute(select(AuditLog.id).where(AuditLog.created_at < cutoff).limit(_BATCH_SIZE)))
                .scalars()
                .all()
            )
            if not ids:
                break
            await session.execute(delete(AuditLog).where(AuditLog.id.in_(ids)))
            await session.commit()
            total_deleted += len(ids)

    if total_deleted:
        logger.info("审计日志过期清理完成：删除 %d 条（保留 %d 天）", total_deleted, retention_days)
    return total_deleted


async def _run_audit_cleanup() -> None:
    """调度引擎调用的无参入口（保留期从配置读）。"""
    await cleanup_expired_audit_logs()


audit_cleanup_task = TaskDefinition(
    name="审计日志过期清理",
    schedule=ScheduleConfig(
        strategy=ScheduleStrategy.CRON,
        expression="0 4 * * *",
        timezone="Asia/Shanghai",
    ),
    coro=_run_audit_cleanup,
    module="platform",
    settings_toggle_key="AUDIT_CLEANUP_ENABLED",
    # 分批删除大量过期日志可能超过默认 300s，给足时间避免被引擎中途取消
    timeout_seconds=1800,
)


def register() -> Any:
    """注册审计清理任务（幂等，main.py lifespan 调用）。"""
    scheduler_registry.register_task(audit_cleanup_task)
    logger.info(
        "审计日志过期清理任务已注册（每天 04:00，保留 %d 天）",
        get_settings().AUDIT_RETENTION_DAYS,
    )
