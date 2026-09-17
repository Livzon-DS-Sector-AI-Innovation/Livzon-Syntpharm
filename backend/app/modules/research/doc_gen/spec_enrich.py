"""AI 辅助标注：为模板槽位补齐检索同义词。

母本自动识别（spec_draft）只能推断槽位的**位置**，推不出**语义**——槽位 label 往往
是母本里的一句提示语，与资料里的实际用语脱节，关键词检索容易 0 命中。这里用一次
批量模型调用为缺检索词的槽位补 search_terms（同义词/英文/缩写/行业惯用叫法）：

- 只补 ``search_terms`` 为空的槽位，人工在模板里配好的检索词不被覆盖；
- 模型不可用 / 输出不合规时静默降级返回 0，不影响任务继续（检索词只是增强项）；
- 结果只写在本次任务的 spec 实例上，不回写模板库——单次任务运行不应改变模板定义；
  后续如需持久化，可在模板保存流程里调用本模块并把结果存入槽位定义。
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, Field

from app.modules.research.doc_gen.template_spec import Slot, TemplateSpec

logger = logging.getLogger(__name__)

_MAX_ENRICH_SLOTS = 60
_MAX_TERMS_PER_SLOT = 8
_ENRICHABLE_KINDS = frozenset({"field", "table", "paragraph"})

_SYSTEM_RULES = (
    "你是制药研发文档的检索词标注助手。给出一批文档模板槽位（字段名与说明），"
    "为每个槽位预测原始研究资料中可能出现的相关表述（近义词、英文名、缩写、行业惯用叫法），"
    "这些词将用于关键词检索定位资料。"
    "特别注意：涉及化学物质/药品的槽位，要包含分子式（如 C18H19N5O2）、CAS 号、"
    "英文通用名（INN）、化学名称等常见表述。"
    "只输出 JSON；没有把握的槽位返回空数组，禁止编造。"
)


class SlotTerms(BaseModel):
    """单个槽位的检索词标注结果。"""

    key: str
    search_terms: list[str] = Field(default_factory=list)


class EnrichOut(BaseModel):
    """批量标注响应。"""

    slots: list[SlotTerms] = Field(default_factory=list)


def enrich_targets(spec: TemplateSpec) -> list[Slot]:
    """需要标注的槽位：非元数据、非人工专用、且还没有检索词的。"""
    return [
        slot
        for slot in spec.slots
        if slot.kind in _ENRICHABLE_KINDS
        and not slot.from_meta
        and not slot.manual_only
        and not slot.search_terms
    ]


def _slot_payload(slot: Slot) -> dict[str, Any]:
    return {
        "key": slot.key,
        "label": slot.label,
        "hint": slot.query_hint,
        "columns": [c.label or c.key for c in slot.columns],
    }


async def enrich_search_terms(
    spec: TemplateSpec,
    *,
    llm: Any = None,
    timeout_seconds: float | None = None,
    llm_kwargs: Mapping[str, Any] | None = None,
) -> int:
    """为缺检索词的槽位补 search_terms，直接写回 spec；返回标注成功的槽位数。

    模型调用套硬超时；任何失败（网络/超时/输出不合规）都按降级处理返回 0，
    由调用方决定是否记录——本函数只 warning，不抛业务异常。
    ``llm_kwargs`` 透传给 chat_json（如 ``model_override`` / ``config_name``），
    便于模板标注与提取/成文走不同模型。
    """
    from app.core.llm import llm_client

    targets = enrich_targets(spec)
    if not targets:
        return 0
    targets = targets[:_MAX_ENRICH_SLOTS]
    payload = [_slot_payload(slot) for slot in targets]
    schema = {"slots": [{"key": "槽位 key", "search_terms": ["同义词1", "同义词2"]}]}
    user = (
        "槽位列表（JSON）：\n"
        f"{json.dumps(payload, ensure_ascii=False)}\n\n"
        f"为每个槽位输出 3-{_MAX_TERMS_PER_SLOT} 个资料中可能出现的检索词；"
        "输出结构示例：\n"
        f"{json.dumps(schema, ensure_ascii=False)}"
    )
    messages = [{"role": "system", "content": _SYSTEM_RULES}, {"role": "user", "content": user}]
    client = llm or llm_client
    try:
        call = client.chat_json(messages, expected_keys=["slots"], temperature=0, **(llm_kwargs or {}))
        raw = await asyncio.wait_for(call, timeout=timeout_seconds) if timeout_seconds else await call
        out = EnrichOut.model_validate(raw)
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001 - 标注是增强项，任何失败都静默降级
        logger.warning("槽位检索词 AI 标注失败，跳过", extra={"error": type(exc).__name__})
        return 0
    terms_by_key = {item.key: item.search_terms for item in out.slots}
    applied = 0
    for slot in targets:
        terms = [term.strip() for term in terms_by_key.get(slot.key, []) if term and term.strip()]
        if terms and not slot.search_terms:
            slot.search_terms = terms[:_MAX_TERMS_PER_SLOT]
            applied += 1
    return applied


__all__ = ["enrich_search_terms", "enrich_targets"]
