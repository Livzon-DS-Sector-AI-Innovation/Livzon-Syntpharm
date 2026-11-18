"""讲稿覆盖度自检：页面上的要点到底有没有被讲到。

为什么需要
--------
AI 讲稿受「单页段数上限 + 送模文本长度」约束，长页容易被压成几句摘要，成片里表现为
「这页没讲完就翻页」。这里用页面元素文本与讲稿做字面重合度比对，给出覆盖率与漏讲清单，
让问题在页面上可见，并支持一键补全。

口径
----
- 只算有文字的元素（含表格单元格），装饰形状不参与；
- 单个元素按 2-gram 重合率判断「讲到」，默认 0.6；
- 覆盖率 = 已讲到元素的文字长度权重 / 全部元素文字长度权重（0~1）；
- 漏讲清单按视觉阅读顺序给出，便于「按顺序补讲」。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.modules.agent.alignment import normalize_text, reading_order
from app.modules.agent.highlight import iter_elements

#: 元素文字少于这个长度不参与判断（「-」「1」这类没有语义）
MIN_ELEMENT_CHARS = 2
#: 漏讲清单最多返回几条，避免长表格把界面撑爆
MAX_MISSING = 10
#: 清单里每条要点保留的字符数
MISSING_TEXT_CHARS = 40
_NON_WORD_RE = re.compile(r"[\s\W_]+", re.UNICODE)


@dataclass(frozen=True)
class CoverageResult:
    """一次覆盖度检查的结果。"""

    #: 0~1，按元素文字长度加权
    score: float
    #: 漏讲要点摘要（阅读顺序，最多 MAX_MISSING 条）
    missing: list[str]
    #: 是否有可判断的内容（纯图片页 / 空讲稿为 False）
    checked: bool


def values_for(script_text: str | None, layout: Any, *, element_threshold: float = 0.6) -> dict[str, Any]:
    """覆盖度 → 数据库 UPDATE 的值；未检查时写空，避免留下过期结论。

    AI 写入、改写写入、手工保存三条路径共用这一份，别在调用方各自拼。
    """
    result = compute_coverage(script_text, layout, element_threshold=element_threshold)
    if not result.checked:
        return {"coverage_score": None, "coverage_missing": None, "coverage_checked_at": None}
    return {
        "coverage_score": result.score,
        "coverage_missing": result.missing or None,
        "coverage_checked_at": datetime.now(UTC),
    }


def _bigrams(text: str) -> set[str]:
    clean = _NON_WORD_RE.sub("", normalize_text(text))
    if len(clean) < 2:
        return {clean} if clean else set()
    return {clean[i : i + 2] for i in range(len(clean) - 1)}


def _summary(text: str) -> str:
    collapsed = re.sub(r"\s+", " ", text).strip()
    return collapsed[:MISSING_TEXT_CHARS] + ("…" if len(collapsed) > MISSING_TEXT_CHARS else "")


def compute_coverage(
    script_text: str | None,
    layout: Any,
    *,
    element_threshold: float = 0.6,
    max_missing: int = MAX_MISSING,
) -> CoverageResult:
    """按页面元素清单检查讲稿覆盖度。"""
    elements = [ref for ref in iter_elements(layout) if len(normalize_text(ref.text)) >= MIN_ELEMENT_CHARS]
    if not elements or not (script_text or "").strip():
        return CoverageResult(score=0.0, missing=[], checked=False)

    script_grams = _bigrams(script_text or "")
    ordered = reading_order(elements, lambda ref: (ref.box.left, ref.box.top, ref.box.width, ref.box.height))

    covered_weight = 0
    total_weight = 0
    missing: list[str] = []
    for ref in ordered:
        text = normalize_text(ref.text)
        weight = max(1, len(text))
        total_weight += weight
        grams = _bigrams(text)
        coverage = len(grams & script_grams) / len(grams) if grams else 0.0
        if coverage >= element_threshold:
            covered_weight += weight
        elif len(missing) < max_missing:
            missing.append(_summary(ref.text))

    score = round(covered_weight / total_weight, 4) if total_weight else 0.0
    return CoverageResult(score=score, missing=missing, checked=True)
