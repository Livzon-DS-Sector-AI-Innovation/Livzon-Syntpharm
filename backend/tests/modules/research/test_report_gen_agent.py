"""Agent 工具链与工具调用协议解析的单元测试。

覆盖三件事：工具集合是封闭且声明完整的、工具分发把异常收敛成失败步骤、
模型返回的 tool_calls 能被规范化（含参数坏掉的降级路径）。
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.llm.client import LLMToolCall, _load_arguments, _looks_like_tools_unsupported, _parse_tool_response
from app.core.llm.exceptions import LLMOutputError
from app.modules.research.report_gen.agent import resolve_initial_mode
from app.modules.research.report_gen.tools import TOOL_NAMES, TOOL_SPECS, ToolOutcome, execute_tool

EXPECTED_TOOLS = {
    "read_template_outline",
    "read_project_context",
    "search_knowledge_base",
    "fill_slot",
    "mark_gap",
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

    runtime = _runtime(search_knowledge_base=handler)

    outcome = await execute_tool("search_knowledge_base", {}, runtime)  # type: ignore[arg-type]

    assert outcome.ok is False
    assert "query" in outcome.summary
    assert outcome.payload["required"] == ["query"]
    assert called == []


@pytest.mark.asyncio
async def test_tool_exception_is_swallowed_into_failed_outcome() -> None:
    async def boom(arguments: dict[str, object]) -> ToolOutcome:
        raise RuntimeError("知识库不可用")

    outcome = await execute_tool(  # type: ignore[arg-type]
        "search_knowledge_base", {"query": "合成路线"}, _runtime(search_knowledge_base=boom)
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
