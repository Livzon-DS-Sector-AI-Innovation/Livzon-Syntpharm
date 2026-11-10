"""模型绑定、任务快照、工具开关与兜底切换的单元测试。

只测对外可观察的行为：给定一段配置字符串，解析出的绑定指向哪份端点与模型；
任务快照是否优先于实时配置；被停用的工具是否既不下发也不可执行；主模型失败时
兜底是否只切一次。
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.llm.exceptions import LLMProviderError, LLMToolsUnsupportedError
from app.modules.research.report_gen import model_binding
from app.modules.research.report_gen.agent import _call_llm, _config_from_snapshot, _ModelSwitch
from app.modules.research.report_gen.config import ReportGenConfig
from app.modules.research.report_gen.model_binding import ModelBinding, resolve_binding, resolve_bindings
from app.modules.research.report_gen.tools import (
    TOOL_NAMES,
    ToolOutcome,
    execute_tool,
    is_tool_enabled,
    resolve_tool_specs,
)


def _named(config_name: str, model_name: str) -> SimpleNamespace:
    """``get_named_config`` 返回值的最小替身（只用两个字段）。"""
    return SimpleNamespace(config_name=config_name, model_name=model_name)


def _config(**overrides: object) -> ReportGenConfig:
    base: dict[str, object] = {
        "model": ModelBinding(),
        "fallback_model": ModelBinding(),
        "structure_model": ModelBinding(),
        "tool_mode": "auto",
        "disabled_tools": frozenset(),
        "max_rounds": 16,
        "llm_timeout_seconds": 180.0,
        "tool_timeout_seconds": 60.0,
        "job_timeout_seconds": 2400.0,
        "kb_top_k": 6,
        "max_steps": 400,
        "agent_prompt": "agent",
        "structure_prompt": "structure",
        "examples_enabled": False,
        "examples_limit": 0,
    }
    base.update(overrides)
    return ReportGenConfig(**base)  # type: ignore[arg-type]


class _Steps:
    """``_call_llm`` 只写一条 status 步骤，用记名字的替身即可。"""

    def __init__(self) -> None:
        self.records: list[tuple[str, str, str]] = []

    async def add(self, kind: str, title: str, *, status: str = "ok", **_: object) -> None:
        self.records.append((kind, title, status))


# ─── 绑定解析 ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_blank_setting_keeps_active_model() -> None:
    binding = await resolve_binding("   ")
    assert binding.is_empty is True
    assert binding.call_kwargs() == {"config_name": None, "model_override": None}


@pytest.mark.asyncio
async def test_registered_config_name_switches_whole_config(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake(_name: str, _config_type: str) -> SimpleNamespace:
        return _named("qwen-prod", "qwen3-max")

    monkeypatch.setattr(model_binding, "get_named_config", fake)

    binding = await resolve_binding("qwen-prod")

    assert (binding.config_name, binding.model) == ("qwen-prod", "qwen3-max")
    # 整份切换：只传配置名。model_override 一起传会盖掉配置里的模型名
    assert binding.call_kwargs() == {"config_name": "qwen-prod", "model_override": None}


@pytest.mark.asyncio
async def test_unregistered_value_only_overrides_model(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake(_name: str, _config_type: str) -> None:
        return None

    monkeypatch.setattr(model_binding, "get_named_config", fake)

    binding = await resolve_binding("DeepSeek-V4-Flash")

    assert binding.config_name is None
    assert binding.call_kwargs() == {"config_name": None, "model_override": "DeepSeek-V4-Flash"}


@pytest.mark.asyncio
async def test_structure_slot_reuses_main_binding(monkeypatch: pytest.MonkeyPatch) -> None:
    lookups: list[str] = []

    async def fake(name: str, _config_type: str) -> SimpleNamespace:
        lookups.append(name)
        return _named(name, f"{name}-model")

    monkeypatch.setattr(model_binding, "get_named_config", fake)

    main, structure, fallback = await resolve_bindings("cfg-main", "", "")

    assert structure is main, "结构识别留空时应复用主档，而不是再查一次库"
    assert fallback.is_empty is True
    assert lookups == ["cfg-main"]


# ─── 任务快照 ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_job_snapshot_wins_over_live_config(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake(name: str, _config_type: str) -> SimpleNamespace:
        return _named(name, f"{name}-model")

    monkeypatch.setattr(model_binding, "get_named_config", fake)

    job = SimpleNamespace(
        model_config_name="cfg-old",
        structure_model_name="cfg-old",
        fallback_model_name="cfg-fb",
    )
    live = _config(model=ModelBinding(raw="cfg-live", model="cfg-live"))

    merged = await _config_from_snapshot(job, live)  # type: ignore[arg-type]

    assert merged.model.config_name == "cfg-old"
    assert merged.fallback_model.config_name == "cfg-fb"
    assert merged.tool_mode == "auto", "快照只覆盖模型三档，运行参数沿用实时配置"


@pytest.mark.asyncio
async def test_legacy_job_without_snapshot_keeps_live_config() -> None:
    job = SimpleNamespace(model_config_name=None, structure_model_name=None, fallback_model_name=None)
    live = _config()

    assert await _config_from_snapshot(job, live) is live  # type: ignore[arg-type]


# ─── 工具开关 ──────────────────────────────────────────────────────────────


def test_disabled_tools_are_not_sent_to_model() -> None:
    specs = resolve_tool_specs(frozenset({"mark_gap", "search_knowledge_base"}))
    names = {spec["function"]["name"] for spec in specs}

    assert names == set(TOOL_NAMES) - {"mark_gap", "search_knowledge_base"}


def test_finalize_cannot_be_disabled() -> None:
    assert is_tool_enabled("finalize", frozenset({"finalize"})) is True
    names = {spec["function"]["name"] for spec in resolve_tool_specs(frozenset({"finalize"}))}
    assert "finalize" in names


@pytest.mark.asyncio
async def test_execute_tool_refuses_disabled_tool() -> None:
    called: list[str] = []

    def handler(_arguments: dict[str, object]) -> ToolOutcome:
        called.append("hit")
        return ToolOutcome(ok=True, summary="不该被执行")

    runtime = SimpleNamespace(
        config=SimpleNamespace(disabled_tools=frozenset({"mark_gap"})),
        mark_gap=handler,
    )

    outcome = await execute_tool("mark_gap", {"reason": "缺资料"}, runtime)  # type: ignore[arg-type]

    assert outcome.ok is False
    assert "停用" in outcome.summary
    assert called == [], "禁用必须挡在 handler 之前，而不是执行后再报错"


# ─── 兜底切换 ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_main_model_failure_switches_to_fallback_once() -> None:
    steps = _Steps()
    job = SimpleNamespace(id=uuid4(), used_fallback=False)
    used: list[str | None] = []

    async def call(binding: ModelBinding) -> str:
        used.append(binding.model)
        if binding.model == "slow-model":
            raise LLMProviderError("502 bad gateway")
        return "ok"

    switch = _ModelSwitch(ModelBinding(model="slow-model"), ModelBinding(model="fallback-model"))

    result = await _call_llm(switch, job, steps, call)  # type: ignore[arg-type]

    assert result == "ok"
    assert used == ["slow-model", "fallback-model"]
    assert switch.switched is True
    assert job.used_fallback is True
    assert steps.records[0][0] == "status"
    assert "自动补齐" in steps.records[0][1]


@pytest.mark.asyncio
async def test_fallback_failure_propagates_without_retry_loop() -> None:
    calls: list[str | None] = []
    job = SimpleNamespace(id=uuid4(), used_fallback=False)

    async def boom(binding: ModelBinding) -> str:
        calls.append(binding.model)
        raise LLMProviderError("still down")

    switch = _ModelSwitch(ModelBinding(model="slow"), ModelBinding(model="fallback"))

    with pytest.raises(LLMProviderError):
        await _call_llm(switch, job, _Steps(), boom)  # type: ignore[arg-type]

    assert calls == ["slow", "fallback"], "兜底只切一次，不能在兜底上继续重试"
    assert switch.current is switch.fallback


@pytest.mark.asyncio
async def test_no_fallback_configured_keeps_original_error() -> None:
    async def boom(_binding: ModelBinding) -> str:
        raise LLMProviderError("502")

    job = SimpleNamespace(id=uuid4(), used_fallback=False)
    switch = _ModelSwitch(ModelBinding(model="slow"), ModelBinding())

    with pytest.raises(LLMProviderError):
        await _call_llm(switch, job, _Steps(), boom)  # type: ignore[arg-type]

    assert switch.switched is False
    assert job.used_fallback is False


@pytest.mark.asyncio
async def test_tools_unsupported_is_not_treated_as_model_failure() -> None:
    """协议不支持要抛回上层做 tools→json 降级，不能白白切到兜底模型。"""

    async def unsupported(_binding: ModelBinding) -> str:
        raise LLMToolsUnsupportedError("endpoint rejects tools")

    job = SimpleNamespace(id=uuid4(), used_fallback=False)
    switch = _ModelSwitch(ModelBinding(model="slow"), ModelBinding(model="fallback"))

    with pytest.raises(LLMToolsUnsupportedError):
        await _call_llm(switch, job, _Steps(), unsupported)  # type: ignore[arg-type]

    assert switch.switched is False
    assert job.used_fallback is False


# ─── 运行时配置解析 ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_load_config_normalizes_disabled_tool_list(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.modules.research.report_gen import config as config_module

    values = {
        "REPORT_GEN_DISABLED_TOOLS": " Mark_Gap , search_knowledge_base ",
        "REPORT_GEN_TOOL_MODE": "tools",
    }

    async def fake_setting(_module: str, key: str, default: str = "") -> str:
        return values.get(key, default)

    async def fake_int(_module: str, _key: str, default: int) -> int:
        return default

    async def fake_float(_module: str, _key: str, default: float) -> float:
        return default

    async def fake_bindings(*_args: object, **_kwargs: object) -> tuple[ModelBinding, ModelBinding, ModelBinding]:
        return ModelBinding(), ModelBinding(), ModelBinding()

    monkeypatch.setattr(config_module, "get_module_setting", fake_setting)
    monkeypatch.setattr(config_module, "get_module_setting_int", fake_int)
    monkeypatch.setattr(config_module, "get_module_setting_float", fake_float)
    monkeypatch.setattr(config_module, "resolve_bindings", fake_bindings)

    loaded = await config_module.load_config()

    assert loaded.disabled_tools == frozenset({"mark_gap", "search_knowledge_base"})
    assert loaded.tool_mode == "tools"


def test_probe_failure_detail_never_echoes_provider_text() -> None:
    """连通测试的失败原因会直接显示在配置页，不能带出端点与密钥。"""
    from app.modules.research.report_gen.service import _probe_failure_detail

    exc = LLMProviderError(
        "401 Unauthorized: base_url=https://gw.example.com key=sk-secret-value",
        status_code=401,
    )

    detail = _probe_failure_detail(exc)

    assert "sk-secret-value" not in detail
    assert "gw.example.com" not in detail
    assert "401" in detail
