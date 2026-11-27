"""限值文本解析：把标准原文转成可比对的区间。

设计原则：**解析不出来不算错**。返回 `kind="none"` 表示该层无标准，
判定时跳过这一层，绝不因为一条奇怪的标准而阻塞整批导入。

支持的写法（全部来自真实样本）：
- `8.0%～11.0%`          → 区间
- `-153°～-170°`         → 反向区间，自动摆正为 [-170, -153]
- `≤0.5%` / `＜0.20EU/mg` → 上限
- `≥84.0%`               → 下限
- `≥10µm：应≤6000粒/g`    → 复合表述，取最后一段的上限
- `应不得过百万分之二十`    → 中文分数 → 20 ppm
- `517` 这类单值          → 视为无判定范围（目标值），不参与超限判断
- `应符合规定` / `不得浓于1号浊度标准液` → 无数字，按文字判定处理
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass

from app.modules.quality.qc_report.constants import (
    CN_FRACTION_PATTERN,
    CN_FRACTION_SCALE,
    GRADE_PATTERN,
    INTERVAL_PATTERN,
    LOWER_PATTERN,
    NO_STANDARD_TEXTS,
    PLAIN_NUMBER_PATTERN,
    QUAL_PATTERN,
    UPPER_PATTERN,
    VALUE_TYPE_GRADE,
    VALUE_TYPE_QUAL,
    VALUE_TYPE_QUANT,
)

logger = logging.getLogger(__name__)

KIND_INTERVAL = "interval"
KIND_UPPER = "upper"
KIND_LOWER = "lower"
KIND_NONE = "none"

_CN_DIGITS = {
    "零": 0,
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}


@dataclass(frozen=True)
class LimitRange:
    """某一层标准的数值区间。`kind="none"` 表示不参与判定。"""

    kind: str
    lower: float | None = None
    upper: float | None = None

    @property
    def is_active(self) -> bool:
        return self.kind != KIND_NONE and (self.lower is not None or self.upper is not None)

    def contains(self, value: float) -> bool:
        """是否在范围内；未设边界的一侧视为不限。"""
        if not self.is_active:
            return True
        if self.lower is not None and value < self.lower:
            return False
        if self.upper is not None and value > self.upper:
            return False
        return True


INACTIVE_LIMIT = LimitRange(kind=KIND_NONE)


def _cn_to_int(text: str) -> int | None:
    """中文数字转整数，覆盖 1–999 的常见写法。"""
    text = text.strip()
    if not text:
        return None
    if text.isdigit():
        return int(text)
    if "十" in text:
        head, _, tail = text.partition("十")
        tens = _CN_DIGITS.get(head, 1) if head else 1
        ones = _CN_DIGITS.get(tail, 0) if tail else 0
        return tens * 10 + ones
    if "百" in text:
        head, _, tail = text.partition("百")
        hundreds = _CN_DIGITS.get(head, 1) if head else 1
        rest = 0
        if tail:
            rest = _cn_to_int(tail) or 0
        return hundreds * 100 + rest
    total = 0
    for char in text:
        if char not in _CN_DIGITS:
            return None
        total = total * 10 + _CN_DIGITS[char]
    return total


def _parse_cn_fraction(text: str) -> float | None:
    """`百万分之二十` → 20（按 ppm 记）；`万分之三` → 300。"""
    match = CN_FRACTION_PATTERN.search(text)
    if not match:
        return None
    unit, number_text = match.group(1), match.group(2)
    number = _cn_to_int(number_text)
    if number is None:
        return None
    scale = CN_FRACTION_SCALE.get(unit)
    if scale is None:
        return None
    return float(number) * scale


def _to_float(text: str) -> float | None:
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    return value


_TILDE_PATTERN = re.compile(r"[~～－—至]")


def normalize_standard_text(text: str | None) -> str | None:
    """把反向书写的区间摆正，只改写法、不改判定。

    样本里存在 `0.5～0.0`（= ≤0.5）、`10.1～8.5`、`Y4.5/…～Y2.0/…` 这类倒着写的区间，
    判定层已用 min/max 校正，但存库与界面上看着别扭，入库前统一摆正。

    只处理「区间」写法；`≤0.6%`、`符合规定`、`517` 等一律原样返回。
    """
    if is_empty_standard(text):
        return text
    raw = (text or "").strip()

    # 只认波浪号一类分隔符，不用 ASCII 连字符：`-153°～-170°` 里的 `-` 是负号。
    # 以分隔符为界整体切分，让单位（°、%、℃）跟着各自的数值走，
    # 否则交换后会出现 `-170°°～-153` 这种残句。
    separator_match = _TILDE_PATTERN.search(raw)
    if separator_match is None:
        return text

    left_segment = raw[: separator_match.start()].strip()
    right_segment = raw[separator_match.end() :].strip()
    left_value = _last_number(left_segment)
    right_value = _first_number(right_segment)
    if left_value is None or right_value is None or left_value <= right_value:
        return text

    separator = separator_match.group(0)
    return f"{right_segment}{separator}{left_segment}"


def _first_number(text: str) -> float | None:
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    return _to_float(match.group(0)) if match else None


def _last_number(text: str) -> float | None:
    matches = re.findall(r"-?\d+(?:\.\d+)?", text)
    return _to_float(matches[-1]) if matches else None


def is_empty_standard(text: str | None) -> bool:
    """该层是否等同于「没有标准」。"""
    if text is None:
        return True
    stripped = text.strip()
    if not stripped:
        return True
    if stripped in NO_STANDARD_TEXTS:
        return True
    return stripped.startswith("未作规定")


def parse_limit(text: str | None) -> LimitRange:
    """把标准原文解析成区间。解析不出返回 INACTIVE_LIMIT。"""
    if is_empty_standard(text):
        return INACTIVE_LIMIT
    raw = (text or "").strip()

    # 1) 中文分数（"应不得过百万分之二十"）
    fraction = _parse_cn_fraction(raw)
    if fraction is not None:
        return LimitRange(kind=KIND_UPPER, upper=fraction)

    # 2) 区间（含反向区间与带空格的写法）
    interval = INTERVAL_PATTERN.search(raw)
    if interval:
        first = _to_float(interval.group(1))
        second = _to_float(interval.group(2))
        if first is not None and second is not None:
            lower, upper = min(first, second), max(first, second)
            return LimitRange(kind=KIND_INTERVAL, lower=lower, upper=upper)

    # 3) 上限（取最靠后的一段，兼容「≥10µm：应≤6000粒/g」）
    upper_matches = list(UPPER_PATTERN.finditer(raw))
    if upper_matches:
        upper_value = _to_float(upper_matches[-1].group(1))
        if upper_value is not None:
            return LimitRange(kind=KIND_UPPER, upper=upper_value)

    # 4) 下限
    lower_matches = list(LOWER_PATTERN.finditer(raw))
    if lower_matches:
        lower_value = _to_float(lower_matches[-1].group(1))
        if lower_value is not None:
            return LimitRange(kind=KIND_LOWER, lower=lower_value)

    # 5) 纯数字单值：没有上下边界，视为目标值不判定
    if PLAIN_NUMBER_PATTERN.match(raw):
        logger.debug("qc_report limit is a single value, treated as no range: %s", raw)
        return INACTIVE_LIMIT

    return INACTIVE_LIMIT


def infer_value_type(
    legal_text: str | None,
    internal_text: str | None,
    sigma_text: str | None,
    record_only: bool = False,
) -> str:
    """根据三层标准原文推断项目类型。

    判定顺序：能解析出数值区间 → 数值型；含色号/深浅特征 → 等级型；否则文字型。
    不直接信任标准表里的「类型」列（样本里细菌内毒素被标成文本，标准却是 ＜0.20）。
    """
    if record_only:
        return VALUE_TYPE_QUANT

    for text in (legal_text, internal_text, sigma_text):
        if text and parse_limit(text).is_active:
            return VALUE_TYPE_QUANT

    for text in (legal_text, internal_text, sigma_text):
        if text and GRADE_PATTERN.search(text):
            return VALUE_TYPE_GRADE

    joined = " ".join(t for t in (legal_text, internal_text, sigma_text) if t)
    if joined and QUAL_PATTERN.search(joined):
        return VALUE_TYPE_QUAL

    # 完全没有可识别标准：按文字处理（不变色，只记录）
    return VALUE_TYPE_QUAL


def to_number(value: str | None) -> float | None:
    """实测值转数值；`符合规定`、`未检出` 等返回 None。"""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("＜", "<").replace("＞", ">").replace("％", "%")
    # 去掉比较符与单位后缀，只留数字
    cleaned = text.replace("<", " ").replace(">", " ").replace("≤", " ").replace("≥", " ")
    cleaned = cleaned.replace("%", " ").replace("＋", "+").replace("－", "-")
    cleaned = cleaned.strip()
    if not cleaned:
        return None
    head = cleaned.split()[0] if cleaned.split() else ""
    number = _to_float(head)
    if number is not None:
        return number
    # 还不行就尝试整段是数字
    return _to_float(cleaned)


__all__ = [
    "KIND_INTERVAL",
    "KIND_UPPER",
    "KIND_LOWER",
    "KIND_NONE",
    "INACTIVE_LIMIT",
    "LimitRange",
    "infer_value_type",
    "is_empty_standard",
    "normalize_standard_text",
    "parse_limit",
    "to_number",
]
