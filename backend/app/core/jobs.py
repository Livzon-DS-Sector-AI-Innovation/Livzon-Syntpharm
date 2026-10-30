"""一次性异步任务入口（用户触发的耗时操作）。

`AGENTS.md` 禁止用 `asyncio.create_task()` 处理业务逻辑：无法重试、无法监控、重启后丢失。
本模块是对外的正确入口：

- 先在 `core.background_jobs` 落一行（独立会话提交，不受调用方事务影响），
  任务状态因此可被查询、可在重启后被发现（停在 `running` 表示进程中途退出）；
- 再把协程交给进程内 runner 执行，结束时回写 `done` / `failed` 与错误摘要。

runner 是整个应用里唯一的 `create_task` 出口，属规则允许的基础设施例外；
业务代码只允许调用 `submit_job()`。

注意：本模块只保证「状态不丢」，不保证「可重跑」——重试的幂等性仍由被写入的数据决定
（`AGENTS.md`：所有重试操作必须是幂等的）。
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from app.core.database import async_session_factory
from app.core.job_repository import JobRepository
from app.core.tasks import spawn_task

logger = logging.getLogger(__name__)

__all__ = ["JobRunner", "submit_job"]

JobRunner = Callable[[UUID], Awaitable[Any]]


async def submit_job(name: str, runner: JobRunner) -> UUID:
    """登记并启动一个后台任务，返回 job_id。

    Args:
        name: 任务名（`<module>.<动作>`，如 `safety.rectification-review`）
        runner: `runner(job_id)`，在后台协程里执行；正常返回 dict 记入 result，
            抛异常则记入 error 并置 failed。
    """
    async with async_session_factory() as session:
        job_id = await JobRepository(session).create(name)

    async def _run() -> None:
        try:
            result = await runner(job_id)
        except Exception as exc:  # noqa: BLE001 — 后台任务不能把异常抛给事件循环
            logger.exception("job %s failed: job_id=%s", name, job_id)
            async with async_session_factory() as session:
                await JobRepository(session).fail(job_id, str(exc)[:2000])
        else:
            payload = result if isinstance(result, dict) else None
            async with async_session_factory() as session:
                await JobRepository(session).complete(job_id, payload)

    spawn_task(_run(), name=f"{name}-{str(job_id)[:8]}")
    return job_id
