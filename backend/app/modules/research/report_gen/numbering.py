"""目录编号解析与顺延：不绑定某一种标题写法或某一个模板。

报告母本的目录编号常见几种形态，新增子标题后都要能接着往下排：

- 阿拉伯多级：``4.4. 路线4``、``4.4 路线4``、``4、路线4``；
- 中文序号：``四、路线4``、``（四）路线4``、``第四章 工艺路线``；
- 括号阿拉伯：``(4) 路线4``、``（4）路线4``。

这里把「编号 token」拆成前缀 / 数值分量 / 后缀 / 分隔符，顺延时只动数值，
前后缀与分隔符原样保留；识别不了就返回 ``None``，由调用方保持原样、不伪造编号。
纯函数，工具层（剥模型自带的编号）与渲染层（目录条目顺延）共用。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_CN_DIGITS = "零一二三四五六七八九"
_CN_UNITS = {"十": 10, "百": 100, "千": 1000}

# 第四章 / 第4章 / 第四节
_CHAPTER_RE = re.compile(
    r"^(?P<head>第)(?P<num>[0-9]+|[一二三四五六七八九十百千]+)(?P<tail>[章节部分篇])(?P<separator>\s*)"
)
# （四） / (4) / （4.2） / (4.2)
_PAREN_RE = re.compile(
    r"^(?P<head>[（(])(?P<num>[0-9]+(?:[.．][0-9]+)*|[一二三四五六七八九十百千]+)(?P<tail>[）)])(?P<separator>\s*)"
)
# 4.4. / 4、 / 四、 / 一 概述
_PLAIN_RE = re.compile(r"^(?P<num>[0-9]+(?:[.．][0-9]+)*|[一二三四五六七八九十百千]+)(?P<separator>[、.．]?\s*)")


@dataclass(slots=True)
class NumberToken:
    """一个编号 token：``（四）路线4`` → 前缀 ``（``、数值 ``[4]``、后缀 ``）``。"""

    head: str
    parts: list[int]
    tail: str
    separator: str
    chinese: bool
    # 编号 token（含前后缀、不含分隔符）在原字符串里的结束位置，用于原地替换
    end: int

    def render(self) -> str:
        if self.chinese and len(self.parts) == 1:
            body = _int_to_chinese(self.parts[0])
        else:
            body = ".".join(str(part) for part in self.parts)
        return f"{self.head}{body}{self.tail}"


def _chinese_to_int(text: str) -> int | None:
    if not text:
        return None
    if text.isdigit():
        return int(text)
    total = 0
    current = 0
    for char in text:
        if char in _CN_DIGITS:
            current = _CN_DIGITS.index(char)
        elif char in _CN_UNITS:
            total += (current or 1) * _CN_UNITS[char]
            current = 0
        else:
            return None
    return total + current


def _int_to_chinese(value: int) -> str:
    """1..9999 → 中文序号；超出范围退回阿拉伯数字，避免造出奇怪的字。"""
    if value < 0:
        return str(value)
    if value < 10:
        return _CN_DIGITS[value]
    if value < 20:
        return "十" + (_CN_DIGITS[value % 10] if value % 10 else "")
    if value < 100:
        tens, ones = divmod(value, 10)
        return _CN_DIGITS[tens] + "十" + (_CN_DIGITS[ones] if ones else "")
    if value < 1000:
        hundreds, rest = divmod(value, 100)
        text = f"{_CN_DIGITS[hundreds]}百"
        if rest:
            text += ("零" if rest < 10 else "") + _int_to_chinese(rest)
        return text
    if value < 10000:
        thousands, rest = divmod(value, 1000)
        text = f"{_CN_DIGITS[thousands]}千"
        if rest:
            text += ("零" if rest < 100 else "") + _int_to_chinese(rest)
        return text
    return str(value)


def _split_number(raw: str) -> tuple[list[int], bool] | None:
    if all(char.isdigit() or char in ".．" for char in raw):
        parts = [int(item) for item in re.split(r"[.．]", raw) if item]
        return (parts, False) if parts else None
    value = _chinese_to_int(raw)
    return ([value], True) if value is not None else None


def parse_number(text: str | None) -> NumberToken | None:
    """解析字符串开头的编号；没有编号或格式不认识时返回 ``None``。"""
    value = text or ""
    for pattern in (_CHAPTER_RE, _PAREN_RE, _PLAIN_RE):
        match = pattern.match(value)
        if match is None:
            continue
        split = _split_number(match.group("num"))
        if split is None:
            return None
        parts, chinese = split
        groups = match.groupdict()
        return NumberToken(
            head=groups.get("head") or "",
            parts=parts,
            tail=groups.get("tail") or "",
            separator=match.group("separator"),
            chinese=chinese,
            end=match.start("separator"),
        )
    return None


def bump_number(token: NumberToken) -> NumberToken | None:
    """编号末位加一：``4.4`` → ``4.5``、``四`` → ``五``。"""
    if not token.parts:
        return None
    parts = list(token.parts)
    parts[-1] += 1
    return NumberToken(
        head=token.head,
        parts=parts,
        tail=token.tail,
        separator=token.separator,
        chinese=token.chinese,
        end=token.end,
    )


def strip_number(text: str | None) -> str:
    """去掉开头的编号与分隔符：``4.5 路线5`` / ``（五）路线5`` → ``路线5``。"""
    value = text or ""
    token = parse_number(value)
    if token is None:
        return " ".join(value.split())
    # end 是编号 token 的结束位置（不含分隔符），剥离时要把「、」「. 」一并吃掉
    return " ".join(value[token.end + len(token.separator) :].split())


__all__ = ["NumberToken", "bump_number", "parse_number", "strip_number"]
