"""表格计算列：所有算术一律在代码里做，禁止让模型算数。"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")
_NON_NUM = re.compile(r"[^\d.\-]")


def to_number(text: str) -> Decimal | None:
    """从文本中取第一个数字（容忍千分位、单位、百分号）。"""
    if not text:
        return None
    match = _NUM_RE.search(text.replace(",", "").replace("，", ""))
    if not match:
        return None
    try:
        return Decimal(match.group())
    except InvalidOperation:
        return None


def format_number(value: Decimal, digits: int = 2) -> str:
    """去掉多余的小数 0。"""
    quantized = value.quantize(Decimal(1).scaleb(-digits))
    text = f"{quantized:f}".rstrip("0")
    return text.rstrip(".") or "0"


def product(values: list[Decimal | None]) -> Decimal | None:
    """操作数相乘；任一操作数缺失返回 None。"""
    result = Decimal(1)
    for value in values:
        if value is None:
            return None
        result *= value
    return result


def sum_values(values: list[Decimal | None]) -> Decimal | None:
    """求和；全空返回 None。"""
    present = [v for v in values if v is not None]
    if not present:
        return None
    total = Decimal(0)
    for value in present:
        total += value
    return total


def percent(part: Decimal | None, total: Decimal | None, digits: int = 2) -> str:
    """占比百分数字符串。"""
    if part is None or not total:
        return ""
    return f"{format_number(part / total * Decimal(100), digits)}%"


def strip_units(text: str) -> str:
    """只保留数字与小数点/负号（用于校验数值型输出）。"""
    return _NON_NUM.sub("", text or "")


__all__ = ["format_number", "percent", "product", "strip_units", "sum_values", "to_number"]
