"""worker 并发行为：按 max_concurrency 补满槽位；领不到就停手。

跨进程闸门在 `repo.claim_next_job` 里（按租约统计运行中任务数），这里只钉住 worker 侧
的两个动作：补满到配置的并发度、领不到任务时不空转。
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.modules.research.doc_gen import worker
from app.modules.research.doc_gen.runtime_config import RuntimeConfig


async def test_pump_fills_slots_up_to_capacity(monkeypatch: pytest.MonkeyPatch) -> None:
    """并发度 3 → 一次补满 3 个在跑任务，一个不多一个不少。"""
    started: list[str] = []

    async def _claim(_config: RuntimeConfig) -> Any:
        return f"job-{len(started) + 1}"

    async def _execute(job_id: Any, _config: RuntimeConfig) -> str:
        started.append(str(job_id))
        await asyncio.sleep(0.2)
        return "completed"

    monkeypatch.setattr(worker, "_claim", _claim)
    monkeypatch.setattr(worker, "_execute_guarded", _execute)

    running: set[asyncio.Task[Any]] = set()
    await worker._pump(running, RuntimeConfig(max_concurrency=3))
    assert len(running) == 3

    for task in running:
        task.cancel()
    await asyncio.gather(*running, return_exceptions=True)


async def test_pump_serial_when_capacity_is_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """默认（并发度 1）与串行行为完全一致：只跑一个任务。"""

    async def _claim(_config: RuntimeConfig) -> Any:
        return "job-1"

    async def _execute(_job_id: Any, _config: RuntimeConfig) -> str:
        await asyncio.sleep(0.2)
        return "completed"

    monkeypatch.setattr(worker, "_claim", _claim)
    monkeypatch.setattr(worker, "_execute_guarded", _execute)

    running: set[asyncio.Task[Any]] = set()
    await worker._pump(running, RuntimeConfig(max_concurrency=1))
    assert len(running) == 1

    for task in running:
        task.cancel()
    await asyncio.gather(*running, return_exceptions=True)


async def test_pump_stops_when_claim_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """没有可领的任务（或已达跨进程闸门）时立即停手，不空转重试。"""
    calls = {"claim": 0}

    async def _claim(_config: RuntimeConfig) -> Any:
        calls["claim"] += 1
        return None

    async def _execute(_job_id: Any, _config: RuntimeConfig) -> str:  # pragma: no cover - 不该被调用
        return "completed"

    monkeypatch.setattr(worker, "_claim", _claim)
    monkeypatch.setattr(worker, "_execute_guarded", _execute)

    running: set[asyncio.Task[Any]] = set()
    await worker._pump(running, RuntimeConfig(max_concurrency=3))

    assert running == set()
    assert calls["claim"] == 1
