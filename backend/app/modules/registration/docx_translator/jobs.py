"""DOCX 翻译 —— 任务注册表。

比通用 `JobStore` 多一层进度表：翻译是分钟级任务，前端需要
`files_done / files_total / current_file` 才能画出进度条。
状态仍存进程内（重启即丢），前端按「任务已过期」兜底。
"""

from __future__ import annotations

import logging
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from app.core.exceptions import NotFoundException
from app.core.job_store import JobStore
from app.core.tasks import spawn_task

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
    """进程内任务：状态 + 进度 + 结果（结果文件在 MinIO，这里只存引用）。"""

    def __init__(self) -> None:
        self._store = JobStore()
        self._progress: OrderedDict[str, _Progress] = OrderedDict()

    def start(
        self,
        name: str,
        files_total: int,
        runner: Callable[[str], Awaitable[dict[str, Any] | None]],
    ) -> str:
        job_id = self._store.create()
        self._progress[job_id] = _Progress(files_total=files_total, started_at=time.monotonic())
        self._prune()
        spawn_task(self._run(job_id, runner), name=f"{name}-{job_id[:8]}")
        return job_id

    async def _run(self, job_id: str, runner: Callable[[str], Awaitable[dict[str, Any] | None]]) -> None:
        try:
            result = await runner(job_id)
            self._store.complete(job_id, result)
        except Exception as e:  # noqa: BLE001 - 后台任务兜底，异常写入任务状态
            logger.exception("docx translation job %s failed", job_id[:8], extra={"job_id": job_id})
            self._store.fail(job_id, str(e))
        finally:
            progress = self._progress.get(job_id)
            if progress is not None:
                progress.finished_at = time.monotonic()

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
            old_id, _ = self._progress.popitem(last=False)
            self._store._jobs.pop(old_id, None)  # noqa: SLF001 - 与 JobStore 同步释放内存

    def exists(self, job_id: str) -> bool:
        """进程内是否还持有该任务状态。

        服务重启后 registry 为空，但数据库里的任务行可能仍是 running，
        据此识别“僵尸任务”。
        """
        return self._store.get(job_id) is not None

    def state(self, job_id: str) -> DocxTranslationJobState:
        job = self._store.get(job_id)
        if job is None:
            raise NotFoundException(f"任务 {job_id} 不存在或服务已重启")
        progress = self._progress.get(job_id) or _Progress()
        files: list[DocxTranslationFileResult] = []
        if job.result:
            raw_files = job.result.get("files") or []
            files = [DocxTranslationFileResult.model_validate(item) for item in raw_files]
        return DocxTranslationJobState(
            job_id=job.job_id,
            status=job.status,
            files_done=progress.files_done,
            files_total=progress.files_total,
            current_file=progress.current_file,
            files=files,
            error=job.error,
            batch_done=progress.batch_done,
            batch_total=progress.batch_total,
            elapsed_seconds=(
                int((progress.finished_at or time.monotonic()) - progress.started_at) if progress.started_at else 0
            ),
        )

    def states(self, job_ids: list[str]) -> list[DocxTranslationJobState]:
        """批量取状态：不存在的 id 直接跳过，避免单个过期任务拖垮整页。"""
        result: list[DocxTranslationJobState] = []
        for job_id in job_ids:
            if not self.exists(job_id):
                continue
            result.append(self.state(job_id))
        return result

    def mark_failed(self, job_id: str, message: str) -> None:
        """把挂死的任务在进程内标失败，让前端轮询立刻看到失败态。"""
        job = self._store.get(job_id)
        if job is None or job.status != "running":
            return
        self._store.fail(job_id, message)

    def result(self, job_id: str) -> dict[str, Any] | None:
        job = self._store.get(job_id)
        return job.result if job else None

    def created_at(self, job_id: str) -> float | None:
        job = self._store.get(job_id)
        return job.created_at if job else None


_registry: TranslationJobRegistry | None = None


def get_registry() -> TranslationJobRegistry:
    global _registry
    if _registry is None:
        _registry = TranslationJobRegistry()
    return _registry


__all__ = ["TranslationJobRegistry", "get_registry"]
