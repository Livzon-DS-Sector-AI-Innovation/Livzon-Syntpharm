"""任务链路的「不该干就别干」与额度联动测试。

只覆盖两类容易回退的行为：
1. 没有分析对象的阶段必须提前返回（不写状态、不打模型）；
2. 事实抽取的任务内额度随后台富化开关联动（后台接管全库覆盖）。
"""

from __future__ import annotations

import asyncio
import types
import uuid
from typing import Any

import pytest

from app.modules.research.doc_gen import pipeline
from app.modules.research.doc_gen.models import DocGenJob
from app.modules.research.doc_gen.runtime_config import ModelChoice, RuntimeConfig
from app.modules.research.doc_gen.templates import get_template_spec
from app.modules.research.knowledge_base.facts import FactStats


class FakeSession:
    """只关心提交次数与「是否被动过」的假会话。"""

    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


def _ctx() -> pipeline.JobContext:
    return pipeline.JobContext(
        job=DocGenJob(id=uuid.uuid4(), status="extracting", step=""),
        spec=get_template_spec("tech_research_report"),
        files=[],
    )


async def test_file_analysis_skipped_without_task_files(monkeypatch: pytest.MonkeyPatch) -> None:
    """没有任务级资料文件（知识库模式）时，文件分析一个模型调用都不该发生。"""
    called: list[Any] = []

    async def _fake_analyze(*args: Any, **kwargs: Any) -> Any:
        called.append(True)

    monkeypatch.setattr(pipeline, "analyze_files", _fake_analyze)
    session = FakeSession()
    ctx = _ctx()

    await pipeline._file_analysis_stage(session, ctx, RuntimeConfig(file_analysis_enabled=True))

    assert called == []
    assert session.commits == 0  # 连状态写都不做


async def test_stage_timer_accumulates_per_name() -> None:
    """阶段计时：同名阶段多次执行要累加（提取分骨架/章节两轮），不同名互不影响。"""
    ctx = _ctx()
    async with pipeline._stage_timer(ctx, "extract"):
        await asyncio.sleep(0.06)
    async with pipeline._stage_timer(ctx, "extract"):
        await asyncio.sleep(0.06)
    first = ctx.timings["extract"]
    async with pipeline._stage_timer(ctx, "render"):
        pass

    assert first > 0
    assert set(ctx.timings) == {"extract", "render"}
    assert ctx.timings["extract"] == first


def test_process_notes_report_probe_refs_and_table_rows() -> None:
    """生成说明的过程留痕：补问/引用编号复核/表格未核对行都要写给使用者看。"""
    from app.modules.research.doc_gen.extraction import ExtractStats

    ctx = _ctx()
    ctx.probe_recovered = 2
    ctx.extract_stats = ExtractStats(refs_rescued=1, table_rows_unverified=3)

    notes = pipeline._process_notes(ctx)

    assert any("定向补问补上 2 项" in note for note in notes)
    assert any("引用编号复核救回 1 项" in note for note in notes)
    assert any("3 行未能核对" in note for note in notes)


async def test_fact_extract_limit_follows_background_enrich(monkeypatch: pytest.MonkeyPatch) -> None:
    """后台富化启用时任务内额度缩到 inline 上限；关闭时用完整额度。"""
    captured: dict[str, Any] = {}

    async def _fake_extract(session: Any, kb: Any, **kwargs: Any) -> FactStats:
        captured.update(kwargs)
        return FactStats()

    async def _fake_kb_row(session: Any, ctx: Any) -> Any:
        return types.SimpleNamespace(id="kb-1", name="测试库")

    async def _resolve(name: str, purpose: str = "text") -> ModelChoice:
        return ModelChoice()

    monkeypatch.setattr("app.modules.research.knowledge_base.facts.extract_facts", _fake_extract)
    monkeypatch.setattr(pipeline, "_project_kb_row", _fake_kb_row)
    monkeypatch.setattr(pipeline, "resolve_model", _resolve)

    await pipeline._fact_extract_stage(
        FakeSession(),
        _ctx(),
        RuntimeConfig(kb_background_enrich_enabled=True, inline_fact_max_chunks=60, fact_extract_max_chunks=200),
    )
    assert captured["max_chunks"] == 60

    await pipeline._fact_extract_stage(
        FakeSession(),
        _ctx(),
        RuntimeConfig(kb_background_enrich_enabled=False, inline_fact_max_chunks=60, fact_extract_max_chunks=200),
    )
    assert captured["max_chunks"] == 200
