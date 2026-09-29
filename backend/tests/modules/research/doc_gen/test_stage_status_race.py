"""_stage_status 取消竞态回归测试。

Bug 场景：外部事务（API 取消）把任务置为 ``cancelled`` 后，执行 session 内存里的
``job.status`` 是陈旧值（``expire_on_commit=False``）。若照常 ORM 写运行中状态并
commit，会把「已取消」覆盖回运行中，取消监视轮询从此查不到标记——任务白跑到底，
终态还被错标成 failed。``_stage_status`` 用条件 UPDATE（``status != 'cancelled'``）
保证取消一旦生效绝不被覆盖。
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

import pytest

from app.modules.research.doc_gen import pipeline, repository
from app.modules.research.doc_gen.cancellation import AbortHandle
from app.modules.research.doc_gen.models import DocGenJob


class _FakeSession:
    """只支持 _stage_status 用到的接口；rowcount 模拟行是否已被外部置为 cancelled。"""

    def __init__(self, rowcount: int = 1) -> None:
        self._rowcount = rowcount
        self.executed: list[Any] = []
        self.commits = 0

    async def execute(self, statement: Any) -> Any:
        self.executed.append(statement)
        return SimpleNamespace(rowcount=self._rowcount)

    async def commit(self) -> None:
        self.commits += 1


def _session(rowcount: int = 1) -> Any:
    """工厂包装：给 mypy 返回 Any，替身不必伪装成 AsyncSession。"""
    return _FakeSession(rowcount)


def _job(status: str = "queued") -> DocGenJob:
    return DocGenJob(id=uuid.uuid4(), status=status, step="排队", progress=0)


def _patch_db_cancel(monkeypatch: pytest.MonkeyPatch, cancelled: bool) -> None:
    async def _cancel_requested(_session: Any, _job_id: Any) -> bool:
        return cancelled

    monkeypatch.setattr(repository, "cancel_requested", _cancel_requested)


async def test_normal_write_syncs_memory_and_commits(monkeypatch: pytest.MonkeyPatch) -> None:
    """正常路径：条件 UPDATE 命中，落库提交且内存同步（供上层返回与后续读取）。"""
    _patch_db_cancel(monkeypatch, False)
    session = _session(rowcount=1)
    job = _job()
    await pipeline._stage_status(session, job, None, "extracting", step="AI 分析资料", progress=30)
    assert (job.status, job.step, job.progress) == ("extracting", "AI 分析资料", 30)
    assert session.commits == 1


async def test_cancelled_row_is_never_overwritten(monkeypatch: pytest.MonkeyPatch) -> None:
    """复查与写入之间取消已落库（rowcount=0）：抛取消异常、不提交、内存同步为 cancelled。"""
    _patch_db_cancel(monkeypatch, False)
    session = _session(rowcount=0)
    job = _job()
    with pytest.raises(pipeline.JobAbortedError):
        await pipeline._stage_status(session, job, None, "extracting", step="AI 分析资料")
    assert job.status == "cancelled"
    assert session.commits == 0


async def test_db_cancel_detected_before_write(monkeypatch: pytest.MonkeyPatch) -> None:
    """前置复查命中：连条件 UPDATE 都不执行，绝不碰数据库状态。"""
    _patch_db_cancel(monkeypatch, True)
    session = _session()
    job = _job()
    with pytest.raises(pipeline.JobAbortedError):
        await pipeline._stage_status(session, job, None, "parsing", step="解析资料")
    assert session.executed == []
    assert session.commits == 0


async def test_in_process_handle_cancel_detected_before_write(monkeypatch: pytest.MonkeyPatch) -> None:
    """同进程取消（心跳/租约失效置 handle）：同样在写库前中止。"""
    _patch_db_cancel(monkeypatch, False)
    handle = AbortHandle(uuid.uuid4())
    handle.request("superseded")
    session = _session()
    job = _job()
    with pytest.raises(pipeline.JobAbortedError):
        await pipeline._stage_status(session, job, handle, "rendering", step="填充模板")
    assert session.executed == []
