"""直接生成模式：一次性把全部资料文本塞进 context，让模型直接生成报告内容，再按槽位映射填充模板。

替代传统的「逐槽位提取 → 成文」两步流程，将 LLM 调用从 30+ 次降到 1-2 次。
适用于对速度要求高于对逐槽位证据追溯要求的场景。
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from app.core.llm import llm_client
from app.core.llm.exceptions import LLMProviderError, LLMRateLimitError
from app.modules.research.doc_gen import status
from app.modules.research.doc_gen.extraction import SlotResult
from app.modules.research.doc_gen.parsing import TextBlock
from app.modules.research.doc_gen.template_spec import Slot, TemplateSpec

logger = logging.getLogger(__name__)

CancelProbe = Callable[[], bool]
ProgressCallback = Callable[[int, int], Awaitable[None]]

# 直接生成模式下的最大上下文字符数（默认 180K，约 112K tokens，适配 128K 输入模型）
DEFAULT_DIRECT_MAX_CHARS = 180_000
# 输出预留 tokens（匹配 Local-DeepSeek-V4.1-Flash 最大输出 8192）
DIRECT_OUTPUT_RESERVE = 8192

_SYSTEM_PROMPT = """\
你是制药研发技术调研报告的专业撰写助手。你的任务是根据提供的资料文件内容，\
为模板中的每个填充项生成准确、专业的内容。

规则：
1) 只能使用提供的资料内容作为信息来源，禁止编造任何数字、日期、编号或结论；
2) 如果某个填充项在资料中找不到相关信息，返回空字符串 ""；
3) 数字与单位保留原文写法，不得改写精度；
4) 表述客观、简洁、书面化，不要出现「根据资料」「经查询」「AI」等过程性措辞；
5) 化学式（如 C18H19N5O2）、分子式、CAS 号、英文药名等专业术语保留原文；
6) 表格类填充项（kind=table）必须返回行数据列表，每行是一个 JSON 对象；
7) 段落类填充项（kind=paragraph）请写成连贯的书面段落；
8) 字段类填充项（kind=field）请简洁填写，不超过指定字数上限；
9) 只输出 JSON，不要解释。
"""


class DirectGenResult(BaseModel):
    """直接生成的完整结果。"""

    slot_values: dict[str, Any] = Field(default_factory=dict)
    """key → value 映射。value 可以是 str（field/paragraph）或 list[dict]（table）"""


def _build_slot_descriptions(slots: list[Slot]) -> str:
    """构建槽位描述文本，告诉 LLM 每个填充项的要求。"""
    lines: list[str] = []
    for slot in slots:
        if slot.from_meta or slot.manual_only:
            continue
        kind_label = {"field": "字段", "paragraph": "段落", "table": "表格", "image": "图片"}
        kind_text = kind_label.get(slot.kind, slot.kind)
        line = f"- {slot.key}（{slot.label}，类型={kind_text}"
        if slot.max_chars:
            line += f"，字数上限={slot.max_chars}"
        if slot.kind == "table" and slot.columns:
            col_desc = "，".join(f"{c.key}={c.label}" for c in slot.columns)
            line += f"，列定义=[{col_desc}]"
        if slot.search_terms:
            line += f"，检索关键词=[{', '.join(slot.search_terms[:5])}]"
        line += ")"
        lines.append(line)
    return "\n".join(lines)


def _build_source_text(
    blocks: list[TextBlock], max_chars: int, file_names: dict[str, str] | None = None
) -> str:
    """拼接所有文本块为一份资料来源文本。"""
    parts: list[str] = []
    total = 0
    names = file_names or {}
    # 按文件分组，加文件分隔标记
    current_file = None
    for block in blocks:
        if block.file_id != current_file:
            current_file = block.file_id
            file_label = names.get(block.file_id, block.file_id)
            parts.append(f"\n===== 资料来源：{file_label} =====\n")
        page_info = f"[第{block.page}页]" if block.page else ""
        chunk = f"{page_info}{block.text}\n"
        if total + len(chunk) > max_chars:
            remaining = max_chars - total
            if remaining > 200:
                parts.append(chunk[:remaining] + "\n...[内容截断]")
            break
        parts.append(chunk)
        total += len(chunk)
    return "".join(parts)


def _build_prompt(
    spec: TemplateSpec,
    blocks: list[TextBlock],
    max_chars: int,
    supplement_text: str = "",
    file_names: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    """构建 LLM 调用的 messages。"""
    # 槽位描述
    slot_desc = _build_slot_descriptions(spec.slots)
    # 资料来源文本
    source_text = _build_source_text(blocks, max_chars, file_names)
    # 补充信息
    supplement_section = ""
    if supplement_text:
        supplement_section = f"\n\n## 人工补充信息\n{supplement_text}\n"

    # 构建输出格式说明
    output_format_lines = ["输出 JSON 格式如下：", "{"]
    for slot in spec.slots:
        if slot.from_meta or slot.manual_only:
            continue
        if slot.kind == "table":
            col_keys = [c.key for c in slot.columns]
            output_format_lines.append(f'  "{slot.key}": [{{"{col_keys[0]}": "值", ...}}],')
        elif slot.kind == "image":
            continue
        else:
            output_format_lines.append(f'  "{slot.key}": "值",')
    output_format_lines.append("}")
    output_format = "\n".join(output_format_lines)

    user_content = f"""\
