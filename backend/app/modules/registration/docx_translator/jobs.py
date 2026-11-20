"""DOCX 翻译 —— 任务注册表。

状态持久化在 `core.background_jobs`（经 `app/core/jobs.py::submit_job`），
因此服务重启后仍可查询到 `done` / `failed` 与结果；
进程内的 `_Progress` 只补充「翻译到第几个文件 / 批内进度」这类分钟级细粒度信息，
重启即丢，前端按「无进度即未知」兜底。
"""

from __future__ import annotations

import logging
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.core.database import async_session_factory
from app.core.exceptions import NotFoundException
from app.core.job_repository import JobRepository
from app.core.jobs import submit_job

from .schemas import DocxTranslationFileResult, DocxTranslationJobState

logger = logging.getLogger(__name__)

_MAX_TRACKED_JOBS = 200


@dataclass
class _Progress:
    started_at: float = 0.0
    finished_at: float | None = None
    files_total: int = 0
    files_done: int = 0
    current_file: str | None = None
    batch_done: int = 0
    batch_total: int = 0


class TranslationJobRegistry:
    """任务状态以 DB 为准，进度以进程内为准。"""

    def __init__(self) -> None:
        self._progress: OrderedDict[str, _Progress] = OrderedDict()

    async def start(
        self,
        name: str,
        files_total: int,
        runner: Callable[[str], Awaitable[dict[str, Any] | None]],
    ) -> str:
        """登记并启动任务，返回 job_id（字符串形式，与历史表 `job_ref` 一致）。"""
        progress = _Progress(files_total=files_total, started_at=time.monotonic())

        async def _runner(job_uuid: UUID) -> dict[str, Any] | None:
            job_id = str(job_uuid)
            self._progress[job_id] = progress
            self._prune()
            try:
                return await runner(job_id)
            finally:
                progress.finished_at = time.monotonic()

        job_uuid = await submit_job(name, _runner)
        return str(job_uuid)

    def update(
        self,
        job_id: str,
        *,
        files_done: int | None = None,
        current_file: str | None = None,
        batch_done: int | None = None,
        batch_total: int | None = None,
    ) -> None:
        progress = self._progress.get(job_id)
        if progress is None:
            return
        if files_done is not None:
            progress.files_done = files_done
        if current_file is not None:
            progress.current_file = current_file
        if batch_done is not None:
            progress.batch_done = batch_done
        if batch_total is not None:
            progress.batch_total = batch_total

    def _prune(self) -> None:
        while len(self._progress) > _MAX_TRACKED_JOBS:
            self._progress.popitem(last=False)

    def exists(self, job_id: str) -> bool:
        """本进程内是否仍持有该任务的进度。

        服务重启后 registry 为空，但数据库里的任务行可能仍是 running，
        据此识别「僵尸任务」。
        """
        return job_id in self._progress

    async def _load_job(self, job_id: str) -> Any:
        try:
            job_uuid = UUID(job_id)
        except (TypeError, ValueError) as exc:
            raise NotFoundException(f"任务 {job_id} 不存在") from exc
        async with async_session_factory() as session:
            return await JobRepository(session).get(job_uuid)

    @staticmethod
    def _elapsed_seconds(job: Any, progress: _Progress | None) -> int:
        if progress is not None and progress.started_at:
            return int((progress.finished_at or time.monotonic()) - progress.started_at)
        started_at = getattr(job, "started_at", None)
        if started_at is None:
            return 0
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=UTC)
        finished_at = getattr(job, "finished_at", None) or datetime.now(UTC)
        if finished_at.tzinfo is None:
            finished_at = finished_at.replace(tzinfo=UTC)
        return max(int((finished_at - started_at).total_seconds()), 0)

    async def state(self, job_id: str) -> DocxTranslationJobState:
        job = await self._load_job(job_id)
        if job is None:
            raise NotFoundException(f"任务 {job_id} 不存在或已被清理")
        progress = self._progress.get(job_id)
        files: list[DocxTranslationFileResult] = []
        if job.result:
            raw_files = job.result.get("files") or []
            files = [DocxTranslationFileResult.model_validate(item) for item in raw_files]
        return DocxTranslationJobState(
            job_id=str(job.id),
            status=job.state,
            files_done=progress.files_done if progress else 0,
            files_total=progress.files_total if progress else 0,
            current_file=progress.current_file if progress else None,
            files=files,
            error=job.error,
            batch_done=progress.batch_done if progress else 0,
            batch_total=progress.batch_total if progress else 0,
            elapsed_seconds=self._elapsed_seconds(job, progress),
        )

    async def states(self, job_ids: list[str]) -> list[DocxTranslationJobState]:
        """批量取状态：不存在的 id 直接跳过，避免单个过期任务拖垮整页。"""
        result: list[DocxTranslationJobState] = []
        for job_id in job_ids:
            try:
                result.append(await self.state(job_id))
            except NotFoundException:
                continue
        return result

    async def mark_failed(self, job_id: str, message: str) -> None:
        """把挂死的任务在持久层标失败，让前端轮询立刻看到失败态。"""
        try:
            job_uuid = UUID(job_id)
        except (TypeError, ValueError):
            return
        async with async_session_factory() as session:
            repo = JobRepository(session)
            job = await repo.get(job_uuid)
            if job is None or job.state != "running":
                return
            await repo.fail(job_uuid, message)

    async def result(self, job_id: str) -> dict[str, Any] | None:
        job = await self._load_job(job_id)
        return job.result if job is not None else None


_registry: TranslationJobRegistry | None = None


def get_registry() -> TranslationJobRegistry:
    global _registry
    if _registry is None:
        _registry = TranslationJobRegistry()
    return _registry


__all__ = ["TranslationJobRegistry", "get_registry"]
