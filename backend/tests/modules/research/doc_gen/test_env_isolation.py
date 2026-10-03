"""任务队列环境隔离 + 删除报告联动取消的回归测试。

背景：本地与 UAT 共用同一 Postgres 时，旧部署的 worker 会抢走新环境创建的任务
（跨环境执行、代码版本不一致直接跑崩）。``doc_gen_jobs.env`` 标签 + claim/恢复
过滤是根治手段；同时删除报告必须联动取消未结束任务，避免为已删报告空跑模型。
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.exceptions import BadRequestException
from app.modules.research import service as research_service
from app.modules.research.doc_gen import repository
from app.modules.research.doc_gen import service as doc_gen_service
from app.modules.research.doc_gen.models import DocGenJob


def _job(env: str = "local", status: str = "pending") -> DocGenJob:
    return DocGenJob(id=uuid.uuid4(), status=status, step="排队", progress=0, env=env, attempts=0)


class _CaptureSession:
    """记录执行过的语句；select 返回固定任务行，update 返回 rowcount。"""

    def __init__(self, rows: list[DocGenJob] | None = None) -> None:
        self.statements: list[Any] = []
        self._rows = rows or []
        self.commits = 0

    async def scalar(self, _stmt: Any) -> int:
        return 0

    async def execute(self, statement: Any) -> Any:
        self.statements.append(statement)
        rows = self._rows
        return SimpleNamespace(
            rowcount=len(rows),
            scalar_one_or_none=lambda: rows[0] if rows else None,
            scalars=lambda: SimpleNamespace(all=lambda: rows),
        )

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1


def _sql_of(session: _CaptureSession, index: int = -1) -> tuple[str, dict[str, Any]]:
    compiled = session.statements[index].compile()
    return str(compiled), dict(compiled.params)


# ---------------------------------------------------------------------------
# claim / 启动恢复：env 过滤
# ---------------------------------------------------------------------------


async def test_claim_next_job_filters_by_env() -> None:
    session = _CaptureSession([_job(env="local")])
    job = await repository.claim_next_job(session, 1800, 1, env="local")  # type: ignore[arg-type]
    assert job is not None and job.env == "local"
    # 领取 select 的 where 必须带 env 条件且绑定本环境值
    sql, params = _sql_of(session, 0)
    assert "doc_gen_jobs.env =" in sql
    assert params.get("env_1") == "local"


async def test_claim_next_job_without_env_keeps_legacy_behavior() -> None:
    session = _CaptureSession([_job(env="default")])
    job = await repository.claim_next_job(session, 1800, 1)  # type: ignore[arg-type]
    assert job is not None
    sql, _params = _sql_of(session, 0)
    assert "doc_gen_jobs.env =" not in sql


async def test_recover_stale_jobs_scoped_by_env() -> None:
    session = _CaptureSession([])
    await repository.recover_stale_jobs(session, env="local")  # type: ignore[arg-type]
    sql, params = _sql_of(session, 0)
    assert "UPDATE research.doc_gen_jobs" in sql
    assert "env" in sql and params.get("env_1") == "local"


# ---------------------------------------------------------------------------
# 删除报告联动取消
# ---------------------------------------------------------------------------


async def test_cancel_jobs_of_report_cancels_active_and_skips_terminated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report_id = uuid.uuid4()
    active = _job(status="parsing")
    ready = _job(status="ready")
    session = _CaptureSession([active, ready])
    cancelled_ids: list[uuid.UUID] = []

    async def _fake_cancel(_session: Any, job_id: uuid.UUID) -> DocGenJob:
        if job_id == ready.id:
            raise BadRequestException("任务已结束，无法取消")
        cancelled_ids.append(job_id)
        return active

    monkeypatch.setattr(doc_gen_service, "cancel_job", _fake_cancel)
    count = await doc_gen_service.cancel_jobs_of_report(session, report_id)  # type: ignore[arg-type]
    assert count == 1
    assert cancelled_ids == [active.id]
    # 查询只筛未终态任务：completed/failed/cancelled 不在取消范围
    sql = str(session.statements[0].compile(compile_kwargs={"literal_binds": True}))
    assert "report_id" in sql
    assert "'completed'" in sql and "'failed'" in sql and "'cancelled'" in sql


async def test_delete_report_cascades_cancel(monkeypatch: pytest.MonkeyPatch) -> None:
    report_id = uuid.uuid4()
    calls: list[str] = []

    async def _fake_cancel_jobs(_session: Any, rid: uuid.UUID) -> int:
        calls.append(f"cancel:{rid}")
        return 2

    async def _fake_repo_delete(_db: Any, rid: uuid.UUID, _user: Any) -> None:
        calls.append(f"delete:{rid}")

    db = _CaptureSession([])
    monkeypatch.setattr(doc_gen_service, "cancel_jobs_of_report", _fake_cancel_jobs)
    monkeypatch.setattr(research_service.repo, "delete_report", _fake_repo_delete)

    await research_service.delete_report(db, report_id)  # type: ignore[arg-type]
    assert calls == [f"cancel:{report_id}", f"delete:{report_id}"]
    assert db.commits == 1
