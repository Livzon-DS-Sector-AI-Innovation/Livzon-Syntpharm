"""模板分析测试：抽取指引 + 需求描述（template_structure v2）的生成与回写（假模型）。"""

from __future__ import annotations

from typing import Any

from app.modules.research.doc_gen.template_analyzer import (
    TemplateAnalysisOut,
    TemplateAnalysisResult,
    analyze_template,
    apply_requirements_to_spec,
)
from app.modules.research.doc_gen.template_spec import TemplateSpec
from app.modules.research.doc_gen.templates import get_template_spec


class FakeLLM:
    """按脚本返回预设响应（这里只关心需求描述字段的解析与归一）。"""

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self._responses = responses

    async def chat_json(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        return self._responses[0]


def _spec() -> TemplateSpec:
    """取一份独立副本：模板 registry 里是单例，直接改槽位会污染其它测试。"""
    return get_template_spec("tech_research_report").model_copy(deep=True)


def _analysis(requirements: dict[str, dict[str, Any]]) -> TemplateAnalysisResult:
    return TemplateAnalysisResult(requirements=requirements)


async def test_analyze_template_collects_requirements() -> None:
    """模型给出的需求描述被收集，并对随机写法归一（multiple→one_or_more、kb→project_kb）。"""
    llm = FakeLLM(
        [
            {
                "slots": [
                    {
                        "key": "originator",
                        "key_indicators": ["原研企业"],
                        "unit": "mg",
                        "enum_values": "是，否",
                        "cardinality": "multiple",
                        "source_scope": "kb",
                    }
                ]
            }
        ]
    )
    analysis = await analyze_template(_spec(), llm=llm)
    req = analysis.requirements["originator"]
    assert req["unit"] == "mg"
    assert req["enum_values"] == ["是", "否"]
    assert req["cardinality"] == "one_or_more"
    assert req["source_scope"] == "project_kb"


async def test_analyze_template_defaults_when_model_stays_silent() -> None:
    """模型只给指引不给需求描述时，需求描述全为保守默认（不约束）。"""
    llm = FakeLLM([{"slots": [{"key": "originator", "key_indicators": ["原研企业"]}]}])
    analysis = await analyze_template(_spec(), llm=llm)
    req = analysis.requirements["originator"]
    assert req == {"unit": "", "enum_values": [], "cardinality": "single", "source_scope": "any"}


async def test_analyze_template_tolerates_invalid_requirement_values() -> None:
    """非法枚举值不导致整体失败：退回保守默认，其余槽位照常解析。"""
    llm = FakeLLM(
        [
            {
                "slots": [
                    {"key": "originator", "cardinality": "1~N", "source_scope": "随便写的"},
                    {"key": "spec", "enum_values": "片剂/胶囊", "unit": ["℃", "mg"]},
                ]
            }
        ]
    )
    analysis = await analyze_template(_spec(), llm=llm)
    assert analysis.failed is False
    assert analysis.requirements["originator"]["cardinality"] == "single"
    assert analysis.requirements["originator"]["source_scope"] == "any"
    assert analysis.requirements["spec"]["enum_values"] == ["片剂", "胶囊"]
    assert analysis.requirements["spec"]["unit"] == "℃、mg"


async def test_analyze_template_accepts_parsed_payload() -> None:
    """直接喂已解析模型也能构造出需求描述（供离线回放）。"""
    out = TemplateAnalysisOut.model_validate(
        {"slots": [{"key": "originator", "unit": "mg/mL", "cardinality": "one or more"}]}
    )
    assert out.slots[0].cardinality == "one_or_more"
    assert out.slots[0].unit == "mg/mL"


def test_apply_requirements_fills_defaults_only() -> None:
    """只补保守默认值：AI 结论写入空槽位，人工已声明的约束不被覆盖。"""
    spec = _spec()
    by_key = {slot.key: slot for slot in spec.slots}
    by_key["product_spec"].unit = "mg"  # 人工已声明
    analysis = _analysis(
        {
            "originator": {
                "unit": "mg",
                "enum_values": ["是", "否"],
                "cardinality": "single",
                "source_scope": "any",
            },
            "product_spec": {"unit": "℃", "enum_values": [], "cardinality": "single", "source_scope": "any"},
            "not_exists": {"unit": "kg", "enum_values": [], "cardinality": "single", "source_scope": "any"},
        }
    )

    applied = apply_requirements_to_spec(spec, analysis)

    assert applied == 1
    assert by_key["originator"].unit == "mg"
    assert by_key["originator"].enum_values == ["是", "否"]
    assert by_key["product_spec"].unit == "mg"  # 保持人工声明
    assert all(slot.source_scope == "any" for slot in spec.slots)


def test_apply_requirements_skips_all_default() -> None:
    """全默认的需求描述既不写入也不计数。"""
    spec = _spec()
    analysis = _analysis(
        {"originator": {"unit": "", "enum_values": [], "cardinality": "single", "source_scope": "any"}}
    )
    assert apply_requirements_to_spec(spec, analysis) == 0
