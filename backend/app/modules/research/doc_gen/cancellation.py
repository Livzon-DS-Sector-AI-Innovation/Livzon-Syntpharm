"""正在执行任务的强制终止注册表（进程内通道）。

为什么需要它：数据库里的 ``status='cancelled'`` 是跨副本的真相来源，但从 API 写入
到 worker 命中下一个检查点之间可能隔着一整次模型调用（默认超时 120 秒 × 重试），
而且全局 session 工厂是 ``expire_on_commit=False``，worker 内存里的 ORM 对象**看不见**
别的事务改的状态。所以取消必须双通道：

- **DB 标志**：跨进程、重启后仍有效，worker 主动查库时命中；
- **进程内注册表**（本模块）：置位 ``threading.Event`` 让同步解析在下一个页/行边界退出，
  并对执行中的 ``asyncio.Task`` 调 ``cancel()``，立刻打断 httpx 等待与 ``to_thread`` 等待。

按 AGENTS.md，这里只承载后台工作进程的基础设施能力（心跳、取消分发），不做业务逻辑。
"""

from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AbortHandle:
    """单个在执行任务的取消句柄。"""

    job_id: uuid.UUID
    event: threading.Event = field(default_factory=threading.Event)
    task: asyncio.Task[str | None] | None = None
    reason: str = ""

    def should_cancel(self) -> bool:
        """供同步解析守卫与模型调用边界轮询。"""
        return self.event.is_set()

    def request(self, reason: str) -> None:
        self.reason = self.reason or reason
        self.event.set()


_registry: dict[str, AbortHandle] = {}
_lock = threading.Lock()


def _key(job_id: uuid.UUID | str) -> str:
    return str(job_id)


def register(job_id: uuid.UUID | str) -> AbortHandle:
    """登记一个开始执行的任务，返回其取消句柄。"""
    handle = AbortHandle(job_id=job_id if isinstance(job_id, uuid.UUID) else uuid.UUID(str(job_id)))
    with _lock:
        previous = _registry.get(_key(job_id))
        if previous is not None:
            # 同一任务被重复领取（租约过期后重启的进程又领了一次）：先终止旧的，避免双跑
            previous.request("superseded")
            if previous.task is not None and not previous.task.done():
                previous.task.cancel()
            logger.warning("同一任务被重复领取，已终止上一次执行", extra={"job_id": _key(job_id)})
        _registry[_key(job_id)] = handle
    return handle


def attach_task(handle: AbortHandle, task: asyncio.Task[str | None]) -> None:
    """把执行任务的 asyncio.Task 绑到句柄上，使取消可以抢占 await 点。"""
    handle.task = task
    if handle.event.is_set() and not task.done():
        task.cancel()


def unregister(job_id: uuid.UUID | str) -> None:
    with _lock:
        _registry.pop(_key(job_id), None)


def get(job_id: uuid.UUID | str) -> AbortHandle | None:
    with _lock:
        return _registry.get(_key(job_id))


def request_abort(job_id: uuid.UUID | str, reason: str = "cancelled") -> bool:
    """请求强制终止某个在执行任务。返回是否命中正在执行的任务。"""
    with _lock:
        handle = _registry.get(_key(job_id))
    if handle is None:
        return False
    handle.request(reason)
    if handle.task is not None and not handle.task.done():
        handle.task.cancel()
    logger.info("已发出强制终止请求", extra={"job_id": _key(job_id), "reason": reason})
    return True


def is_aborted(job_id: uuid.UUID | str) -> bool:
    """该任务是否已被请求终止（供检查点查询）。"""
    with _lock:
        handle = _registry.get(_key(job_id))
    return bool(handle and handle.event.is_set())


def should_cancel_for(job_id: uuid.UUID | str) -> Callable[[], bool]:
    """给解析器/提取器的取消探针；任务不在本进程执行时恒为 False。"""
    handle = get(job_id)
    if handle is None:
        return lambda: False
    return handle.should_cancel


def running_job_ids() -> list[str]:
    with _lock:
        return list(_registry)


def abort_all(reason: str = "shutdown") -> int:
    """进程退出/热重载前终止全部在执行任务，让解析与模型调用尽快放手。"""
    with _lock:
        handles = list(_registry.values())
    for handle in handles:
        handle.request(reason)
        if handle.task is not None and not handle.task.done():
            handle.task.cancel()
    if handles:
        logger.info("已终止全部在执行任务", extra={"count": len(handles), "reason": reason})
    return len(handles)
