"""页内视觉引导：把讲稿按句切开，逐句高亮页面上对应的区域。

接口只有两个：`build_plan()` 产出分段时间轴，`plan_signature()` 产出缓存指纹。

三条刻意的取舍：

1. **不动 PPT、不解析动画**。画面用的是同一张静帧，只叠「压暗 + 提亮/描边」，
   PPT 动画（`p:timing`）复杂到无法可靠还原，投入产出比极低。
2. **不依赖 TTS 时间戳**。按字数加权切分总时长，误差几百毫秒观众无感，
   换来的是不需要改动 TTS 引擎与音频格式。
3. **字面命中才高亮**。不靠 LLM 输出坐标（模型给的坐标不可信），
   命中不了就整页常亮，宁可不亮也不能亮错。

纯函数、无 IO，可直接单测。
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

from app.modules.agent.alignment import normalize_text

#: 句末标点：优先按这些切分
_SENTENCE_END_RE = re.compile(r"(?<=[。！？!?；;\n])")
#: 次级标点：句子过长时再按逗号切
_CLAUSE_RE = re.compile(r"(?<=[，,、：:])")

#: 单句超过这个字数就尝试按逗号二次切分
LONG_SENTENCE_CHARS = 28
#: 形状文字被判定为「被讲到」的最低字符覆盖率
SHAPE_HIT_COVERAGE = 0.6


@dataclass(frozen=True)
class HighlightBox:
    """一个需要高亮的区域，坐标为 EMU，相对整页。"""

    left: int
    top: int
    width: int
    height: int


@dataclass(frozen=True)
class HighlightStep:
    """一段画面：在 [start_ms, end_ms) 内高亮 boxes 指定的区域。"""

    text: str
    start_ms: int
    end_ms: int
    boxes: list[HighlightBox] = field(default_factory=list)

    @property
    def duration_ms(self) -> int:
        return max(0, self.end_ms - self.start_ms)


@dataclass(frozen=True)
class HighlightPlan:
    """一页的完整引导计划。steps 覆盖整段旁白时长。"""

    steps: list[HighlightStep]
    total_ms: int

    @property
    def has_boxes(self) -> bool:
        return any(step.boxes for step in self.steps)


def iter_shapes(layout: Any) -> list[dict[str, Any]]:
    """layout 允许两种形态：纯形状列表，或 {width,height,shapes} 字典。"""
    if isinstance(layout, dict):
        shapes = layout.get("shapes")
        return [s for s in shapes if isinstance(s, dict)] if isinstance(shapes, list) else []
    if isinstance(layout, list):
        return [s for s in layout if isinstance(s, dict)]
    return []


def slide_size(layout: Any) -> tuple[int, int] | None:
    """取页面尺寸（EMU）。缺失时返回 None，调用方退化为整页常亮。"""
    if isinstance(layout, dict):
        try:
            width = int(layout.get("width") or 0)
            height = int(layout.get("height") or 0)
        except (TypeError, ValueError):
            return None
        if width > 0 and height > 0:
            return width, height
    return None


def split_sentences(text: str, max_steps: int = 6) -> list[str]:
    """按标点切句；句子过长再按逗号切，最后按需合并过短的句子。"""
    normalized = normalize_text(text)
    if not normalized:
        return []

    raw: list[str] = []
    for sentence in _SENTENCE_END_RE.split(normalized):
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) > LONG_SENTENCE_CHARS:
            clauses = [c.strip() for c in _CLAUSE_RE.split(sentence) if c.strip()]
            raw.extend(clauses or [sentence])
        else:
            raw.append(sentence)

    if not raw:
        return []

    # 过短的句子（<6 字）向相邻句合并，避免画面高频闪烁
    merged: list[str] = []
    for sentence in raw:
        if merged and len(sentence) < 6 and len(merged[-1]) + len(sentence) <= LONG_SENTENCE_CHARS * 2:
            merged[-1] = merged[-1] + sentence
        else:
            merged.append(sentence)

    # 超过 max_steps 时按长度均分合并（保留顺序）
    while len(merged) > max(1, max_steps):
        index = min(range(len(merged) - 1), key=lambda i: len(merged[i]) + len(merged[i + 1]))
        merged[index : index + 2] = [merged[index] + merged[index + 1]]

    return merged


def _bigrams(text: str) -> set[str]:
    clean = re.sub(r"[\s\W_]+", "", normalize_text(text))
    if len(clean) < 2:
        return {clean} if clean else set()
    return {clean[i : i + 2] for i in range(len(clean) - 1)}


def match_shapes(sentence: str, layout: Any) -> list[HighlightBox]:
    """按字符重合度匹配被讲到的形状；命中不到返回空列表。"""
    sentence_grams = _bigrams(sentence)
    if not sentence_grams:
        return []

    boxes: list[HighlightBox] = []
    for shape in iter_shapes(layout):
        shape_text = normalize_text(str(shape.get("text") or ""))
        if len(shape_text) < 2:
            continue
        grams = _bigrams(shape_text)
        if not grams:
            continue
        coverage = len(grams & sentence_grams) / len(grams)
        if coverage < SHAPE_HIT_COVERAGE:
            continue
        try:
            left = int(shape.get("left") or 0)
            top = int(shape.get("top") or 0)
            width = int(shape.get("width") or 0)
            height = int(shape.get("height") or 0)
        except (TypeError, ValueError):
            continue
        if width <= 0 or height <= 0:
            continue
        boxes.append(
            HighlightBox(
                # 外扩一点边距，避免描边压到文字
                left=max(0, left - 60000),
                top=max(0, top - 40000),
                width=width + 120000,
                height=height + 80000,
            )
        )
    return boxes


def build_plan(
    script_text: str,
    layout: Any,
    duration_ms: int,
    max_steps: int = 6,
) -> HighlightPlan:
    """按句切分并分配时长。

    时长按字符数加权，保证各段之和严格等于 `duration_ms`（末段吃掉取整余数），
    这样音频与画面的总长完全对齐，不会出现片段累加漂移。
    """
    duration_ms = max(0, duration_ms)
    sentences = split_sentences(script_text, max_steps)
    if not sentences or duration_ms <= 0:
        return HighlightPlan(steps=[], total_ms=duration_ms)

    weights = [max(1, len(sentence)) for sentence in sentences]
    total_weight = sum(weights)

    steps: list[HighlightStep] = []
    cursor = 0
    for index, sentence in enumerate(sentences):
        if index == len(sentences) - 1:
            end = duration_ms
        else:
            end = cursor + int(duration_ms * weights[index] / total_weight)
        steps.append(
            HighlightStep(
                text=sentence,
                start_ms=cursor,
                end_ms=max(cursor, end),
                boxes=match_shapes(sentence, layout),
            )
        )
        cursor = end

    return HighlightPlan(steps=steps, total_ms=duration_ms)


def plan_signature(plan: HighlightPlan) -> str:
    """视觉指纹：句子切分与高亮框任何变化都要让缓存失效。"""
    raw = "|".join(
        f"{step.start_ms}-{step.end_ms}:{','.join(f'{b.left},{b.top},{b.width},{b.height}' for b in step.boxes)}"
        for step in plan.steps
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def visual_fingerprint(plan: HighlightPlan, layout: Any, style: str) -> str:
    """片段缓存用的视觉指纹 = 分句映射 + 页面布局 + 高亮样式。

    只算 `plan_signature` 不够：同一句话换个样式（压暗/描边）或页面布局挪了位置，
    画面其实变了但句子时间轴没变，旧片段会被原样复用、高亮静默失效。
    """
    layout_raw = "|".join(
        f"{shape.get('left')},{shape.get('top')},{shape.get('width')},{shape.get('height')}"
        for shape in iter_shapes(layout)
    )
    raw = f"visual\n{plan_signature(plan)}\n{style}\n{layout_raw}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
