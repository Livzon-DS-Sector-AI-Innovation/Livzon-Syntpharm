"""AI 槽位检索词标注测试（假模型，不打真实服务）。"""

from __future__ import annotations

from typing import Any

from app.modules.research.doc_gen.spec_enrich import enrich_search_terms, enrich_targets
from app.modules.research.doc_gen.templates import get_template_spec


class FakeLLM:
    """返回预设响应或抛异常。"""

    def __init__(self, response: dict[str, Any] | Exception) -> None:
        self._response = response
        self.calls = 0

    async def chat_json(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        self.calls += 1
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


def _spec() -> Any:
    """独立副本（deep=True），避免污染模板注册表里的缓存对象。"""
    spec = get_template_spec("tech_research_report").model_copy(deep=True)
    for slot in spec.slots:
        slot.search_terms = []
    return spec


async def test_enrich_fills_empty_search_terms_only() -> None:
    """为缺检索词的槽位补同义词；已配置检索词的槽位不被覆盖。"""
    spec = _spec()
    target = next(s for s in spec.slots if s.key == "originator")
    other = next(s for s in spec.slots if s.key == "route_1")
    other.search_terms = ["已有检索词"]
    llm = FakeLLM(
        {
            "slots": [
                {"key": "originator", "search_terms": ["原研厂家", "originator company"]},
                {"key": "route_1", "search_terms": ["新词"]},
            ]
        }
    )
    applied = await enrich_search_terms(spec, llm=llm)
    assert llm.calls == 1
    assert applied == 1
    assert target.search_terms == ["原研厂家", "originator company"]
    assert other.search_terms == ["已有检索词"]


async def test_enrich_targets_excludes_manual_slots() -> None:
    """人工填写槽位不参与 AI 标注。"""
    spec = _spec()
    keys = {s.key for s in enrich_targets(spec)}
    manual = [s for s in spec.slots if s.manual_only]
    assert manual, "模板应存在 manual_only 槽位"
    assert all(s.key not in keys for s in manual)
    assert "originator" in keys


async def test_enrich_degrades_on_model_failure() -> None:
    """模型不可用时静默降级返回 0，槽位保持原样，不抛异常。"""
    spec = _spec()
    llm = FakeLLM(RuntimeError("模型不可用"))
    applied = await enrich_search_terms(spec, llm=llm)
    assert applied == 0
    assert all(not s.search_terms for s in spec.slots)
