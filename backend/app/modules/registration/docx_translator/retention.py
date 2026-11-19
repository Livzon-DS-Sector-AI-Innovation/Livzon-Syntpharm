"""DOCX 翻译 —— 过期译文清理。

按保留天数扫描历史表，删除对象存储里的文件并软删记录。
纯逻辑函数（不依赖请求上下文），便于单测。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from .repository import DocxTranslationTaskRepository
from .service import delete_task_records

logger = logging.getLogger(__name__)


async def cleanup_expired(
    session: AsyncSession,
    *,
    days: int,
    now: datetime,
    batch_limit: int = 200,
) -> dict[str, int]:
    """清理超过保留天数的译文。

    - `days <= 0` 视为不自动清理，直接短路；
    - 单条对象删除失败只记日志，不影响其他记录与记录软删；
    - 返回 `{scanned, deleted, objects_failed}`。
    """
    stats = {"scanned": 0, "deleted": 0, "objects_failed": 0}
    if days <= 0:
        return stats

    cutoff = now - timedelta(days=days)
    repo = DocxTranslationTaskRepository(session)
    tasks = await repo.list_expired(cutoff, limit=batch_limit)
    stats["scanned"] = len(tasks)
    if not tasks:
        return stats

    for task in tasks:
        try:
            await delete_task_records(session, task)
            stats["deleted"] += 1
        except Exception:
            stats["objects_failed"] += 1
            logger.warning(
                "清理过期翻译任务失败",
                extra={"job_id": task.job_ref, "biz_module": "registration"},
                exc_info=True,
            )

    return stats
