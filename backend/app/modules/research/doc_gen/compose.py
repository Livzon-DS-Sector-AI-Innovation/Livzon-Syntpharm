"""成文（AI 报告生成）：把人工确认过的取值写成报告正文。

**这一步只写字，不改事实**：进来的取值已过证据回检与人工确认，成文模型
（Local-DeepSeek-V4-Flash 一类）负责把它们连成书面段落，程序侧再用两道硬校验兜底：

1. 数字守恒——成文里出现的每个数字，必须已在该槽位的确认值或补充信息里出现过，
   否则判为编造，丢弃该条并保留人工确认文本；
2. 字数守恒——不得超过槽位在母本登记的字数上限（超了会把表格/段落挤出版式），同样回退。

任何槽位成文失败都不阻断任务，与既有降级策略一致；渲染仍由 python-docx 按母本版式完成，
本模块不碰 Word 结构。
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

from pydantic import BaseModel, Field

from app.core.llm import llm_client
from app.modules.research.doc_gen import status
from app.modules.research.doc_gen.extraction import SlotResult
from app.modules.research.doc_gen.template_spec import Slot, split_slot_key

logger = logging.getLogger(__name__)

# 成文只处理有事实可写状态：空槽/需人工填写项没有可成文的依据
COMPOSABLE_STATES = frozenset({status.STATUS_OK, status.STATUS_DRAFT, status.STATUS_CONFLICT})
# 占位与待定标记必须原样留在成文里，否则「这里还欠材料」的信号会被漂亮话吃掉
_KEEP_MARKS = (status.PENDING_PREFIX, status.DRAFT_PREFIX, status.CONFLICT_MARK)
# 表格行最多带进 prompt 的条数（成文要看的是事实，不是整张表）
_MAX_PROMPT_ROWS = 40
# 无补充信息时也能引用的一手信息载体标识
_SYSTEM_RULES = (
    "你是制药研发报告的行文助手，负责把已核实的事实写成报告正文。规则："
    "1) 只能使用给定的【已确认取值】与【补充信息】，禁止新增任何数字、日期、编号、单位或结论；"
    "2) 数字与单位保留原文写法，不得改写精度，不得自行计算合计或百分比；"
    "3) 表述客观、简洁、书面化，不要出现「根据资料」「经查询」「AI」等过程性措辞；"
    "4) 严格控制在给定字数上限内；"
    "5) 以「[待补充」「【AI草稿」「[材料冲突」开头的取值是占位或待定标记，必须原样保留在输出里；"
    "6) 没有事实可写的槽位，把 text 原样返回；"
    "7) 化学式（如 C18H19N5O2）、分子式、CAS 号、英文药名（INN 名称）等专业术语保留原文不翻译，"
    "不得改写或省略；其余英文描述性内容须翻译为中文书面语，不要保留英文原文；"
    "8) 只输出 JSON，不要解释。"
)


class ComposedSlot(BaseModel):
    """单个槽位的成文结果。"""

    key: str
    text: str = ""


class ComposeOut(BaseModel):
    """一批槽位的成文响应。"""

    slots: list[ComposedSlot] = Field(default_factory=list)


@dataclass(slots=True)
class ComposeStats:
    """成文过程统计（写进任务 stats，供生成说明与界面展示）。"""

    batches: int = 0
    calls: int = 0
    composed: int = 0
    # 因引入新数字或超字数而被丢弃的条数（数字守恒是硬约束，不做通融）
    rejected: int = 0
    failures: int = 0
    warnings: list[str] = field(default_factory=list)


def _extract_numbers(text: str) -> set[str]:
    """抽取数字 token（小数按原写法整体匹配，避免 0.50 被当成 0 与 50）。"""
    return set(re.findall(r"\d+(?:\.\d+)*", text or ""))


def _fact_lines(result: SlotResult, label: str) -> list[str]:
    """把一个槽位的已确认事实摊成 prompt 行（表格逐行给，不给整段 JSON）。"""
    lines: list[str] = []
    if result.text.strip():
        lines.append(f"{label}：{result.text.strip()}")
    for row in result.rows[:_MAX_PROMPT_ROWS]:
        cells = "；".join(f"{key}={value}" for key, value in row.items() if str(value).strip())
        if cells:
            lines.append(f"{label}·{cells}")
    return lines


def _allowed_numbers(facts: Iterable[str], supplement: str) -> set[str]:
    """成文允许出现的数字集合 = 已确认取值数字 ∪ 补充信息数字。"""
    allowed: set[str] = set()
    for text in (*facts, supplement):
        allowed |= _extract_numbers(text)
    return allowed


def _reject_reason(text: str, allowed: set[str], max_chars: int) -> str:
    """成文结果是否可用；返回拒绝原因，空串表示通过。"""
    if not text.strip():
        return "成文结果为空"
    if max_chars and len(text) > max_chars:
        return f"超出字数上限 {max_chars}（实际 {len(text)}）"
    missing = _extract_numbers(text) - allowed
    if missing:
        return f"引入未确认的数字 {sorted(missing)[:5]}"
    return ""


def _preserve_marks(composed: str, original: str) -> str:
    """占位/待定标记不得被成文吃掉。"""
    for mark in _KEEP_MARKS:
        if original.startswith(mark) and mark not in composed:
            return original
    return composed


def build_compose_prompt(
    slots: Sequence[Slot],
    results: Mapping[str, SlotResult],
    *,
    supplement: str = "",
    section_titles: Mapping[str, str] | None = None,
    max_context_chars: int = 12000,
) -> tuple[list[dict[str, str]], list[str]]:
    """构造一批槽位的成文 prompt，同时返回实际参与成文的槽位 key。"""
    blocks: list[str] = []
    keys: list[str] = []
    for slot in slots:
        result = results.get(slot.key)
        if result is None or result.state not in COMPOSABLE_STATES:
            continue
        facts = _fact_lines(result, slot.label)
        if not facts:
            continue
        section_key, _ = split_slot_key(slot.key)
        title = (section_titles or {}).get(section_key or "")
        heading = f"【{title}】" if title else ""
        blocks.append(f"{heading}key={slot.key} 名称={slot.label} 字数上限={slot.max_chars}\n" + "\n".join(facts))
        keys.append(slot.key)
    if not blocks:
        return [], []
    schema = {"slots": [{"key": "槽位 key", "text": "成文后的正文"}]}
    supplement_block = f"\n【补充信息】\n{supplement[: max(0, max_context_chars)]}\n" if supplement else ""
    user = (
        "请把下列每个槽位的已确认取值改写成报告正文（一到数句、连贯书面化）：\n\n"
        + "\n\n".join(blocks)
        + "\n"
        + supplement_block
        + f"必须为每个 key 各返回一条结果，key 只能是 {json.dumps(keys, ensure_ascii=False)}。输出结构示例：\n"
        + json.dumps(schema, ensure_ascii=False)
    )
    return [{"role": "system", "content": _SYSTEM_RULES}, {"role": "user", "content": user}], keys


@dataclass
class ComposeOutcome:
    """成文结果：被改写过文本的槽位（含成文前原文）与过程统计。"""

    results: dict[str, SlotResult] = field(default_factory=dict)
    stats: ComposeStats = field(default_factory=ComposeStats)


async def compose_results(
    slots: Sequence[Slot],
    results: Mapping[str, SlotResult],
    *,
    supplement: str = "",
    section_titles: Mapping[str, str] | None = None,
    llm: Any = None,
    llm_kwargs: Mapping[str, Any] | None = None,
    batch_size: int = 5,
    max_context_chars: int = 12000,
    timeout_seconds: float | None = None,
    should_cancel: Callable[[], bool] | None = None,
    max_concurrent_batches: int = 1,
) -> ComposeOutcome:
    """按批成文；返回的字典只包含真正改写了文本的槽位。

    原确认文本存进 ``SlotResult.pre_compose_text``，供人工对照与成文失败回退。
    ``max_concurrent_batches > 1`` 时多批并发调用 LLM，加速成文阶段。
    """
    client = llm or llm_client
    call_kwargs = dict(llm_kwargs or {})
    outcome = ComposeOutcome()
    targets = [slot for slot in slots if slot.key in results and results[slot.key].state in COMPOSABLE_STATES]
    batches = [targets[start : start + max(1, batch_size)] for start in range(0, len(targets), max(1, batch_size))]

    async def _process_batch(batch: list[Slot]) -> None:
        if should_cancel is not None and should_cancel():
            return
        messages, keys = build_compose_prompt(
            batch,
            results,
            supplement=supplement,
            section_titles=section_titles,
            max_context_chars=max_context_chars,
        )
        if not keys:
            return
        outcome.stats.batches += 1
        raw = await _call(client, messages, call_kwargs, timeout_seconds)
        if raw is None:
            outcome.stats.failures += 1
            return
        outcome.stats.calls += 1
        _apply_batch(raw, keys, batch, results, outcome, supplement)

    if max_concurrent_batches <= 1:
        for batch in batches:
            if should_cancel is not None and should_cancel():
                outcome.stats.warnings.append("成文已终止，未完成部分保留人工确认文本")
                break
            await _process_batch(batch)
    else:
        sem = asyncio.Semaphore(max_concurrent_batches)

        async def _guarded(batch: list[Slot]) -> None:
            async with sem:
                await _process_batch(batch)

        await asyncio.gather(*(_guarded(b) for b in batches))
        if should_cancel is not None and should_cancel():
            outcome.stats.warnings.append("成文已终止，未完成部分保留人工确认文本")
    return outcome


async def _call(
    client: Any,
    messages: list[dict[str, str]],
    llm_kwargs: Mapping[str, Any],
    timeout_seconds: float | None,
) -> dict[str, Any] | None:
    """一次成文调用；失败按降级返回 None（成文是增强项，不抛业务异常）。"""
    try:
        call = client.chat_json(messages, expected_keys=["slots"], temperature=0.2, **dict(llm_kwargs))
        raw = await asyncio.wait_for(call, timeout=timeout_seconds) if timeout_seconds else await call
        return ComposeOut.model_validate(raw).model_dump()
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001 - 网络/超时/输出不合规一律降级保留原文
        logger.warning("成文模型调用失败，该批保留人工确认文本", extra={"error": type(exc).__name__})
        return None


def _apply_batch(
    raw: Mapping[str, Any],
    keys: Sequence[str],
    batch: Sequence[Slot],
    results: Mapping[str, SlotResult],
    outcome: ComposeOutcome,
    supplement: str,
) -> None:
    """校验并采用成文结果；不合规则的槽位保持人工确认文本。"""
    slot_by_key = {slot.key: slot for slot in batch}
    for item in raw.get("slots") or []:
        key = str(item.get("key") or "")
        slot = slot_by_key.get(key)
        if slot is None or key not in set(keys) or key in outcome.results:
            continue
        original = results[key]
        text = re.sub(r"[ \t]+\n", "\n", str(item.get("text") or "")).strip()
        facts = _fact_lines(original, slot.label)
        reason = _reject_reason(text, _allowed_numbers(facts, supplement), slot.max_chars)
        if reason:
            outcome.stats.rejected += 1
            outcome.stats.warnings.append(f"槽位 {key} 未采用成文结果：{reason}")
            continue
        # 重跑成文时保留最早的人工确认原文，pre_compose_text 不被上一次的成文结果覆盖
        outcome.results[key] = replace(
            original,
            text=_preserve_marks(text, original.text),
            pre_compose_text=original.pre_compose_text or original.text,
        )
        outcome.stats.composed += 1