## 需要填充的项目

{slot_desc}

## 输出格式要求

{output_format}

## 资料文件内容

{source_text}
{supplement_section}

请根据以上资料内容，为每个填充项生成准确的内容。只输出 JSON，不要解释。"""

    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def _parse_llm_response(
    response_text: str,
    spec: TemplateSpec,
) -> dict[str, SlotResult]:
    """解析 LLM 返回的 JSON，映射为 SlotResult 字典。"""
    # 尝试提取 JSON（LLM 有时会在 JSON 前后加文字）
    text = response_text.strip()
    # 尝试找 JSON 块
    json_match = re.search(r"\{[\s\S]*\}", text)
    if json_match:
        text = json_match.group(0)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("直接生成：LLM 返回无法解析的 JSON", extra={"response_preview": text[:500]})
        return {}

    results: dict[str, SlotResult] = {}
    slot_map = {s.key: s for s in spec.slots}

    for key, value in data.items():
        slot = slot_map.get(key)
        if slot is None:
            continue  # 忽略不在模板中的 key

        if slot.kind == "table":
            # 表格槽位：value 应该是 list[dict]
            if isinstance(value, list):
                rows: list[dict[str, str]] = []
                col_keys = {c.key for c in slot.columns}
                for row_data in value:
                    if isinstance(row_data, dict):
                        row = {k: str(v) for k, v in row_data.items() if k in col_keys}
                        if any(row.values()):
                            rows.append(row)
                results[key] = SlotResult(
                    key=key,
                    text="",
                    rows=rows,
                    state=status.STATUS_OK if rows else status.STATUS_PENDING,
                )
            else:
                results[key] = SlotResult(
                    key=key,
                    text="",
                    state=status.STATUS_FAILED,
                    reason="表格数据格式错误",
                )
        else:
            # field / paragraph 槽位：value 应该是 str
            text_value = str(value).strip() if value else ""
            if text_value:
                # 截断到字数上限
                if slot.max_chars and len(text_value) > slot.max_chars:
                    text_value = text_value[: slot.max_chars]
                results[key] = SlotResult(
                    key=key,
                    text=text_value,
                    state=status.STATUS_OK,
                )
            else:
                results[key] = SlotResult(
                    key=key,
                    text=status.pending("资料中未找到相关信息"),
                    state=status.STATUS_PENDING,
                )

    # 为模板中未出现在 LLM 输出里的槽位填充默认值
    for slot in spec.slots:
        if slot.from_meta or slot.manual_only:
            continue
        if slot.key not in results:
            if slot.kind == "image":
                results[slot.key] = SlotResult(
                    key=slot.key,
                    text=status.IMAGE_PLACEHOLDER.format(label=slot.label),
                    state=status.STATUS_MANUAL,
                )
            else:
                results[slot.key] = SlotResult(
                    key=slot.key,
                    text=status.pending("模型未返回该填充项"),
                    state=status.STATUS_PENDING,
                )

    return results


@dataclass(slots=True)
class DirectGenStats:
    """直接生成统计。"""

    calls: int = 0
    failures: int = 0
    source_chars: int = 0
    result_count: int = 0


async def direct_generate(
    spec: TemplateSpec,
    blocks: list[TextBlock],
    *,
    max_chars: int = DEFAULT_DIRECT_MAX_CHARS,
    timeout_seconds: int = 300,
    model_override: str | None = None,
    config_name: str | None = None,
    supplement_text: str = "",
    file_names: dict[str, str] | None = None,
    should_cancel: CancelProbe | None = None,
    on_progress: ProgressCallback | None = None,
) -> tuple[dict[str, SlotResult], DirectGenStats]:
    """一次性生成全部填充项内容。

    Args:
        spec: 模板规格定义
        blocks: 解析后的文本块列表
        max_chars: 资料来源文本最大字符数
        timeout_seconds: LLM 调用超时
        model_override: 模型名覆盖
        config_name: LLM 配置名
        supplement_text: 人工补充信息
        file_names: file_id → 文件名映射，用于资料来源标注
        should_cancel: 取消检查回调
        on_progress: 进度回调

    Returns:
        (slot_results, stats) 元组
    """
    stats = DirectGenStats()

    if on_progress:
        await on_progress(0, 1)

    # 构建 prompt
    messages = _build_prompt(spec, blocks, max_chars, supplement_text, file_names)
    source_chars = sum(len(m.get("content", "")) for m in messages)
    stats.source_chars = source_chars

    logger.info(
        "直接生成：开始调用 LLM",
        extra={
            "source_chars": source_chars,
            "blocks": len(blocks),
            "slots": len([s for s in spec.slots if not s.from_meta and not s.manual_only]),
        },
    )

    try:
        response = await asyncio.wait_for(
            llm_client.chat(
                messages=messages,
                response_format="json_object",
                max_tokens=DIRECT_OUTPUT_RESERVE,
                model_override=model_override,
                config_name=config_name,
            ),
            timeout=timeout_seconds,
        )
        stats.calls = 1
    except asyncio.TimeoutError:
        logger.warning("直接生成：LLM 调用超时", extra={"timeout": timeout_seconds})
        stats.failures = 1
        return _fallback_results(spec), stats
    except (LLMProviderError, LLMRateLimitError) as exc:
        logger.warning("直接生成：LLM 调用失败", extra={"error": str(exc)})
        stats.failures = 1
        return _fallback_results(spec), stats
    except Exception:
        logger.exception("直接生成：LLM 调用异常")
        stats.failures = 1
        return _fallback_results(spec), stats

    if on_progress:
        await on_progress(1, 1)

    # 解析响应
    results = _parse_llm_response(response, spec)
    stats.result_count = len([r for r in results.values() if r.state == status.STATUS_OK])

    logger.info(
        "直接生成：完成",
        extra={
            "calls": stats.calls,
            "results": stats.result_count,
            "total_slots": len(results),
        },
    )

    return results, stats


def _fallback_results(spec: TemplateSpec) -> dict[str, SlotResult]:
    """LLM 调用失败时的降级结果：所有槽位标为待补充。"""
    results: dict[str, SlotResult] = {}
    for slot in spec.slots:
        if slot.from_meta or slot.manual_only:
            continue
        if slot.kind == "image":
            results[slot.key] = SlotResult(
                key=slot.key,
                text=status.IMAGE_PLACEHOLDER.format(label=slot.label),
                state=status.STATUS_MANUAL,
            )
        else:
            results[slot.key] = SlotResult(
                key=slot.key,
                text=status.pending("直接生成失败，请人工填写"),
                state=status.STATUS_FAILED,
            )
    return results
