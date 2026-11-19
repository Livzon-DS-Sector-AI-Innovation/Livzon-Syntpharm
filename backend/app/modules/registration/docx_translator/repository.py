"""DOCX 翻译 —— 数据访问（术语表 + 历史产出文件）。"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from .models import DocxTranslationFile, DocxTranslationTask, DocxTranslationTerm


class DocxTranslationTermRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, term_id: UUID) -> DocxTranslationTerm | None:
        result = await self.session.execute(
            select(DocxTranslationTerm).where(
                DocxTranslationTerm.id == term_id,
                DocxTranslationTerm.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_en(self, term_en: str) -> DocxTranslationTerm | None:
        result = await self.session.execute(
            select(DocxTranslationTerm).where(
                DocxTranslationTerm.term_en_lower == term_en.strip().lower(),
                DocxTranslationTerm.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def list_terms(
        self,
        *,
        keyword: str | None = None,
        enabled: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DocxTranslationTerm], int]:
        stmt = select(DocxTranslationTerm).where(DocxTranslationTerm.is_deleted.is_(False))
        if keyword:
            like = f"%{keyword.strip()}%"
            stmt = stmt.where(or_(DocxTranslationTerm.term_en.ilike(like), DocxTranslationTerm.term_zh.ilike(like)))
        if enabled is not None:
            stmt = stmt.where(DocxTranslationTerm.is_enabled.is_(enabled))

        total_result = await self.session.execute(select(func.count()).select_from(stmt.subquery()))
        total = total_result.scalar() or 0

        stmt = (
            stmt.order_by(DocxTranslationTerm.term_en_lower.asc(), DocxTranslationTerm.term_en.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = await self.session.execute(stmt)
        return list(rows.scalars().all()), total

    async def list_enabled(self) -> list[DocxTranslationTerm]:
        result = await self.session.execute(
            select(DocxTranslationTerm)
            .where(
                DocxTranslationTerm.is_deleted.is_(False),
                DocxTranslationTerm.is_enabled.is_(True),
            )
            .order_by(DocxTranslationTerm.term_en_lower.asc(), DocxTranslationTerm.term_en.asc())
        )
        return list(result.scalars().all())

    async def list_all(self, limit: int = 10000) -> list[DocxTranslationTerm]:
        result = await self.session.execute(
            select(DocxTranslationTerm)
            .where(DocxTranslationTerm.is_deleted.is_(False))
            .order_by(DocxTranslationTerm.term_en_lower.asc(), DocxTranslationTerm.term_en.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(
                select(DocxTranslationTerm.id).where(DocxTranslationTerm.is_deleted.is_(False)).subquery()
            )
        )
        return result.scalar() or 0

    async def create(self, term: DocxTranslationTerm) -> DocxTranslationTerm:
        self.session.add(term)
        await self.session.commit()
        await self.session.refresh(term)
        return term

    async def save(self, term: DocxTranslationTerm) -> DocxTranslationTerm:
        await self.session.commit()
        await self.session.refresh(term)
        return term


class DocxTranslationFileRepository:
    """历史产出文件的数据访问（列表/下载/删除/过期清理共用）。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, file_id: UUID) -> DocxTranslationFile | None:
        result = await self.session.execute(
            select(DocxTranslationFile).where(
                DocxTranslationFile.id == file_id,
                DocxTranslationFile.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def list_files(
        self, *, keyword: str | None = None, page: int = 1, page_size: int = 20
    ) -> tuple[list[DocxTranslationFile], int]:
        stmt = select(DocxTranslationFile).where(DocxTranslationFile.is_deleted.is_(False))
        if keyword:
            like = f"%{keyword.strip()}%"
            stmt = stmt.where(
                or_(
                    DocxTranslationFile.source_filename.ilike(like),
                    DocxTranslationFile.output_filename.ilike(like),
                )
            )

        total_result = await self.session.execute(select(func.count()).select_from(stmt.subquery()))
        total = total_result.scalar() or 0

        stmt = stmt.order_by(DocxTranslationFile.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = await self.session.execute(stmt)
        return list(rows.scalars().all()), total

    async def delete_by_source(self, job_ref: str, source_filename: str) -> None:
        """重放幂等：同一任务下同一源文件的旧记录先物理删除（含失败行）。"""
        await self.session.execute(
            delete(DocxTranslationFile).where(
                DocxTranslationFile.job_ref == job_ref,
                DocxTranslationFile.source_filename == source_filename,
            )
        )
        await self.session.commit()

    async def list_by_job(self, job_ref: str) -> list[DocxTranslationFile]:
        result = await self.session.execute(
            select(DocxTranslationFile)
            .where(
                DocxTranslationFile.job_ref == job_ref,
                DocxTranslationFile.is_deleted.is_(False),
            )
            .order_by(DocxTranslationFile.source_filename.asc(), DocxTranslationFile.output_kind.asc())
        )
        return list(result.scalars().all())

    async def soft_delete_by_job(self, job_ref: str) -> int:
        rows = await self.list_by_job(job_ref)
        return await self.soft_delete_many(rows)

    async def sum_sizes_by_job(self, job_refs: list[str]) -> dict[str, int]:
        """按任务汇总产出文件大小（列表展示用，避免逐行子查询）。"""
        if not job_refs:
            return {}
        result = await self.session.execute(
            select(DocxTranslationFile.job_ref, func.sum(DocxTranslationFile.file_size))
            .where(
                DocxTranslationFile.job_ref.in_(job_refs),
                DocxTranslationFile.is_deleted.is_(False),
            )
            .group_by(DocxTranslationFile.job_ref)
        )
        return {str(row[0]): int(row[1] or 0) for row in result.all()}

    async def list_expired(self, cutoff: datetime, limit: int = 200) -> list[DocxTranslationFile]:
        result = await self.session.execute(
            select(DocxTranslationFile)
            .where(
                DocxTranslationFile.is_deleted.is_(False),
                DocxTranslationFile.created_at < cutoff,
            )
            .order_by(DocxTranslationFile.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_many(self, rows: list[DocxTranslationFile]) -> int:
        """批量落库；`(job_ref, object_key)` 冲突时跳过（spawn_task 重放幂等）。"""
        if not rows:
            return 0
        values = [
            {
                "id": row.id,
                "task_id": row.task_id,
                "job_ref": row.job_ref,
                "source_filename": row.source_filename,
                "output_filename": row.output_filename,
                "output_kind": row.output_kind,
                "object_key": row.object_key,
                "file_size": row.file_size,
                "source_lang": row.source_lang,
                "target_lang": row.target_lang,
                "mode": row.mode,
                "success_rate": row.success_rate,
                "translated_units": row.translated_units,
                "total_units": row.total_units,
                "warnings": row.warnings,
                "success": True if row.success is None else row.success,
                "error": row.error,
                "created_by": row.created_by,
            }
            for row in rows
        ]
        stmt = (
            pg_insert(DocxTranslationFile)
            .values(values)
            .on_conflict_do_nothing(constraint="uq_docx_translation_files_job_object")
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return len(values)

    async def soft_delete(self, row: DocxTranslationFile) -> None:
        row.is_deleted = True
        await self.session.commit()

    async def soft_delete_many(self, rows: list[DocxTranslationFile]) -> int:
        for row in rows:
            row.is_deleted = True
        await self.session.commit()
        return len(rows)


class DocxTranslationTaskRepository:
    """任务级历史的数据访问（列表/详情/收尾/清理）。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, task_id: UUID) -> DocxTranslationTask | None:
        result = await self.session.execute(
            select(DocxTranslationTask).where(
                DocxTranslationTask.id == task_id,
                DocxTranslationTask.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_job(self, job_ref: str) -> DocxTranslationTask | None:
        result = await self.session.execute(
            select(DocxTranslationTask).where(
                DocxTranslationTask.job_ref == job_ref,
                DocxTranslationTask.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def create(self, task: DocxTranslationTask) -> DocxTranslationTask:
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def save(self, task: DocxTranslationTask) -> DocxTranslationTask:
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def list_tasks(
        self,
        *,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DocxTranslationTask], int]:
        stmt = select(DocxTranslationTask).where(DocxTranslationTask.is_deleted.is_(False))
        if keyword:
            like = f"%{keyword.strip()}%"
            stmt = stmt.where(DocxTranslationTask.first_source_filename.ilike(like))

        total_result = await self.session.execute(select(func.count()).select_from(stmt.subquery()))
        total = total_result.scalar() or 0

        stmt = stmt.order_by(DocxTranslationTask.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = await self.session.execute(stmt)
        return list(rows.scalars().all()), total

    async def list_expired(self, cutoff: datetime, limit: int = 200) -> list[DocxTranslationTask]:
        result = await self.session.execute(
            select(DocxTranslationTask)
            .where(
                DocxTranslationTask.is_deleted.is_(False),
                DocxTranslationTask.created_at < cutoff,
            )
            .order_by(DocxTranslationTask.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def soft_delete(self, task: DocxTranslationTask) -> None:
        task.is_deleted = True
        await self.session.commit()

    async def soft_delete_many(self, tasks: list[DocxTranslationTask]) -> int:
        for task in tasks:
            task.is_deleted = True
        await self.session.commit()
        return len(tasks)
