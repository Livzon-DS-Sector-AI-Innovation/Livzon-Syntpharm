"""三层判定引擎（需求文档 F3）。

规则：
1. 没有实测值 → 待检（pending），不参与整批汇总
2. 等级型项目（溶液颜色、澄清度这类）→ 仅记录（skip），不自动变色
3. 文字型项目 → 出现「不符合 / 不呈 / 不合格 / 未通过」即超法定，否则正常
4. 数值型项目 → 依次比 法定 → 内控 → 3σ，命中即停；某层无标准自动跳过
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from app.modules.quality.qc_report.constants import (
    LEVEL_INTERNAL,
    LEVEL_NORMAL,
    LEVEL_OOS,
    LEVEL_PENDING,
    LEVEL_PRIORITY,
    LEVEL_SKIP,
    LEVEL_TREND,
    NEGATIVE_KEYWORDS,
    VALUE_TYPE_GRADE,
    VALUE_TYPE_QUANT,
)
from app.modules.quality.qc_report.service.limits import (
    INACTIVE_LIMIT,
    LimitRange,
    parse_limit,
    to_number,
)


@dataclass(frozen=True)
class JudgeItem:
    """判定所需的项目快照（不依赖 ORM，便于单测）。"""

    item_name: str
    value_type: str
    legal_text: str | None = None
    internal_text: str | None = None
    sigma_text: str | None = None
    is_record_only: bool = False


@dataclass(frozen=True)
class ItemLimits:
    """预先解析好的三层区间，避免每个单元格重复解析。"""

    legal: LimitRange = INACTIVE_LIMIT
    internal: LimitRange = INACTIVE_LIMIT
    sigma: LimitRange = INACTIVE_LIMIT


@dataclass(frozen=True)
class JudgeResult:
    """单格判定结果。"""

    level: str
    numeric_value: float | None = None


def compile_item_limits(item: JudgeItem) -> ItemLimits:
    """按项目解析一次三层标准，供整批数据复用。"""
    return ItemLimits(
        legal=parse_limit(item.legal_text),
        internal=parse_limit(item.internal_text),
        sigma=parse_limit(item.sigma_text),
    )


def has_negative_words(actual: str | None) -> bool:
    if not actual:
        return False
    return any(keyword in actual for keyword in NEGATIVE_KEYWORDS)


def judge_value(item: JudgeItem, actual: str | None, limits: ItemLimits | None = None) -> JudgeResult:
    """判定单个单元格。"""
    text = (actual or "").strip()
    if not text:
        return JudgeResult(level=LEVEL_PENDING)

    if item.is_record_only or item.value_type == VALUE_TYPE_GRADE:
        return JudgeResult(level=LEVEL_SKIP)

    if item.value_type == VALUE_TYPE_QUANT:
        number = to_number(text)
        if number is None:
            # 数值型项目录了文字：按文字规则兜底，避免「符合规定」被判成待检
            level = LEVEL_OOS if has_negative_words(text) else LEVEL_NORMAL
            return JudgeResult(level=level)
        ranges = limits or compile_item_limits(item)
        if ranges.legal.is_active and not ranges.legal.contains(number):
            return JudgeResult(level=LEVEL_OOS, numeric_value=number)
        if ranges.internal.is_active and not ranges.internal.contains(number):
            return JudgeResult(level=LEVEL_INTERNAL, numeric_value=number)
        if ranges.sigma.is_active and not ranges.sigma.contains(number):
            return JudgeResult(level=LEVEL_TREND, numeric_value=number)
        return JudgeResult(level=LEVEL_NORMAL, numeric_value=number)

    # 文字型项目
    level = LEVEL_OOS if has_negative_words(text) else LEVEL_NORMAL
    return JudgeResult(level=level)


def aggregate_level(levels: Iterable[str]) -> str:
    """整批最高等级：待检与仅记录不计入；全为待检时返回待检。"""
    best = LEVEL_SKIP
    best_priority = -2
    saw_pending = False
    for level in levels:
        if level == LEVEL_PENDING:
            saw_pending = True
            continue
        if level == LEVEL_SKIP:
            continue
        priority = LEVEL_PRIORITY.get(level, -2)
        if priority > best_priority:
            best, best_priority = level, priority
    if best_priority >= 0:
        return best
    return LEVEL_PENDING if saw_pending else LEVEL_SKIP


__all__ = [
    "ItemLimits",
    "JudgeItem",
    "JudgeResult",
    "aggregate_level",
    "compile_item_limits",
    "has_negative_words",
    "judge_value",
]
