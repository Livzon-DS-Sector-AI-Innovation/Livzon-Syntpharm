"""_parse_stage 逐文件容错与进度展示的单测（不依赖数据库与对象存储）。

背景：某个资料文件解析失败时必须继续解析下一个文件，不能拖垮整个任务；
同时 job.step 要带上当前正在解析的文件名，供前端轮询展示。
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.modules.research.doc_gen import pipeline
from app.modules.research.doc_gen import repository as docgen_repo
from app.modules.research.doc_gen.cancellation import AbortHandle


def _record(name: str) -> Any:
    """DocGenInputFile 的最小替身（_parse_stage 只读写这些属性）。"""
    return SimpleNamespace(
        job_id="job-1",
        file_id=f"f-{name}",
        object_key=f"obj/{name}",
        original_filename=name,
        mime_type="",
        role="material",
        page_count=0,
        char_count=0,
        parse_status="pending",
        warnings=None,
    )


def _ctx() -> Any:
    job = SimpleNamespace(id="job-1", status="pending", step="排队中", progress=0)
    return SimpleNamespace(job=job, files=[_record("bad.pdf"), _record("good.pdf")], blocks=[], warnings=[])


def _patch(monkeypatch: pytest.MonkeyPatch, parse_one: Any) -> None:
    monkeypatch.setattr(pipeline, "_parse_one", parse_one)
    monkeypatch.setattr(docgen_repo, "cancel_requested", AsyncMock(return_value=False))


def _session_and_config() -> tuple[Any, Any]:
    session = SimpleNamespace(commit=AsyncMock())
    config = SimpleNamespace(
        max_total_pages=100,
        parse_timeout_seconds=30,
        max_pages_per_file=500,
        max_ocr_pages_per_file=50,
        parse_concurrency=1,
    )
    return session, config


async def test_single_file_error_continues_with_next(monkeypatch: pytest.MonkeyPatch) -> None:
    """某个文件解析抛异常：标记 failed 并记录告警，继续解析下一个文件。"""

    async def fake_parse_one(
        record: Any, config: Any, handle: AbortHandle | None = None
    ) -> tuple[list[Any], list[str], int]:
        if record.original_filename == "bad.pdf":
            raise RuntimeError("boom")
        record.page_count = 3
        record.char_count = 120
        record.parse_status = "done"
        return ["块"], [], 3

    _patch(monkeypatch, fake_parse_one)
    ctx = _ctx()
    session, config = _session_and_config()

    await pipeline._parse_stage(session, ctx, config, handle=None)

    assert ctx.files[0].parse_status == "failed"
    assert ctx.files[0].warnings is not None and "解析异常" in ctx.files[0].warnings[0]
    assert ctx.files[1].parse_status == "done"
    assert any("bad.pdf" in warning for warning in ctx.warnings)
    assert ctx.job.status == "parsing"
    assert ctx.job.step.startswith("解析资料 2/2：good.pdf")
    assert ctx.job.progress == 20  # 5 + 15 * 2/2


async def test_all_files_failed_raises_no_text_with_names(monkeypatch: pytest.MonkeyPatch) -> None:
    """全部文件都失败时才报 no_text，且错误信息要指出失败文件。"""

    async def fake_parse_one(
        record: Any, config: Any, handle: AbortHandle | None = None
    ) -> tuple[list[Any], list[str], int]:
        record.parse_status = "failed"
        return [], [], 0

    _patch(monkeypatch, fake_parse_one)
    ctx = _ctx()
    session, config = _session_and_config()

    with pytest.raises(pipeline.JobAbortedError) as exc_info:
        await pipeline._parse_stage(session, ctx, config, handle=None)

    assert exc_info.value.code == "no_text"
    assert "bad.pdf" in exc_info.value.message
    assert "good.pdf" in exc_info.value.message


async def test_step_truncated_to_column_width(monkeypatch: pytest.MonkeyPatch) -> None:
    """step 列宽 64：长文件名拼接后必须截断，避免落库报错。"""

    async def fake_parse_one(
        record: Any, config: Any, handle: AbortHandle | None = None
    ) -> tuple[list[Any], list[str], int]:
        record.parse_status = "done"
        return ["块"], [], 1

    _patch(monkeypatch, fake_parse_one)
    ctx = _ctx()
    ctx.files = [_record("超长文件名示例" * 12 + ".pdf")]
    session, config = _session_and_config()

    await pipeline._parse_stage(session, ctx, config, handle=None)

    assert ctx.job.step.startswith("解析资料 1/1：")
    assert len(ctx.job.step) <= 64



