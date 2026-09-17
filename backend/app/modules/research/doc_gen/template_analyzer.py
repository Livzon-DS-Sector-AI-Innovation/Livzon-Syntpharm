"""模板分析：用本地模型解析模板结构，输出每个槽位的抽取指引。

在提取阶段之前运行，让模型先「读懂」模板需要什么样的内容，
为后续的文件分析和槽位提取提供精准的指引信号。
分析结果直接写回 spec 实例（search_terms / query_hint 增强），不回写模板库。
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from app.modules.research.doc_gen.prompts import build_template_analysis_prompt
from app.modules.research.doc_gen.template_spec import Slot, TemplateSpec

logger = logging.getLogger(__name__)

_MAX_ANALYSIS_SLOTS = 80


class SlotGuide(BaseModel):
    """单个槽位的抽取指引。"""

    key: str
    key_indicators: list[str] = Field(default_factory=list)
    content_pattern: str = ""
    common_locations: list[str] = Field(default_factory=list)
    quality_criteria: str = ""


class TemplateAnalysisOut(BaseModel):
    """模板分析响应。"""

    slots: list[SlotGuide] = Field(default_factory=list)


@dataclass
class TemplateAnalysisResult:
    """模板分析产物：每槽位的抽取指引 + 增强的检索词。"""

    guides: dict[str, SlotGuide] = field(default_factory=dict)
    # 分析过程中为 search_terms 为空的槽位补的同义词
    enriched_terms: dict[str, list[str]] = field(default_factory=dict)
    analyzed_count: int = 0
    failed: bool = False


def _slot_payload(slot: Slot) -> dict[str, Any]:
    return {
        "key": slot.key,
        "label": slot.label,
        "expects": slot.expects,
        "required": slot.required,
        "query_hint": slot.query_hint,
        "search_terms": list(slot.search_terms),
        "kind": slot.kind,
        "columns": [c.label or c.key for c in slot.columns],
    }


def _analysis_targets(spec: TemplateSpec) -> list[Slot]:
    """需要分析的槽位：非元数据、非人工专用。"""
    return [
        slot
        for slot in spec.slots
        if not slot.from_meta and not slot.manual_only and slot.kind in {"field", "paragraph", "table"}
    ][:_MAX_ANALYSIS_SLOTS]


async def analyze_template(
    spec: TemplateSpec,
    *,
    llm: Any = None,
    timeout_seconds: float | None = None,
    llm_kwargs: Mapping[str, Any] | None = None,
) -> TemplateAnalysisResult:
    """用 LLM 分析模板结构，返回每槽位的抽取指引。

    失败时静默降级返回空结果，不影响任务继续——模板分析是增强项，
    没有它提取阶段仍可正常工作（走原有的关键词检索 + LLM 提取）。
    """
    from app.core.llm import llm_client

    targets = _analysis_targets(spec)
    if not targets:
        return TemplateAnalysisResult()

    payload = [_slot_payload(slot) for slot in targets]
    messages = build_template_analysis_prompt(payload, template_name=spec.name)
    client = llm or llm_client

    try:
        call = client.chat_json(messages, expected_keys=["slots"], temperature=0, **(llm_kwargs or {}))
        raw = await asyncio.wait_for(call, timeout=timeout_seconds) if timeout_seconds else await call
        out = TemplateAnalysisOut.model_validate(raw)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.warning("模板分析失败，跳过（提取阶段将使用默认检索策略）", extra={"error": type(exc).__name__})
        return TemplateAnalysisResult(failed=True)

    # 把分析结果写回 guides 字典
    guides: dict[str, SlotGuide] = {}
    enriched_terms: dict[str, list[str]] = {}
    for guide in out.slots:
        guides[guide.key] = guide
        # 如果 key_indicators 非空且该槽位 search_terms 为空，用 indicators 补检索词
        if guide.key_indicators:
            enriched_terms[guide.key] = [t.strip() for t in guide.key_indicators if t.strip()][:8]

    logger.info(
        "模板分析完成",
        extra={
            "template": spec.name,
            "analyzed": len(guides),
            "enriched_terms": len(enriched_terms),
        },
    )
    return TemplateAnalysisResult(
        guides=guides,
        enriched_terms=enriched_terms,
        analyzed_count=len(guides),
    )


def apply_analysis_to_spec(spec: TemplateSpec, analysis: TemplateAnalysisResult) -> int:
    """把模板分析结果应用到 spec 实例上（增强 search_terms），返回实际增强的槽位数。

    只增强 search_terms 为空的槽位，已有人工配置的检索词不被覆盖。
    """
    applied = 0
    for slot in spec.slots:
        if slot.search_terms or slot.from_meta or slot.manual_only:
            continue
        terms = analysis.enriched_terms.get(slot.key)
        if terms:
            slot.search_terms = terms
            applied += 1
    return applied


__all__ = ["analyze_template", "apply_analysis_to_spec", "TemplateAnalysisResult", "SlotGuide"]
