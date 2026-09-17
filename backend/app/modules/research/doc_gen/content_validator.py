"""内容交叉校验：对比文件分析摘要与槽位提取结果，标记不一致。

在提取阶段完成后运行，用 LLM 对比文件分析阶段的产物与提取阶段的槽位值，
发现潜在遗漏（文件有内容但槽位未提取到）或冲突（两者值不一致）。
校验结果作为告警写入任务统计，供人工复核时参考。
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from app.modules.research.doc_gen.extraction import SlotResult
from app.modules.research.doc_gen.file_analyzer import FileAnalysisBatchResult
from app.modules.research.doc_gen.prompts import build_cross_validation_prompt
from app.modules.research.doc_gen import status

logger = logging.getLogger(__name__)

_MAX_VALIDATION_SLOTS = 60


class ValidationCheck(BaseModel):
    """单槽位校验结果。"""

    key: str
    status: str = "consistent"  # consistent/potential_miss/potential_conflict
    detail: str = ""


class ValidationOut(BaseModel):
    """校验响应。"""

    checks: list[ValidationCheck] = Field(default_factory=list)


@dataclass
class ValidationResult:
    """交叉校验产物。"""

    checks: dict[str, ValidationCheck] = field(default_factory=dict)
    potential_misses: list[str] = field(default_factory=list)
    potential_conflicts: list[str] = field(default_factory=list)
    consistent_count: int = 0
    failed: bool = False
    warnings: list[str] = field(default_factory=list)


def _build_file_summaries(
    batch_result: FileAnalysisBatchResult,
    slot_keys: Sequence[str],
) -> list[dict[str, Any]]:
    """从文件分析结果构建校验用的文件摘要。"""
    summaries: list[dict[str, Any]] = []
    for file_id, result in batch_result.results.items():
        if result.failed:
            continue
        slot_data: dict[str, Any] = {}
        for key in slot_keys:
            extraction = result.slot_extractions.get(key)
            if extraction is not None and extraction.found:
                slot_data[key] = {
                    "content": extraction.extracted_content[:200],
                    "relevance": extraction.relevance,
                }
        if slot_data:
            summaries.append({
                "file_id": file_id,
                "file_name": result.file_name,
                "summary": result.summary,
                "slot_content": slot_data,
            })
    return summaries


def _build_slot_results_for_validation(
    results: Mapping[str, SlotResult],
    slot_keys: Sequence[str],
) -> list[dict[str, Any]]:
    """构建校验用的槽位提取结果。"""
    items: list[dict[str, Any]] = []
    for key in slot_keys:
        result = results.get(key)
        if result is None:
            continue
        items.append({
            "key": key,
            "text": result.text[:200] if result.text else "",
            "state": result.state,
            "has_evidence": len(result.evidence) > 0,
        })
    return items


async def validate_extraction(
    file_analysis: FileAnalysisBatchResult,
    slot_results: Mapping[str, SlotResult],
    *,
    llm: Any = None,
    timeout_seconds: float | None = None,
    llm_kwargs: Mapping[str, Any] | None = None,
) -> ValidationResult:
    """用 LLM 交叉校验文件分析摘要与槽位提取结果。

    只校验有文件分析数据且提取结果非空的槽位。
    失败时静默降级返回空结果，不影响任务继续。
    """
    from app.core.llm import llm_client

    # 收集需要校验的槽位：文件分析中有内容且提取结果非 pending/failed
    candidate_keys: list[str] = []
    for key in file_analysis.slot_to_files:
        slot_result = slot_results.get(key)
        if slot_result is not None and slot_result.state not in (status.STATUS_FAILED,):
            candidate_keys.append(key)
    candidate_keys = candidate_keys[:_MAX_VALIDATION_SLOTS]

    if not candidate_keys:
        return ValidationResult()

    file_summaries = _build_file_summaries(file_analysis, candidate_keys)
    slot_results_data = _build_slot_results_for_validation(slot_results, candidate_keys)

    if not file_summaries:
        return ValidationResult()

    messages = build_cross_validation_prompt(file_summaries, slot_results_data)
    client = llm or llm_client

    try:
        call = client.chat_json(messages, expected_keys=["checks"], temperature=0, **(llm_kwargs or {}))
        raw = await asyncio.wait_for(call, timeout=timeout_seconds) if timeout_seconds else await call
        out = ValidationOut.model_validate(raw)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.warning("交叉校验失败，跳过", extra={"error": type(exc).__name__})
        return ValidationResult(failed=True)

    # 解析结果
    result = ValidationResult()
    for check in out.checks:
        result.checks[check.key] = check
        if check.status == "potential_miss":
            result.potential_misses.append(check.key)
        elif check.status == "potential_conflict":
            result.potential_conflicts.append(check.key)
        else:
            result.consistent_count += 1

    # 生成告警
    if result.potential_misses:
        result.warnings.append(
            f"交叉校验发现 {len(result.potential_misses)} 个槽位可能存在遗漏"
            f"（{', '.join(result.potential_misses[:5])}），建议人工复核"
        )
    if result.potential_conflicts:
        result.warnings.append(
            f"交叉校验发现 {len(result.potential_conflicts)} 个槽位可能存在冲突"
            f"（{', '.join(result.potential_conflicts[:5])}），建议人工复核"
        )

    logger.info(
        "交叉校验完成",
        extra={
            "checked": len(result.checks),
            "consistent": result.consistent_count,
            "potential_misses": len(result.potential_misses),
            "potential_conflicts": len(result.potential_conflicts),
        },
    )
    return result


__all__ = ["validate_extraction", "ValidationResult"]
