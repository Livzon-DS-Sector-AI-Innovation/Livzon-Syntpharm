"""后台富化 worker 测试：有活干活、没活休眠、开关关闭不查库。"""

from __future__ import annotations

import types
from typing import Any

import pytest

from app.modules.research.doc_gen.runtime_config import ModelChoice, RuntimeConfig
from app.modules.research.knowledge_base import enrich_worker
from app.modules.research.knowledge_base.facts import FactStats, IndexStats


class _FakeSession:
    """只要求能被 async with 使用（worker 通过 async_session_factory 取 session）。"""

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, *exc: Any) -> bool:
        return False

    async def commit(self) -> None:
        """_extract_round 成功路径会提交；替身只需可调用（不落库）。"""

    async def rollback(self) -> None:
        """失败路径会回滚；替身只需可调用，避免刷出误导性的异常日志。"""


def _patch(
    monkeypatch: pytest.MonkeyPatch,
    *,
    enabled: bool = True,
    pending: int = 0,
    busy: bool = False,
    extract_stats: FactStats | None = None,
    index_stats: IndexStats | None = None,
) -> dict[str, list[Any]]:
    """把 session 工厂、配置、知识库扫描与两轮执行全替换成离线替身。"""
    calls: dict[str, list[Any]] = {"active_kbs": [], "extract": [], "index": []}
    kb = types.SimpleNamespace(id="kb-1")

    async def _busy_with_generation(_session: Any) -> bool:
        return busy

    monkeypatch.setattr(enrich_worker, "_busy_with_generation", _busy_with_generation)

    async def _config() -> RuntimeConfig:
        return RuntimeConfig(kb_background_enrich_enabled=enabled)

    async def _active(_session: Any) -> list[Any]:
        calls["active_kbs"].append(True)
        return [kb]

    async def _pending(_session: Any, _kb_id: Any) -> int:
        return pending

    async def _extract(_session: Any, target: Any, _config: RuntimeConfig, **_kwargs: Any) -> FactStats:
        calls["extract"].append(target.id)
        return extract_stats or FactStats(chunks_done=1, facts_added=2)

    async def _index(_session: Any, target: Any, _config: RuntimeConfig, **_kwargs: Any) -> IndexStats:
        calls["index"].append(target.id)
        return index_stats or IndexStats()

    monkeypatch.setattr("app.core.database.async_session_factory", _FakeSession)
    monkeypatch.setattr(enrich_worker, "load_runtime_config", _config)
    monkeypatch.setattr(enrich_worker, "_active_kbs", _active)
    monkeypatch.setattr(enrich_worker, "_pending_fact_chunks", _pending)
    monkeypatch.setattr(enrich_worker, "_extract_round", _extract)
    monkeypatch.setattr(enrich_worker, "_index_round", _index)
    return calls


async def test_disabled_switch_skips_everything(monkeypatch: pytest.MonkeyPatch) -> None:
    """开关关闭时一轮都不跑，也不去查知识库。"""
    calls = _patch(monkeypatch, enabled=False)
    assert await enrich_worker.run_once() is False
    assert calls == {"active_kbs": [], "extract": [], "index": []}


async def test_extract_round_wins_when_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    """有待抽切片时优先抽事实，不再重复摸底。"""
    calls = _patch(monkeypatch, pending=5)
    assert await enrich_worker.run_once() is True
    assert calls["extract"] == ["kb-1"]
    assert calls["index"] == []


async def test_index_round_discovers_new_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    """没有待抽切片时轮转摸底：发现新增切片也算干了实事（下一轮就会去抽它）。"""
    calls = _patch(monkeypatch, index_stats=IndexStats(chunks_added=3, pending_facts=3))
    assert await enrich_worker.run_once() is True
    assert calls["index"] == ["kb-1"]
    assert calls["extract"] == []


async def test_idle_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """既没有待抽切片、摸底也没有任何变化时，返回 False 让循环去休眠。"""
    _patch(monkeypatch)
    assert await enrich_worker.run_once() is False


async def test_extract_round_yields_when_generation_is_running(monkeypatch: pytest.MonkeyPatch) -> None:
    """有生成任务在跑：后台事实抽取降到让路额度与并发 1；空闲时恢复完整额度。"""
    captured: dict[str, Any] = {}

    async def _fake_extract(_session: Any, _kb: Any, **kwargs: Any) -> FactStats:
        captured.update(kwargs)
        return FactStats()

    async def _resolve(_name: str, purpose: str = "text") -> ModelChoice:
        return ModelChoice()

    monkeypatch.setattr("app.modules.research.knowledge_base.facts.extract_facts", _fake_extract)
    monkeypatch.setattr(enrich_worker, "resolve_model", _resolve)

    kb = types.SimpleNamespace(id="kb-1")
    config = RuntimeConfig(kb_background_enrich_max_chunks=200, fact_extract_concurrency=4)

    await enrich_worker._extract_round(_FakeSession(), kb, config, busy=True)
    assert captured["max_chunks"] == enrich_worker.BUSY_EXTRACT_LIMIT
    assert captured["concurrency"] == 1

    await enrich_worker._extract_round(_FakeSession(), kb, config, busy=False)
    assert captured["max_chunks"] == 200
    # 空闲时并发 = min(代码硬顶, 配置)：这里配置 4 小于硬顶，故取配置值
    assert captured["concurrency"] == min(enrich_worker.MAX_CONCURRENCY, config.fact_extract_concurrency)
