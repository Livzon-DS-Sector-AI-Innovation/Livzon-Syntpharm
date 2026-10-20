"""审计日志过期清理定时任务。

``audit.logs`` 为 append-only 表（无软删除，过期即物理清理）。按
``AUDIT_RETENTION_DAYS``（默认 7 天）每天凌晨清理一次过期记录，分批删除避免长事务锁表。
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.platform.audit.models import AuditLog

logger = logging.getLogger(__name__)

# 每批删除条数：避免单条 DELETE 长事务锁住大表
_BATCH_SIZE = 5000

stop_cleanup_flag = asyncio.Event()


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


async def audit_cleanup_loop() -> None:
    """每天凌晨 04:00 清理一次过期审计日志（独立轮询循环，main.py 启动）。"""
    logger.info(
        "审计日志过期清理任务已启动（每天 04:00，保留 %d 天）",
        get_settings().AUDIT_RETENTION_DAYS,
    )

    while not stop_cleanup_flag.is_set():
        now = datetime.now()
        next_run = (now + timedelta(days=1)).replace(hour=4, minute=0, second=0, microsecond=0)
        wait_seconds = (next_run - now).total_seconds()
        try:
            await asyncio.wait_for(stop_cleanup_flag.wait(), timeout=wait_seconds)
            break
        except TimeoutError:
            pass

        if stop_cleanup_flag.is_set():
            break
        try:
            await cleanup_expired_audit_logs()
        except Exception:
            logger.exception("审计日志过期清理失败")

    logger.info("审计日志过期清理任务已停止")
