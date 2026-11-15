"""Agent 工具链与工具调用协议解析的单元测试。

覆盖三件事：工具集合是封闭且声明完整的、工具分发把异常收敛成失败步骤、
模型返回的 tool_calls 能被规范化（含参数坏掉的降级路径）。
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest

from app.core.llm.client import LLMToolCall, _load_arguments, _looks_like_tools_unsupported, _parse_tool_response
from app.core.llm.exceptions import LLMOutputError
from app.modules.research.report_gen.agent import _coverage_percent, _StepWriter, resolve_initial_mode
from app.modules.research.report_gen.prompts import with_human_locked_summary, with_opinion_digest
from app.modules.research.report_gen.tools import (
    TOOL_NAMES,
    TOOL_SPECS,
    ReportGenRuntime,
    ToolOutcome,
    execute_tool,
)

EXPECTED_TOOLS = {
    "read_template_outline",
    "read_project_context",
    "search_knowledge_base",
    "write_paragraph",
    "write_cell",
    "append_paragraph",
    "append_table_rows",
    "append_references",
    "finalize",
}


def _runtime(**handlers: object) -> SimpleNamespace:
    """工具分发只按属性取函数，用鸭子类型的假 runtime 即可。"""
    return SimpleNamespace(**handlers)


def test_auto_mode_tries_tools_protocol_first() -> None:
    """默认 auto 必须先走 tools；退回 JSON 只应发生在显式 json 或 tools 不被支持时。"""
    assert resolve_initial_mode("auto") == "tools"
    assert resolve_initial_mode("tools") == "tools"
    assert resolve_initial_mode("json") == "json"


def test_tool_specs_are_complete_and_closed() -> None:
    assert set(TOOL_NAMES) == EXPECTED_TOOLS
    assert len(TOOL_NAMES) == len(set(TOOL_NAMES))
    for spec in TOOL_SPECS:
        assert spec["type"] == "function"
        function = spec["function"]
        assert function["name"] in EXPECTED_TOOLS
        assert function["description"]
        assert function["parameters"]["type"] == "object"


@pytest.mark.asyncio
async def test_execute_tool_supports_async_and_sync_handlers() -> None:
    async def async_handler(arguments: dict[str, object]) -> ToolOutcome:
        return ToolOutcome(ok=True, summary=f"async:{arguments['q']}", payload={"echo": arguments["q"]})

    def sync_handler(arguments: dict[str, object]) -> ToolOutcome:
        return ToolOutcome(ok=True, summary=f"sync:{arguments['q']}", payload={})

    runtime = _runtime(read_template_outline=async_handler, finalize=sync_handler)

    first = await execute_tool("read_template_outline", {"q": "母本"}, runtime)  # type: ignore[arg-type]
    second = await execute_tool("finalize", {"q": "收尾"}, runtime)  # type: ignore[arg-type]

    assert first.ok is True
    assert first.summary == "async:母本"
    assert second.ok is True
    assert second.summary == "sync:收尾"


@pytest.mark.asyncio
async def test_unknown_tool_is_a_failed_step_not_an_exception() -> None:
    outcome = await execute_tool("delete_database", {}, _runtime())  # type: ignore[arg-type]
    assert outcome.ok is False
    assert "未知工具" in outcome.summary


@pytest.mark.asyncio
async def test_missing_required_argument_short_circuits_before_handler() -> None:
    """模型发空参数调用时不进 handler，直接点明缺哪些必填项。"""
    called: list[dict[str, object]] = []

    def handler(arguments: dict[str, object]) -> ToolOutcome:
        called.append(arguments)
        return ToolOutcome(ok=True, summary="不该被调用")

    runtime = _runtime(write_paragraph=handler)

    outcome = await execute_tool("write_paragraph", {}, cast(Any, runtime))

    assert outcome.ok is False
    assert "items" in outcome.summary
    assert outcome.payload["required"] == ["items"]
    assert called == []


@pytest.mark.asyncio
async def test_tool_exception_is_swallowed_into_failed_outcome() -> None:
    async def boom(arguments: dict[str, object]) -> ToolOutcome:
        raise RuntimeError("知识库不可用")

    outcome = await execute_tool(
        "search_knowledge_base", {"query": "合成路线"}, cast(Any, _runtime(search_knowledge_base=boom))
    )
    assert outcome.ok is False
    assert "知识库不可用" in outcome.summary
    assert outcome.payload["error"] == "知识库不可用"


def test_parse_tool_response_normalizes_calls() -> None:
    payload = {
        "choices": [
            {
                "finish_reason": "tool_calls",
                "message": {
                    "content": "我先看模板",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "function": {"name": "read_template_outline", "arguments": '{"limit": 40}'},
                        }
                    ],
                },
            }
        ]
    }

    response = _parse_tool_response(payload)

    assert response.content == "我先看模板"
    assert response.finish_reason == "tool_calls"
    assert len(response.tool_calls) == 1
    call = response.tool_calls[0]
    assert isinstance(call, LLMToolCall)
    assert call.name == "read_template_outline"
    assert call.arguments == {"limit": 40}
    assert call.parse_error is None


def test_parse_tool_response_keeps_broken_arguments_as_raw_text() -> None:
    payload = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {"id": "c1", "function": {"name": "fill_slot", "arguments": "{不是 JSON"}},
                    ]
                }
            }
        ]
    }

    response = _parse_tool_response(payload)

    assert response.tool_calls[0].arguments == {}
    assert response.tool_calls[0].arguments_raw == "{不是 JSON"
    assert response.tool_calls[0].parse_error is not None


def test_parse_tool_response_missing_message_raises() -> None:
    with pytest.raises(LLMOutputError):
        _parse_tool_response({"choices": []})


@pytest.mark.parametrize(
    ("raw", "expected_arguments", "has_error"),
    [
        ("", {}, False),
        ('{"slot_key": "drug_name"}', {"slot_key": "drug_name"}, False),
        ("[1, 2]", {}, True),
        ("not json", {}, True),
    ],
)
def test_load_arguments_handles_empty_invalid_and_non_object(
    raw: str, expected_arguments: dict[str, object], has_error: bool
) -> None:
    arguments, error = _load_arguments(raw)
    assert arguments == expected_arguments
    assert (error is not None) is has_error


@pytest.mark.parametrize(
    ("error_text", "supported"),
    [
        ('{"error": {"message": "tools is not supported"}}', True),
        ("This model does not support tool calling", True),
        ("response_format is not supported", True),
        ("invalid request: model not found", False),
        ("rate limit exceeded", False),
    ],
)
def test_tools_unsupported_detection(error_text: str, supported: bool) -> None:
    assert _looks_like_tools_unsupported(error_text) is supported


def _patched_search(
    monkeypatch: pytest.MonkeyPatch,
    calls: list[tuple[str, int]],
    counts: dict[str, int],
) -> Any:
    """造一个只跑检索预算逻辑的 runtime：三个检索源都换成记录调用的假实现。

    ``counts`` 指定每个源最多返回几条，用来观察预算怎么分配。
    """
    runtime: Any = object.__new__(ReportGenRuntime)

    async def facts(kb: object, query: str, top_k: int) -> list[dict[str, Any]]:
        calls.append(("facts", top_k))
        return [{"content": f"fact{index}"} for index in range(min(top_k, counts.get("facts", 0)))]

    async def remote(kb: object, query: str, top_k: int) -> list[dict[str, Any]]:
        calls.append(("remote", top_k))
        return [{"content": f"chunk{index}"} for index in range(min(top_k, counts.get("remote", 0)))]

    async def local(kb: object, query: str, top_k: int) -> list[dict[str, Any]]:
        calls.append(("local", top_k))
        return [{"content": f"local{index}"} for index in range(min(top_k, counts.get("local", 0)))]

    monkeypatch.setattr(runtime, "_search_facts", facts, raising=False)
    monkeypatch.setattr(runtime, "_search_chunks_remote", remote, raising=False)
    monkeypatch.setattr(runtime, "_search_chunks_local", local, raising=False)
    return runtime


@pytest.mark.asyncio
async def test_search_budget_reserves_half_for_remote_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    """事实库不能吃满预算：查询带品种名时会把远程切片挤掉，正文就只能留空。"""
    calls: list[tuple[str, int]] = []
    runtime = _patched_search(monkeypatch, calls, {"facts": 99, "remote": 99})

    items = await runtime._search_one(object(), "米诺地尔 合成路线 工艺", 6)  # noqa: SLF001

    assert calls == [("facts", 3), ("remote", 3)]
    assert len(items) == 6


def test_opinion_digest_is_appended_as_writing_requirements() -> None:
    prompt = with_opinion_digest("基础提示词", "1. 结果必须写因果")

    assert prompt.startswith("基础提示词")
    assert "【历史评审意见汇总" in prompt
    assert "1. 结果必须写因果" in prompt
    # 空汇总不产生空标题：否则每份报告都多一段无内容提示
    assert with_opinion_digest("基础提示词", "  ") == "基础提示词"


def test_human_locked_summary_lists_positions_without_values() -> None:
    prompt = with_human_locked_summary("基础提示词", ["正文第2段", "表1第2行第2列"])

    assert "【本次沿用上一版人工确认内容的位置" in prompt
    assert "正文第2段、表1第2行第2列" in prompt
    assert with_human_locked_summary("基础提示词", []) == "基础提示词"


@pytest.mark.asyncio
async def test_search_budget_falls_back_to_local_chunks_when_both_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """事实库与 RAGFlow 都没命中时，本地切片仍按完整预算兜底。"""
    calls: list[tuple[str, int]] = []
    runtime = _patched_search(monkeypatch, calls, {"facts": 0, "remote": 0, "local": 99})

    items = await runtime._search_one(object(), "米诺地尔 合成路线", 6)  # noqa: SLF001

    assert calls == [("facts", 3), ("remote", 6), ("local", 6)]
    assert len(items) == 6


class _FakeSession:
    """只记录写入与事务次数：轨迹批量化后，commit 次数就是回归口径。"""

    def __init__(self) -> None:
        self.added: list[object] = []
        self.flushes = 0
        self.commits = 0

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        self.flushes += 1

    async def commit(self) -> None:
        self.commits += 1


def _writer() -> tuple[_StepWriter, _FakeSession, SimpleNamespace]:
    session = _FakeSession()
    job = SimpleNamespace(id=uuid4(), current_step="", progress=0)
    return _StepWriter(cast(Any, session), cast(Any, job), max_steps=400), session, job


async def test_step_writer_no_longer_commits_per_trace() -> None:
    """一条轨迹只 flush，不单独开事务：否则一轮 10 次写入就是 20+ 次事务往返。"""
    writer, session, _job = _writer()

    await writer.add("status", "任务开始")
    await writer.add("tool_call", "调用 write_paragraph", tool_name="write_paragraph")

    assert session.flushes == 2
    assert session.commits == 0

    await writer.commit_pending()
    assert session.commits == 1


async def test_progress_throttled_skips_small_delta_within_interval() -> None:
    """写工具批内连写多处：增幅与间隔都不够时不落库，够大才落库。"""
    writer, session, job = _writer()

    assert await writer.progress_throttled("写入资料到文档 · 已写 1/10 处", 15) is True
    assert await writer.progress_throttled("写入资料到文档 · 已写 1/10 处", 16) is False
    assert await writer.progress_throttled("写入资料到文档 · 已写 5/10 处", 50) is True

    assert session.commits == 2
    assert job.progress == 50


def test_coverage_percent_leaves_headroom_for_rendering() -> None:
    """覆盖率映射到 5%~90%：最后 10% 留给出稿归档，进度条不会在出稿前打满。"""
    assert _coverage_percent({"writable_total": 0, "written": 0}) == 5
    assert _coverage_percent({"writable_total": 10, "written": 0}) == 5
    assert _coverage_percent({"writable_total": 10, "written": 10}) == 90
