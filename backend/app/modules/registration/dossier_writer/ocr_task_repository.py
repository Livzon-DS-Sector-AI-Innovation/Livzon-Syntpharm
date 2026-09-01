"""OCR task repository for managing async OCR extraction tasks."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import OcrExtractionTask


class OcrTaskRepository:
    """Repository for OCR extraction tasks."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_task(
        self,
        asset_id: UUID,
        chapter_id: UUID | None,
        task_type: str,
    ) -> OcrExtractionTask:
        """创建OCR任务记录"""
        task = OcrExtractionTask(
            asset_id=asset_id,
            chapter_id=chapter_id,
            task_type=task_type,
            status="pending",
        )
        self.db.add(task)
        await self.db.flush()
        return task

    async def update_status(
        self,
        task_id: UUID,
        status: str,
        **kwargs: Any,
    ) -> OcrExtractionTask:
        """更新任务状态"""
        task = await self.get_task(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        task.status = status
        if status == "processing" and not task.started_at:
            task.started_at = datetime.now(UTC)
        elif status in ("completed", "failed"):
            task.completed_at = datetime.now(UTC)

        for key, value in kwargs.items():
            setattr(task, key, value)

        await self.db.flush()
        return task

    async def get_task(self, task_id: UUID) -> OcrExtractionTask | None:
        """获取任务详情"""
        stmt = select(OcrExtractionTask).where(OcrExtractionTask.id == task_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_tasks_by_asset(
        self,
        asset_id: UUID,
        limit: int = 10,
    ) -> list[OcrExtractionTask]:
        """获取素材的OCR任务列表"""
        stmt = (
            select(OcrExtractionTask)
            .where(OcrExtractionTask.asset_id == asset_id)
            .order_by(OcrExtractionTask.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
