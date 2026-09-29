"""缺口闭环测试：只重试「换一套检索口径还有救」的缺口，且只接受确有提升的结果。

重试是最贵的补救手段（再调一次模型、再打一次知识库），所以这里钉死三件事：
哪些缺口值得重试、重试结果什么算「变好」、一轮无提升必须立刻收手。
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from app.modules.research.doc_gen import gap, pipeline, status
from app.modules.research.doc_gen.extraction import ExtractionAbortError, ExtractStats, SlotResult
from app.modules.research.doc_gen.models import DocGenJob
from app.modules.research.doc_gen.runtime_config import ModelChoice, RuntimeConfig
from app.modules.research.doc_gen.templates import get_template_spec

# 模板里的真实槽位：originator 是普通槽位，tech_opinion 是人工填写项
SLOT_KEY = "originator"
MANUAL_KEY = "tech_opinion"


def _result(key: str, state: str, reason: str = "", text: str = "") -> SlotResult:
    return SlotResult(key=key, text=text, state=state, gap_reason=reason)


def _pending(key: str) -> SlotResult:
    return _result(key, status.STATUS_PENDING, gap.GAP_NO_MATERIAL)


class StubExtractor:
    """按轮次脚本返回结果的假抽取器，记录每轮实际提交的槽位 key。"""

    def __init__(self, rounds: list[dict[str, SlotResult]]) -> None:
        self.stats = ExtractStats()
        self.batches: list[list[str]] = []
        self._rounds = rounds

    async def run(self, *, slots: Any = None, on_progress: Any = None) -> dict[str, SlotResult]:
        self.batches.append([slot.key for slot in (slots or [])])
        return self._rounds.pop(0) if self._rounds else {}


class BrokenExtractor:
    """模拟强制终止：抽取器把取消转成 ExtractionAbortError。"""

    def __init__(self) -> None:
        self.stats = ExtractStats()

    async def run(self, *, slots: Any = None, on_progress: Any = None) -> dict[str, SlotResult]:
        raise ExtractionAbortError("cancelled")


def _session() -> Any:
    """FakeSession 的 Any 视图：_gap_closure_stage 形参标注 AsyncSession，测试替身无需真实协议。"""
    return FakeSession()


class FakeSession:
    """只关心提交次数的假会话（缺口闭环的检查点靠 commit 落进度）。"""

    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


def _patch(monkeypatch: pytest.MonkeyPatch, extractor: Any) -> None:
    """把模型解析、知识库/事实库构造、抽取器构造全部替换成离线替身。"""

    async def _resolve(name: str, purpose: str = "text") -> ModelChoice:
        return ModelChoice()

    async def _no_retriever(*args: Any, **kwargs: Any) -> None:
        return None

    monkeypatch.setattr(pipeline, "resolve_model", _resolve)
    monkeypatch.setattr(pipeline, "_project_kb_retriever", _no_retriever)
    monkeypatch.setattr(pipeline, "_project_fact_retriever", _no_retriever)
    monkeypatch.setattr(pipeline, "_new_extractor", lambda *args, **kwargs: extractor)


def _ctx(results: dict[str, SlotResult]) -> pipeline.JobContext:
    return pipeline.JobContext(
        job=DocGenJob(id=uuid.uuid4(), status="extracting", step=""),
        spec=get_template_spec("tech_research_report"),
        files=[],
        results=results,
    )


# ---- 决策层：归因 → 要不要重试 / 什么算变好 --------------------------------------


def test_every_gap_code_has_a_label() -> None:
    """每个归因都要有中文标签，否则前端只能显示英文常量。"""
    codes = [value for name, value in vars(gap).items() if name.startswith("GAP_") and isinstance(value, str)]
    assert len(codes) >= 10
    assert [code for code in codes if code not in gap.GAP_LABELS] == []


def test_retryable_keys_and_blocked_keys_are_disjoint() -> None:
    """可重试缺口与「交人工」缺口必须互斥且互不遗漏：每条有归因的结果落一边。"""
    results = {
        "a": _result("a", status.STATUS_PENDING, gap.GAP_NO_MATERIAL),
        "b": _result("b", status.STATUS_OK, ""),
        "c": _result("c", status.STATUS_CONFLICT, gap.GAP_CONFLICT),
        "d": _result("d", status.STATUS_MANUAL, gap.GAP_MANUAL),
        "e": _result("e", status.STATUS_FAILED, gap.GAP_MODEL_FAILED),
        "f": _result("f", status.STATUS_NEEDS_VERIFY, gap.GAP_REQUIREMENT),
    }
    assert gap.retryable_keys(results) == ["a", "e"]
    assert gap.blocked_keys(results) == ["c", "d", "f"]


def test_retryable_keys_respect_allowed_scope() -> None:
    """不在本次实例范围内的槽位（动态章节之外的陈旧结果）不得发起重试。"""
    results = {
        "a": _pending("a"),
        "stale": _pending("stale"),
    }
    assert gap.retryable_keys(results, allowed={"a"}) == ["a"]
    assert gap.blocked_keys(results, allowed={"a"}) == []


def test_is_improvement_only_accepts_upgrades() -> None:
    """只有状态真的变高才算提升：同状态与降级都不算。"""
    assert gap.is_improvement(status.STATUS_PENDING, status.STATUS_OK)
    assert gap.is_improvement(status.STATUS_FAILED, status.STATUS_PENDING)
    assert not gap.is_improvement(status.STATUS_PENDING, status.STATUS_PENDING)
    assert not gap.is_improvement(status.STATUS_OK, status.STATUS_NEEDS_VERIFY)
    assert not gap.is_improvement(status.STATUS_OK, status.STATUS_DRAFT)


def test_state_rank_treats_unknown_state_as_lowest() -> None:
    """未登记的状态按最低处理，避免被误判为「有提升」而覆盖掉已知结果。"""
    assert gap.state_rank("brand_new_state") == 0
    assert gap.is_improvement("brand_new_state", status.STATUS_OK)


def test_gap_reasons_counts_by_label() -> None:
    """归因分布按中文标签汇总，供 job.stats 与日志排查。"""
    results = {
        "a": _pending("a"),
        "b": _pending("b"),
        "c": _result("c", status.STATUS_CONFLICT, gap.GAP_CONFLICT),
        "d": _result("d", status.STATUS_OK, ""),
    }
    assert gap.gap_reasons(results) == {gap.GAP_NO_MATERIAL: 2, gap.GAP_CONFLICT: 1}
    stats = gap.GapStats(targets=2, blocked=1, rounds=1, recovered=1, reasons={"资料未命中": 2})
    assert stats.as_job_stats()["gap_recovered"] == 1
    assert stats.as_job_stats()["gap_reasons"] == {"资料未命中": 2}


# ---- 闭环阶段：跑哪些槽位 / 收什么结果 / 什么时候收手 ----------------------------


async def test_stage_retries_gap_slots_and_keeps_improvements(monkeypatch: pytest.MonkeyPatch) -> None:
    """只重试缺口槽位；提升的结果替换原值，冲突项原地不动只记数。"""
    results = {
        SLOT_KEY: _pending(SLOT_KEY),
        "route_1": _result("route_1", status.STATUS_CONFLICT, gap.GAP_CONFLICT, text=status.CONFLICT_MARK),
    }
    extractor = StubExtractor([{SLOT_KEY: _result(SLOT_KEY, status.STATUS_OK, text="AstraZeneca AB")}])
    _patch(monkeypatch, extractor)
    ctx = _ctx(results)
    session: Any = FakeSession()

    await pipeline._gap_closure_stage(session, ctx, RuntimeConfig(gap_retry_rounds=2))

    assert extractor.batches == [[SLOT_KEY]]
    assert ctx.results[SLOT_KEY].state == status.STATUS_OK
    assert ctx.results[SLOT_KEY].text == "AstraZeneca AB"
    assert ctx.results["route_1"].state == status.STATUS_CONFLICT
    assert ctx.gap_stats is not None
    assert (ctx.gap_stats.targets, ctx.gap_stats.blocked, ctx.gap_stats.rounds) == (1, 1, 1)
    assert ctx.gap_stats.recovered == 1
    assert ctx.gap_stats.reasons == {"资料未命中": 1, "材料冲突": 1}
    assert "缺口补齐" in ctx.job.step
    assert session.commits >= 2


async def test_stage_stops_after_a_round_without_improvement(monkeypatch: pytest.MonkeyPatch) -> None:
    """一轮零提升立即收手：换了口径还是没救，再试就是重复烧模型与知识库。"""
    extractor = StubExtractor(
        [
            {SLOT_KEY: _pending(SLOT_KEY)},
            {SLOT_KEY: _result(SLOT_KEY, status.STATUS_OK, text="第二轮才应该拿到")},
        ]
    )
    _patch(monkeypatch, extractor)
    ctx = _ctx({SLOT_KEY: _pending(SLOT_KEY)})

    await pipeline._gap_closure_stage(_session(), ctx, RuntimeConfig(gap_retry_rounds=3))

    assert len(extractor.batches) == 1
    assert ctx.gap_stats is not None
    assert ctx.gap_stats.rounds == 1
    assert ctx.gap_stats.recovered == 0
    assert ctx.results[SLOT_KEY].state == status.STATUS_PENDING


async def test_stage_rejects_weaker_retry_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """重试是补缺口不是刷新内容：更弱的结果不许覆盖原值，也不许算作补齐。"""
    extractor = StubExtractor([{SLOT_KEY: _result(SLOT_KEY, status.STATUS_FAILED, text="模型还是没返回")}])
    _patch(monkeypatch, extractor)
    ctx = _ctx({SLOT_KEY: _pending(SLOT_KEY)})

    await pipeline._gap_closure_stage(_session(), ctx, RuntimeConfig(gap_retry_rounds=2))

    assert ctx.results[SLOT_KEY].state == status.STATUS_PENDING
    assert ctx.gap_stats is not None
    assert ctx.gap_stats.recovered == 0


async def test_stage_respects_round_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """轮数上限是硬约束：配置 1 轮就只允许一次重试。"""
    extractor = StubExtractor([{SLOT_KEY: _result(SLOT_KEY, status.STATUS_NEEDS_VERIFY, text="模糊命中")}])
    _patch(monkeypatch, extractor)
    ctx = _ctx({SLOT_KEY: _pending(SLOT_KEY)})

    await pipeline._gap_closure_stage(_session(), ctx, RuntimeConfig(gap_retry_rounds=1))

    assert len(extractor.batches) == 1
    assert ctx.gap_stats is not None
    assert ctx.gap_stats.rounds == 1


@pytest.mark.parametrize(
    "overrides",
    [{"gap_retry_enabled": False}, {"gap_retry_rounds": 0}],
)
async def test_stage_is_off_when_disabled(monkeypatch: pytest.MonkeyPatch, overrides: dict[str, Any]) -> None:
    """关闭开关或轮数为 0 时一个槽位都不重试（回到「跑一轮就结束」）。"""
    extractor = StubExtractor([{SLOT_KEY: _result(SLOT_KEY, status.STATUS_OK)}])
    _patch(monkeypatch, extractor)
    ctx = _ctx({SLOT_KEY: _pending(SLOT_KEY)})

    await pipeline._gap_closure_stage(_session(), ctx, RuntimeConfig(**overrides))

    assert extractor.batches == []
    assert ctx.gap_stats is not None
    assert ctx.gap_stats.rounds == 0
    assert ctx.results[SLOT_KEY].state == status.STATUS_PENDING


async def test_stage_without_gaps_does_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    """没有缺口时不开抽取器、不花模型调用。"""
    extractor = StubExtractor([])
    _patch(monkeypatch, extractor)
    ctx = _ctx({SLOT_KEY: _result(SLOT_KEY, status.STATUS_OK, text="AstraZeneca AB")})

    await pipeline._gap_closure_stage(_session(), ctx, RuntimeConfig())

    assert extractor.batches == []
    assert ctx.gap_stats is not None
    assert ctx.gap_stats.targets == 0


async def test_stage_merges_retry_stats_into_extract_stats(monkeypatch: pytest.MonkeyPatch) -> None:
    """重试也是真实的模型调用与召回，账必须记在全量统计上，否则失败率会低于实际。"""
    extractor = StubExtractor([{SLOT_KEY: _result(SLOT_KEY, status.STATUS_OK, text="AstraZeneca AB")}])
    extractor.stats.calls = 2
    extractor.stats.fallback_used = 1
    extractor.stats.retrieval_misses = 1
    extractor.stats.warnings.append("模型调用降级")
    _patch(monkeypatch, extractor)
    ctx = _ctx({SLOT_KEY: _pending(SLOT_KEY)})
    ctx.extract_stats = ExtractStats(calls=5)

    await pipeline._gap_closure_stage(_session(), ctx, RuntimeConfig(gap_retry_rounds=1))

    assert ctx.extract_stats.calls == 7
    assert ctx.extract_stats.fallback_used == 1
    assert ctx.extract_stats.retrieval_misses == 1
    assert "模型调用降级" in ctx.warnings


async def test_stage_converts_cancellation_to_job_abort(monkeypatch: pytest.MonkeyPatch) -> None:
    """取消必须能穿透：转成 JobAbortedError 让任务真的停下来，而不是被当成重试失败。"""
    _patch(monkeypatch, BrokenExtractor())
    ctx = _ctx({SLOT_KEY: _pending(SLOT_KEY)})

    with pytest.raises(pipeline.JobAbortedError) as exc:
        await pipeline._gap_closure_stage(_session(), ctx, RuntimeConfig(gap_retry_rounds=2))

    assert exc.value.code == "cancelled"


async def test_stage_skips_when_no_results(monkeypatch: pytest.MonkeyPatch) -> None:
    """没有提取结果（例如解析后直接失败）时不介入。"""
    extractor = StubExtractor([])
    _patch(monkeypatch, extractor)
    ctx = _ctx({})

    await pipeline._gap_closure_stage(_session(), ctx, RuntimeConfig())

    assert extractor.batches == []
    assert ctx.gap_stats is not None
    assert ctx.gap_stats.targets == 0
