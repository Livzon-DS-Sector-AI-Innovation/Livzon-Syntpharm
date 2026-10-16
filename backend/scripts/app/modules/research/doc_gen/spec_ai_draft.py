"""AI 语义增强：把规则草拟的槽位补成「可被检索/提取命中」的语义。

与 ``spec_enrich`` 的分工：

- ``spec_enrich`` 在**任务运行时**只补 ``search_terms``、不回写模板库（一次性、轻量）；
- ``spec_ai_draft`` 在**模板识别/编辑时**做完整语义增强（label/检索词/期望/必填/置信度），
  结果随 ``template_structure`` 落库，该模板以后每次生成都受益（越用越准的正循环）。

铁律（与「混合：规则定位 + AI 补语义」的决策一致）：

1. **AI 只改语义字段，绝不改 ``anchors``/``kind``/``columns`` 结构**——锚点由规则扫描器
   安全产出，AI 改锚点会导致渲染定位失败；
2. ``search_terms`` 用**并集**（保留已有 + 追加 AI 产出），只增不减，最大化检索召回；
3. 低置信槽位标 ``review_state="needs_review"``，交人工补充，不冒充可信；
4. 任何失败（超时/解析/校验）**静默降级**返回原 spec，不阻塞模板识别。
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.core.llm import llm_client
from app.modules.research.doc_gen.template_spec import Slot, TemplateSpec

logger = logging.getLogger(__name__)

_MAX_SLOTS_PER_CALL = 12
_DEFAULT_TIMEOUT_SECONDS = 120.0
# 置信度低于此值的 AI 标注转「需人工核对」（与提取侧 DOC_GEN_CONFIDENCE_MID 同档）
_NEEDS_REVIEW_THRESHOLD = 0.6
_MAX_SEARCH_TERMS = 12

_EXPECTS_VALUES = frozenset({"text", "number", "date", "percent"})
_CARDINALITY_VALUES = frozenset({"single", "one_or_more"})
_SOURCE_SCOPE_VALUES = frozenset({"any", "project_kb"})

_SYSTEM_PROMPT = (
    "你是制药研发文档模板的槽位语义标注专家。系统已用规则从 Word 母本里定位出可填写位置"
    "（锚点已固定，你不得改动），现在需要你为每个槽位补全「便于从资料中检索和提取」的语义。\n"
    "对每个槽位输出：\n"
    "- label：简洁中文显示名（≤20字）\n"
    "- search_terms：3-8 个检索关键词，覆盖中文名/英文名/缩写/别名/口语说法（检索召回的命脉，尽量全）\n"
    "- query_hint：一句话说明这里该填什么、从资料的什么位置找\n"
    "- expects：值类型，只能是 text/number/date/percent\n"
    "- unit：expects 为 number/percent 时给单位（如 %、mg、℃），否则留空\n"
    "- enum_values：答案为有限选项时列出，否则留空\n"
    "- required：该字段对报告是否 essential（true/false，保守判断）\n"
    "- cardinality：single（单值）或 one_or_more（可能多值，如多条工艺路线）\n"
    "- source_scope：any（任意资料）或 project_kb（仅项目知识库）\n"
    "- confidence：你对本次标注的置信度（0-1）\n"
    '只输出 JSON：{"slots": [{"key": ..., "label": ..., "search_terms": [...], "query_hint": ...,'
    ' "expects": ..., "unit": ..., "enum_values": [...], "required": ...,'
    ' "cardinality": ..., "source_scope": ..., "confidence": ...}]}。key 必须原样返回。'
)


class _SlotSemantics(BaseModel):
    """AI 对单个槽位的语义标注（宽松接收，应用时再 clamp 到合法字面量）。"""

    key: str
    label: str = ""
    search_terms: list[str] = Field(default_factory=list)
    query_hint: str = ""
    expects: str = "text"
    unit: str = ""
    enum_values: list[str] = Field(default_factory=list)
    required: bool = False
    cardinality: str = "single"
    source_scope: str = "any"
    confidence: float = 0.5


def _enrichable(slot: Slot) -> bool:
    """只对「靠资料提取」的文本类槽位增强；图片/系统字段/纯人工槽位跳过。"""
    return slot.kind in ("field", "paragraph", "table") and not slot.from_meta and not slot.manual_only


def _slot_context(slot: Slot) -> dict[str, Any]:
    """把槽位自带的母本上下文（标签/表头/章节标题）整理给 AI，让检索词扎根真实领域用词。"""
    ctx: dict[str, Any] = {"key": slot.key, "label": slot.label, "kind": slot.kind}
    if slot.query_hint:
        ctx["hint"] = slot.query_hint
    if slot.columns:
        ctx["columns"] = [c.label for c in slot.columns]
    heading = next((a.heading for a in slot.anchors if a.heading), "")
    paragraph_label = next((a.paragraph_label for a in slot.anchors if a.paragraph_label), "")
    table_header = next((a.table_header for a in slot.anchors if a.table_header), "")
    if heading:
        ctx["section"] = heading
    if paragraph_label:
        ctx["paragraph_label"] = paragraph_label
    if table_header:
        ctx["table_header"] = table_header
    return ctx


def _merge_terms(existing: list[str], added: list[str]) -> list[str]:
    """检索词并集（保留已有 + 追加 AI），去重去空，截断到上限——只增不减以提升召回。"""
    merged: list[str] = []
    seen: set[str] = set()
    for term in [*existing, *added]:
        cleaned = (term or "").strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        merged.append(cleaned)
        if len(merged) >= _MAX_SEARCH_TERMS:
            break
    return merged


def _apply(slot: Slot, sem: _SlotSemantics, threshold: float) -> None:
    """把 AI 标注写回槽位：语义字段替换、检索词并集、低置信转 needs_review。"""
    if sem.label.strip():
        slot.label = sem.label.strip()[:60]
    slot.search_terms = _merge_terms(slot.search_terms, sem.search_terms)
    if sem.query_hint.strip():
        slot.query_hint = sem.query_hint.strip()
    if sem.expects in _EXPECTS_VALUES:
        slot.expects = sem.expects  # type: ignore[assignment]
    if sem.unit.strip():
        slot.unit = sem.unit.strip()
    enum_values = [v.strip() for v in sem.enum_values if v and v.strip()]
    if enum_values:
        slot.enum_values = enum_values
    slot.required = bool(sem.required)
    if sem.cardinality in _CARDINALITY_VALUES:
        slot.cardinality = sem.cardinality  # type: ignore[assignment]
    if sem.source_scope in _SOURCE_SCOPE_VALUES:
        slot.source_scope = sem.source_scope  # type: ignore[assignment]
    # 置信度分级：低置信标 needs_review 交人工补充；高置信保持 auto（默认可信）
    slot.review_state = "needs_review" if sem.confidence < threshold else "auto"


async def enrich_spec_semantics(
    spec: TemplateSpec,
    *,
    llm: Any = None,
    timeout_seconds: float | None = None,
    llm_kwargs: Mapping[str, Any] | None = None,
    needs_review_threshold: float = _NEEDS_REVIEW_THRESHOLD,
) -> TemplateSpec:
    """AI 增强规格里所有可增强槽位的语义（原地修改并返回 spec）。

    分批调用、单槽位校验失败只跳过该槽位（不连累整批）；任何异常静默降级返回原 spec。
    调用方负责把返回的 spec 落库（``model_dump`` 写入 ``template_structure``）。
    """
    client = llm or llm_client
    timeout = timeout_seconds if timeout_seconds and timeout_seconds > 0 else _DEFAULT_TIMEOUT_SECONDS
    kwargs = dict(llm_kwargs or {})
    targets = [slot for slot in spec.slots if _enrichable(slot)]
    if not targets:
        return spec

    by_key = {slot.key: slot for slot in targets}
    enriched = 0
    needs_review = 0
    for start in range(0, len(targets), _MAX_SLOTS_PER_CALL):
        batch = targets[start : start + _MAX_SLOTS_PER_CALL]
        payload = {
            "template": {"name": spec.name, "stage": spec.stage, "description": spec.description},
            "slots": [_slot_context(slot) for slot in batch],
        }
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"模板与槽位上下文：\n{json.dumps(payload, ensure_ascii=False)}"},
        ]
        try:
            raw = await asyncio.wait_for(
                client.chat_json(messages, expected_keys=["slots"], temperature=0, **kwargs),
                timeout=timeout,
            )
        except TimeoutError:
            logger.warning("槽位语义 AI 增强超时，降级用规则草拟结果", extra={"batch_size": len(batch)})
            continue
        except Exception:  # noqa: BLE001 - 增强失败不阻塞模板识别
            logger.exception("槽位语义 AI 增强调用失败，降级用规则草拟结果")
            continue

        for item in raw.get("slots") or []:
            if not isinstance(item, dict):
                continue
            try:
                sem = _SlotSemantics.model_validate(item)
            except ValidationError:
                continue
            slot = by_key.get(sem.key)
            if slot is None:  # AI 编了不存在的 key，跳过
                continue
            _apply(slot, sem, needs_review_threshold)
            enriched += 1
            if slot.review_state == "needs_review":
                needs_review += 1

    logger.info(
        "槽位语义 AI 增强完成",
        extra={
            "template_code": spec.code,
            "enriched": enriched,
            "needs_review": needs_review,
            "total_targets": len(targets),
        },
    )
    return spec


__all__ = ["enrich_spec_semantics"]
