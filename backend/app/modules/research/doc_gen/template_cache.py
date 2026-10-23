"""模板分析结果的跨任务缓存：同一份模板结构只让模型完整分析一次。

缓存载体是模板行 ``template_structure`` 里的私有键（``_analysis_cache``）：不新增表、
不新增迁移，也不改动槽位结构本身——``TemplateSpec.model_validate`` 会忽略未知键，
``spec_from_structure`` 不受影响。

失效靠 ``fingerprint``（槽位语义签名）：模板语义被编辑（AI 语义增强 / 人工新增填写项 /
换母本重新识别）后指纹变化，缓存自然作废，不存在「用了过期指引」的窗口。

稳定性契约与全链路一致：读写失败一律降级为「没有缓存」，绝不拖垮任务。
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.research.doc_gen.template_analyzer import SlotGuide, TemplateAnalysisResult
from app.modules.research.doc_gen.template_spec import TemplateSpec
from app.modules.research.models import RdDeliverableTemplate

logger = logging.getLogger(__name__)

# 私有缓存键：下划线开头，与 template_structure 的正式字段（code/slots/...）区分
ANALYSIS_CACHE_KEY = "_analysis_cache"
_FINGERPRINT_LEN = 16


def spec_fingerprint(spec: TemplateSpec) -> str:
    """槽位语义签名：指纹一致即认为「模板没变，分析结果可复用」。

    只纳入影响抽取指引的语义字段（名字/提示/检索词/期望/来源范围/列定义），
    渲染定位（anchors）与文档元信息不参与——它们不影响分析产物。
    """
    payload = {
        "code": spec.code,
        "version": spec.version,
        "slots": [
            {
                "key": slot.key,
                "label": slot.label,
                "kind": slot.kind,
                "query_hint": slot.query_hint,
                "search_terms": sorted(slot.search_terms),
                "expects": slot.expects,
                "required": slot.required,
                "max_chars": slot.max_chars,
                "source_roles": sorted(slot.source_roles),
                "source_scope": slot.source_scope,
                "unit": slot.unit,
                "enum_values": list(slot.enum_values),
                "columns": [f"{column.key}:{column.label}" for column in slot.columns],
            }
            for slot in spec.slots
        ],
    }
    dumped = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()[:_FINGERPRINT_LEN]


def result_to_payload(result: TemplateAnalysisResult, fingerprint: str) -> dict[str, Any]:
    """分析结果 → 可 JSON 落库的缓存体。"""
    return {
        "fingerprint": fingerprint,
        "at": datetime.now(UTC).isoformat(),
        "analyzed_count": result.analyzed_count,
        "failed": result.failed,
        "guides": {key: guide.model_dump() for key, guide in result.guides.items()},
        "enriched_terms": {key: list(terms) for key, terms in result.enriched_terms.items()},
        "requirements": {key: dict(value) for key, value in result.requirements.items()},
        "sections": {key: str(value) for key, value in result.sections.items()},
    }


def payload_to_result(payload: Any) -> TemplateAnalysisResult | None:
    """缓存体 → 分析结果；结构不合法返回 None（按未命中处理）。"""
    if not isinstance(payload, dict):
        return None
    try:
        guides = {str(key): SlotGuide.model_validate(value) for key, value in (payload.get("guides") or {}).items()}
    except Exception:  # noqa: BLE001 - 缓存可能被人为改坏，降级为未命中
        logger.exception("模板分析缓存解析失败，按未命中处理")
        return None
    requirements = {
        str(key): dict(value) for key, value in (payload.get("requirements") or {}).items() if isinstance(value, dict)
    }
    enriched = {
        str(key): [str(item) for item in value]
        for key, value in (payload.get("enriched_terms") or {}).items()
        if isinstance(value, list)
    }
    sections = {str(key): str(value) for key, value in (payload.get("sections") or {}).items() if str(value).strip()}
    return TemplateAnalysisResult(
        guides=guides,
        enriched_terms=enriched,
        requirements=requirements,
        sections=sections,
        analyzed_count=int(payload.get("analyzed_count") or 0),
        failed=bool(payload.get("failed")),
    )


def cached_result(structure: Any, fingerprint: str) -> TemplateAnalysisResult | None:
    """从 ``template_structure`` 读缓存：指纹不符或结构非法都返回 None（纯函数）。"""
    if not isinstance(structure, dict):
        return None
    payload = structure.get(ANALYSIS_CACHE_KEY)
    if not isinstance(payload, dict) or payload.get("fingerprint") != fingerprint:
        return None
    return payload_to_result(payload)


def with_cache(structure: Any, payload: dict[str, Any]) -> dict[str, Any]:
    """把缓存体合并进 ``template_structure``（纯函数，不改动原有键）。"""
    merged = dict(structure) if isinstance(structure, dict) else {}
    merged[ANALYSIS_CACHE_KEY] = payload
    return merged


def _as_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


async def load_analysis(
    session: AsyncSession, template_id: str | None, fingerprint: str
) -> TemplateAnalysisResult | None:
    """读模板分析缓存；任何异常降级为「没有缓存」。"""
    key = _as_uuid(template_id or "")
    if key is None:
        return None
    try:
        row = await session.get(RdDeliverableTemplate, key)
        if row is None or row.is_deleted:
            return None
        return cached_result(row.template_structure, fingerprint)
    except Exception:  # noqa: BLE001 - 缓存读取失败不能拖垮任务
        logger.exception("模板分析缓存读取失败，按未命中处理")
        return None


async def save_analysis(
    session: AsyncSession, template_id: str | None, fingerprint: str, result: TemplateAnalysisResult
) -> bool:
    """把分析结果写进模板行的私有缓存键；成功返回 True。

    只写单个私有键（Core UPDATE 绕过 ORM 脏检查，不触碰槽位结构），失败只记日志并
    回滚事务——绝不因为缓存写入把执行 session 拖进 aborted 状态。
    """
    key = _as_uuid(template_id or "")
    if key is None or result.failed:
        return False
    try:
        row = await session.get(RdDeliverableTemplate, key)
        if row is None or row.is_deleted:
            return False
        structure = row.template_structure if isinstance(row.template_structure, dict) else {}
        if not structure.get("slots"):
            # 没有落库结构的模板（纯内置 / 未识别）没有稳定缓存载体，不做缓存
            return False
        merged = with_cache(structure, result_to_payload(result, fingerprint))
        await session.execute(
            update(RdDeliverableTemplate).where(RdDeliverableTemplate.id == key).values(template_structure=merged)
        )
        await session.commit()
        return True
    except Exception:  # noqa: BLE001 - 缓存写入失败不能拖垮任务
        logger.exception("模板分析缓存写入失败（忽略）")
        try:
            await session.rollback()
        except Exception:  # noqa: BLE001 - rollback 也可能失败
            logger.exception("模板分析缓存写入失败后的回滚也失败")
        return False


__all__ = [
    "ANALYSIS_CACHE_KEY",
    "cached_result",
    "load_analysis",
    "payload_to_result",
    "result_to_payload",
    "save_analysis",
    "spec_fingerprint",
    "with_cache",
]
