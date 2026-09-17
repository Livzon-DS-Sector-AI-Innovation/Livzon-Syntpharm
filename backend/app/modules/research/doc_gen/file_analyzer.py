"""文件分析：异步逐文件读取，用本地模型识别并提取与模板要求匹配的内容。

在解析阶段之后、提取阶段之前运行。对每个已解析的文件，用 LLM 阅读其内容
并根据模板槽位指引输出结构化摘要。产物供后续提取阶段作为增强上下文使用：
- 帮助检索层判断哪些文件与哪些槽位相关（文件-槽位关联矩阵）
- 为提取 prompt 提供预提取内容，提升抽取准确率
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from app.modules.research.doc_gen.parsing import TextBlock
from app.modules.research.doc_gen.prompts import build_file_analysis_prompt
from app.modules.research.doc_gen.template_analyzer import SlotGuide

logger = logging.getLogger(__name__)

# 单文件分析的最大上下文字符数（避免超模型 context window）
_MAX_FILE_CHARS = 30000
# 并发分析文件数上限（受 LLM 网关吞吐限制）
_DEFAULT_CONCURRENCY = 4


class FileSlotExtraction(BaseModel):
    """单文件中与单槽位相关的提取结果。"""

    key: str
    found: bool = False
    extracted_content: str = ""
    relevance: str = "low"  # high/medium/low
    evidence_quote: str = ""


class FileAnalysisOut(BaseModel):
    """单文件分析响应。"""

    file_summary: str = ""
    slots: list[FileSlotExtraction] = Field(default_factory=list)


@dataclass
class FileAnalysisResult:
    """单文件的分析产物。"""

    file_id: str
    file_name: str = ""
    summary: str = ""
    # key → 该文件中与该槽位相关的提取内容
    slot_extractions: dict[str, FileSlotExtraction] = field(default_factory=dict)
    # 该文件对哪些槽位有高相关性（relevance=high）
    high_relevance_keys: list[str] = field(default_factory=list)
    failed: bool = False


@dataclass
class FileAnalysisBatchResult:
    """批量文件分析的汇总产物。"""

    results: dict[str, FileAnalysisResult] = field(default_factory=dict)
    # 槽位 → 包含该槽位相关内容的文件 id 列表（按相关性排序）
    slot_to_files: dict[str, list[str]] = field(default_factory=dict)
    total_analyzed: int = 0
    total_failed: int = 0


def _build_slot_guides(
    guides: Mapping[str, SlotGuide],
    slot_keys: Sequence[str],
) -> list[dict[str, Any]]:
    """把 SlotGuide 转成 prompt 需要的字典格式。"""
    result: list[dict[str, Any]] = []
    for key in slot_keys:
        guide = guides.get(key)
        if guide is None:
            result.append({"key": key, "label": key})
        else:
            result.append({
                "key": guide.key,
                "label": guide.key,
                "key_indicators": guide.key_indicators,
                "content_pattern": guide.content_pattern,
                "common_locations": guide.common_locations,
            })
    return result


def _blocks_to_text(blocks: Sequence[TextBlock], max_chars: int = _MAX_FILE_CHARS) -> str:
    """把同一文件的 TextBlock 列表拼成连续文本。"""
    parts: list[str] = []
    total = 0
    for block in blocks:
        if total + len(block.text) > max_chars:
            break
        parts.append(block.text)
        total += len(block.text)
    return "\n".join(parts)


async def _analyze_single_file(
    file_id: str,
    file_name: str,
    blocks: Sequence[TextBlock],
    slot_guides: list[dict[str, Any]],
    *,
    llm: Any = None,
    timeout_seconds: float | None = None,
    llm_kwargs: Mapping[str, Any] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> FileAnalysisResult:
    """用 LLM 分析单个文件，返回与模板槽位匹配的结构化摘要。"""
    from app.core.llm import llm_client

    text = _blocks_to_text(blocks)
    if not text.strip():
        return FileAnalysisResult(file_id=file_id, file_name=file_name, failed=True)

    if should_cancel and should_cancel():
        return FileAnalysisResult(file_id=file_id, file_name=file_name, failed=True)

    messages = build_file_analysis_prompt(text, file_name, slot_guides, max_chars=_MAX_FILE_CHARS)
    client = llm or llm_client

    try:
        call = client.chat_json(messages, expected_keys=["slots"], temperature=0, **(llm_kwargs or {}))
        raw = await asyncio.wait_for(call, timeout=timeout_seconds) if timeout_seconds else await call
        out = FileAnalysisOut.model_validate(raw)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.warning(
            "文件分析失败",
            extra={"file_id": file_id, "file_name": file_name, "error": type(exc).__name__},
        )
        return FileAnalysisResult(file_id=file_id, file_name=file_name, failed=True)

    # 构建结果
    extractions: dict[str, FileSlotExtraction] = {}
    high_relevance: list[str] = []
    for extraction in out.slots:
        extractions[extraction.key] = extraction
        if extraction.found and extraction.relevance == "high":
            high_relevance.append(extraction.key)

    return FileAnalysisResult(
        file_id=file_id,
        file_name=file_name,
        summary=out.file_summary,
        slot_extractions=extractions,
        high_relevance_keys=high_relevance,
    )


async def analyze_files(
    blocks: Sequence[TextBlock],
    template_guides: Mapping[str, SlotGuide],
    file_names: Mapping[str, str] | None = None,
    *,
    llm: Any = None,
    timeout_seconds: float | None = None,
    llm_kwargs: Mapping[str, Any] | None = None,
    concurrency: int = _DEFAULT_CONCURRENCY,
    should_cancel: Callable[[], bool] | None = None,
    on_progress: Callable[[int, int], Awaitable[None]] | None = None,
) -> FileAnalysisBatchResult:
    """异步并发分析所有文件，返回汇总结果。

    按 file_id 分组 blocks，对每个文件并发调用 LLM 分析。
    分析结果构建「文件-槽位」关联矩阵，供提取阶段使用。
    """
    # 按 file_id 分组
    blocks_by_file: dict[str, list[TextBlock]] = {}
    for block in blocks:
        # 跳过虚拟文件（db: / supplement），它们没有实际文件内容需要分析
        if block.file_id.startswith("db:") or block.file_id == "supplement":
            continue
        blocks_by_file.setdefault(block.file_id, []).append(block)

    if not blocks_by_file:
        return FileAnalysisBatchResult()

    # 收集所有需要分析的槽位 key
    slot_keys = list(template_guides.keys()) if template_guides else []
    if not slot_keys:
        return FileAnalysisBatchResult()

    slot_guides_list = _build_slot_guides(template_guides, slot_keys)
    sem = asyncio.Semaphore(max(1, concurrency))
    done_count = 0
    done_lock = asyncio.Lock()
    total_files = len(blocks_by_file)

    async def _guarded_analyze(file_id: str, file_blocks: list[TextBlock]) -> FileAnalysisResult:
        nonlocal done_count
        async with sem:
            if should_cancel and should_cancel():
                return FileAnalysisResult(file_id=file_id, failed=True)
            name = (file_names or {}).get(file_id, file_id)
            result = await _analyze_single_file(
                file_id,
                name,
                file_blocks,
                slot_guides_list,
                llm=llm,
                timeout_seconds=timeout_seconds,
                llm_kwargs=llm_kwargs,
                should_cancel=should_cancel,
            )
        async with done_lock:
            done_count += 1
            if on_progress:
                try:
                    await on_progress(done_count, total_files)
                except Exception:  # noqa: BLE001
                    pass
        return result

    # 并发分析所有文件
    tasks = [_guarded_analyze(fid, fblocks) for fid, fblocks in blocks_by_file.items()]
    results_list = await asyncio.gather(*tasks)

    # 汇总结果
    batch = FileAnalysisBatchResult()
    slot_to_files: dict[str, list[tuple[str, str]]] = {}  # key → [(file_id, relevance)]

    for result in results_list:
        batch.results[result.file_id] = result
        if result.failed:
            batch.total_failed += 1
            continue
        batch.total_analyzed += 1
        for key, extraction in result.slot_extractions.items():
            if extraction.found:
                slot_to_files.setdefault(key, []).append((result.file_id, extraction.relevance))

    # 按相关性排序：high > medium > low
    relevance_order = {"high": 0, "medium": 1, "low": 2}
    for key, file_list in slot_to_files.items():
        file_list.sort(key=lambda x: relevance_order.get(x[1], 3))
        batch.slot_to_files[key] = [fid for fid, _ in file_list]

    logger.info(
        "文件分析完成",
        extra={
            "total_files": total_files,
            "analyzed": batch.total_analyzed,
            "failed": batch.total_failed,
            "slots_with_content": len(batch.slot_to_files),
        },
    )
    return batch


def build_file_analysis_context(
    batch_result: FileAnalysisBatchResult,
    slot_key: str,
    max_files: int = 3,
) -> list[dict[str, str]]:
    """从文件分析结果中提取某槽位的增强上下文。

    返回与该槽位最相关的前 max_files 个文件的提取内容，
    供提取阶段作为额外上下文注入 prompt。
    """
    relevant_file_ids = batch_result.slot_to_files.get(slot_key, [])[:max_files]
    context_items: list[dict[str, str]] = []
    for file_id in relevant_file_ids:
        result = batch_result.results.get(file_id)
        if result is None:
            continue
        extraction = result.slot_extractions.get(slot_key)
        if extraction is not None and extraction.found and extraction.extracted_content:
            context_items.append({
                "file_id": file_id,
                "file_name": result.file_name,
                "content": extraction.extracted_content,
                "relevance": extraction.relevance,
            })
    return context_items


__all__ = [
    "analyze_files",
    "FileAnalysisResult",
    "FileAnalysisBatchResult",
    "FileSlotExtraction",
    "build_file_analysis_context",
]
