"""模板分析：用本地模型解析模板结构，输出每个槽位的抽取指引。

在提取阶段之前运行，让模型先「读懂」模板需要什么样的内容，
为后续的文件分析和槽位提取提供精准的指引信号。
分析结果直接写回 spec 实例（search_terms / query_hint 增强），不回写模板库。
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.modules.research.doc_gen.prompts import build_template_analysis_prompt
from app.modules.research.doc_gen.template_spec import Cardinality, Slot, SourceScope, TemplateSpec

logger = logging.getLogger(__name__)

_MAX_ANALYSIS_SLOTS = 80

# 模型对「需求描述」的字面写法很随意（``one_or_more`` / ``multiple`` / ``1~N``…）：
# 一律归一到 spec 允许的取值，无法识别时退回保守默认，绝不因为枚举值不规范而整体失败。
_CARDINALITY_ALIASES: dict[str, Cardinality] = {
    "one_or_more": "one_or_more",
    "oneormore": "one_or_more",
    "one_to_many": "one_or_more",
    "multiple": "one_or_more",
    "multi": "one_or_more",
    "list": "one_or_more",
    "multi_value": "one_or_more",
    "single": "single",
    "one": "single",
}
_SOURCE_SCOPE_ALIASES: dict[str, SourceScope] = {
    "project_kb": "project_kb",
    "projectkb": "project_kb",
    "project_knowledge_base": "project_kb",
    "kb": "project_kb",
    "knowledge_base": "project_kb",
    "any": "any",
}
_ENUM_SPLIT_RE = re.compile(r"[,，、;；/|]+")


class SlotGuide(BaseModel):
    """单个槽位的抽取指引与需求描述。"""

    key: str
    key_indicators: list[str] = Field(default_factory=list)
    content_pattern: str = ""
    common_locations: list[str] = Field(default_factory=list)
    quality_criteria: str = ""
    # --- 需求描述（template_structure v2）：缺省即保守默认 ---
    unit: str = ""
    enum_values: list[str] = Field(default_factory=list)
    cardinality: Cardinality = "single"
    source_scope: SourceScope = "any"

    @field_validator("unit", mode="before")
    @classmethod
    def _coerce_unit(cls, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (list, tuple)):
            return "、".join(str(v).strip() for v in value if str(v).strip())
        return str(value).strip()

    @field_validator("enum_values", mode="before")
    @classmethod
    def _coerce_enum(cls, value: Any) -> list[str]:
        """允许取值：字符串（逗号/顿号/斜杠分隔）与列表都接受，统一成列表。"""
        if value is None:
            return []
        if isinstance(value, str):
            return [part.strip() for part in _ENUM_SPLIT_RE.split(value) if part.strip()]
        if isinstance(value, (list, tuple, set)):
            return [str(item).strip() for item in value if str(item).strip()]
        return []

    @field_validator("cardinality", mode="before")
    @classmethod
    def _normalize_cardinality(cls, value: Any) -> Cardinality:
        key = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
        return _CARDINALITY_ALIASES.get(key, "single")

    @field_validator("source_scope", mode="before")
    @classmethod
    def _normalize_source_scope(cls, value: Any) -> SourceScope:
        key = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
        return _SOURCE_SCOPE_ALIASES.get(key, "any")


class TemplateAnalysisOut(BaseModel):
    """模板分析响应。"""

    slots: list[SlotGuide] = Field(default_factory=list)


@dataclass
class TemplateAnalysisResult:
    """模板分析产物：每槽位的抽取指引 + 增强的检索词 + 需求描述。"""

    guides: dict[str, SlotGuide] = field(default_factory=dict)
    # 分析过程中为 search_terms 为空的槽位补的同义词
    enriched_terms: dict[str, list[str]] = field(default_factory=dict)
    # 分析得到的槽位需求描述（key → {unit, enum_values, cardinality, source_scope}）
    requirements: dict[str, dict[str, Any]] = field(default_factory=dict)
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
    requirements: dict[str, dict[str, Any]] = {}
    for guide in out.slots:
        guides[guide.key] = guide
        # 如果 key_indicators 非空且该槽位 search_terms 为空，用 indicators 补检索词
        if guide.key_indicators:
            enriched_terms[guide.key] = [t.strip() for t in guide.key_indicators if t.strip()][:8]
        requirements[guide.key] = {
            "unit": guide.unit,
            "enum_values": list(guide.enum_values),
            "cardinality": guide.cardinality,
            "source_scope": guide.source_scope,
        }

    logger.info(
        "模板分析完成",
        extra={
            "template": spec.name,
            "analyzed": len(guides),
            "enriched_terms": len(enriched_terms),
            "requirements": sum(1 for req in requirements.values() if not _is_default_requirement(req)),
        },
    )
    return TemplateAnalysisResult(
        guides=guides,
        enriched_terms=enriched_terms,
        requirements=requirements,
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


def _is_default_requirement(req: Mapping[str, Any]) -> bool:
    """判断需求描述是否为保守默认（不含任何实际约束）。"""
    unit = str(req.get("unit") or "").strip()
    enum_values = [str(v).strip() for v in (req.get("enum_values") or []) if str(v).strip()]
    cardinality = str(req.get("cardinality") or "single").strip().lower()
    source_scope = str(req.get("source_scope") or "any").strip().lower()
    return not unit and not enum_values and cardinality == "single" and source_scope == "any"


def apply_requirements_to_spec(spec: TemplateSpec, analysis: TemplateAnalysisResult) -> int:
    """把模板分析得到的「需求描述」回写到 spec 实例，返回实际写入约束的槽位数。

    保守合并：只补保守默认值，人工在模板里声明过的约束（或上一轮分析写过的）
    一律不覆盖——同 ``apply_analysis_to_spec`` 的边界，不回写模板库。
    """
    by_key = {slot.key: slot for slot in spec.slots}
    applied = 0
    for key, req in analysis.requirements.items():
        slot = by_key.get(key)
        if slot is None or _is_default_requirement(req):
            continue
        changed = False
        unit = str(req.get("unit") or "").strip()
        if unit and not slot.unit:
            slot.unit = unit[:50]
            changed = True
        enum_values = [str(v).strip() for v in (req.get("enum_values") or []) if str(v).strip()]
        if enum_values and not slot.enum_values:
            slot.enum_values = enum_values[:20]
            changed = True
        if str(req.get("cardinality") or "").strip().lower() == "one_or_more" and slot.cardinality == "single":
            slot.cardinality = "one_or_more"
            changed = True
        if str(req.get("source_scope") or "").strip().lower() == "project_kb" and slot.source_scope == "any":
            slot.source_scope = "project_kb"
            changed = True
        if changed:
            applied += 1
    return applied


__all__ = [
    "analyze_template",
    "apply_analysis_to_spec",
    "apply_requirements_to_spec",
    "TemplateAnalysisResult",
    "SlotGuide",
]
