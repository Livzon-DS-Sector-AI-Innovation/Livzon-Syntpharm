"""页内视觉引导：把讲稿按段切开，逐段高亮页面上对应的区域。

接口分三层：

- `resolve_segments()`：讲稿 → 段序列（优先用落库的 `script_segments`，否则按标点切）；
- `build_plan_for_segments()`：段 + 各段真实音频时长 → 高亮时间轴；
- `parse_region_config()`：落库的区域配置（区域三态 + 句级微调）→ 已校验的规则；
- `plan_signature()`：缓存指纹。

三条刻意的取舍：

1. **不动 PPT、不解析动画**。画面用的是同一张静帧，只叠「压暗 + 提亮/描边」，
   PPT 动画（`p:timing`）复杂到无法可靠还原，投入产出比极低。
2. **时长靠逐段 TTS，不靠估算**。每段单独合成音频，段时间轴就是音频实测时长，
   不再按字数加权；估算只在「退回整页单段合成」时使用。
3. **目标由元素 id 指定，坐标永远来自解析结果**。讲稿生成时绑定元素 id，
   命中不了就整页常亮，宁可不亮也不能亮错。

纯函数、无 IO，可直接单测。
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from typing import Any

from app.modules.agent.alignment import normalize_text

#: 句末标点：优先按这些切分
_SENTENCE_END_RE = re.compile(r"(?<=[。！？!?；;\n])")
#: 次级标点：句子过长时再按逗号切
_CLAUSE_RE = re.compile(r"(?<=[，,、：:])")

#: 单句超过这个字数就尝试按逗号二次切分
LONG_SENTENCE_CHARS = 28
#: 形状文字被判定为「被讲到」的最低字符覆盖率（默认值，可被运行时配置覆盖）
SHAPE_HIT_COVERAGE = 0.6
#: 兜底猜测的字面重合度门槛：低于它宁可整页淡底，也不乱点亮一个元素
FALLBACK_GUESS_COVERAGE = 0.2
#: 页面级兜底的底色透明度（0-255）：够看出画面变化，又不至于糊住整页
PAGE_FALLBACK_FILL_ALPHA = 18
#: 句级静音的保留标记：`mute=["*"]` 表示这句完全不亮（兜底也压不住）
MUTE_WHOLE_SENTENCE = "*"
#: 高亮框外扩上限（EMU）：避免描边压到文字，同时不让小元素被撑得离谱
PAD_X_EMU = 60000
PAD_Y_EMU = 40000
#: 讲稿 prompt 里的元素清单上限与单个元素摘要长度
ELEMENT_CATALOG_MAX = 30
ELEMENT_TEXT_CHARS = 40
#: 区域三态：不参与高亮 / 只给文字变色 / 给整块区域铺底色
REGION_MODE_OFF = "off"
REGION_MODE_TEXT = "text"
REGION_MODE_AREA = "area"
REGION_MODES: tuple[str, ...] = (REGION_MODE_OFF, REGION_MODE_TEXT, REGION_MODE_AREA)
#: 手绘矩形在区域清单里的 id 前缀（`rect:0`），与 layout 元素 id 区分开
RECT_ID_PREFIX = "rect:"
#: 区域铺底色未显式指定透明度时的默认值（0-255，约 35%）
DEFAULT_REGION_FILL_ALPHA = 90
#: 单页区域条数与句级微调条数上限：一条 JSON 塞太多会把出帧拖慢
MAX_REGIONS = 60
MAX_SENTENCE_RULES = 40
#: 区域级主色只接受 #RRGGBB，非法值一律丢弃（坏颜色进渲染只会把画面染脏）
_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
#: 只有这些类型允许「无文字也进清单」，装饰性空形状不进 prompt
_VISUAL_KINDS = ("PICTURE", "TABLE", "CHART", "GROUP", "MEDIA")
_KIND_LABELS = {
    "TEXT_BOX": "文本框",
    "AUTO_SHAPE": "形状",
    "PLACEHOLDER": "占位符",
    "PICTURE": "图片",
    "TABLE": "表格",
    "CHART": "图表",
    "GROUP": "组合",
    "GRAPHIC_FRAME": "表格/图表",
    "CELL": "单元格",
    "LINE": "线条",
    "FREEFORM": "图形",
}


@dataclass(frozen=True)
class HighlightBox:
    """一个需要高亮的区域，坐标为 EMU，相对整页。

    `kind` 是元素类型前缀（`TEXT_BOX`、`PICTURE`、`CELL` …），出帧时据此决定
    「文字染色」还是「只描边」：图片/图表整块染色会糊成红色剪影。
    """

    left: int
    top: int
    width: int
    height: int
    kind: str = "TEXT_BOX"
    #: 区域级效果覆盖：空 = 跟随页级样式；`text` 只染字、`area` 铺底色、`off` 不参与
    mode: str = ""
    #: 该区域自己的主色（#RRGGBB）；空 = 跟随页级颜色
    color: str | None = None
    #: `area` 档的底色透明度（0-255）；空 = 用 `DEFAULT_REGION_FILL_ALPHA`
    fill_alpha: int | None = None
    #: 手绘矩形：页面重排/换源后坐标可能失效，`shape_sha` 用来提示复核
    shape_sha: str | None = None

    @property
    def is_text(self) -> bool:
        """文本类区域才做文字染色；表格单元格按文字处理。

        `kind` 来源不统一：python-pptx 给 `TEXT_BOX (17)`，测试/旧数据可能是 `text`，
        所以统一大写后再判断，避免大小写差异把文字当成图片跳过染色。
        """
        prefix = _kind_prefix(self.kind).upper()
        return prefix in ("", "TEXT", "TEXT_BOX", "PLACEHOLDER", "CELL") or prefix.startswith("TEXT")


@dataclass(frozen=True)
class HighlightStep:
    """一段画面：在 [start_ms, end_ms) 内高亮 boxes 指定的区域。"""

    text: str
    start_ms: int
    end_ms: int
    boxes: list[HighlightBox] = field(default_factory=list)
    #: 该段绑定的元素 id（来自讲稿生成阶段），空表示走字面兜底
    targets: tuple[str, ...] = ()
    #: 框的来源：`target`/`text` 是正常命中，`guess`/`page` 是兜底（界面上要标出来）
    fallback: str = ""

    @property
    def duration_ms(self) -> int:
        return max(0, self.end_ms - self.start_ms)


@dataclass(frozen=True)
class ElementRef:
    """页面上一个可被讲稿引用、也可被高亮的元素。"""

    element_id: str
    kind: str
    text: str
    box: HighlightBox

    @property
    def area(self) -> int:
        return self.box.width * self.box.height


@dataclass(frozen=True)
class ScriptSegment:
    """讲稿的一段：文本 + 它讲到的页面元素 id（可为空）+ 这句不亮的区域。"""

    text: str
    targets: tuple[str, ...] = ()
    #: 句级微调：这句即使命中了也不亮的区域 id
    mute: tuple[str, ...] = ()


@dataclass(frozen=True)
class RegionRule:
    """一个人工配置的区域：id 指向 layout 元素，或 `rect:N` 指向手绘矩形。"""

    element_id: str
    mode: str
    color: str | None = None
    fill_alpha: int | None = None
    #: 手绘矩形相对整页的比例（x/y/w/h，0~1）；元素区域为空
    rect: tuple[float, float, float, float] | None = None
    #: 画框时的页图 sha256：页图变了说明坐标可能已失效
    shape_sha: str | None = None

    @property
    def is_manual(self) -> bool:
        return self.rect is not None


@dataclass(frozen=True)
class SentenceRule:
    """句级微调：这句讲哪些区域（整体替换自动绑定）、哪些区域这句不亮。"""

    text: str = ""
    targets: tuple[str, ...] = ()
    mute: tuple[str, ...] = ()


@dataclass(frozen=True)
class RegionConfig:
    """一页已校验过的区域配置；`rules` 的键是区域 id，`sentences` 的键是句文本去标点。"""

    rules: dict[str, RegionRule] = field(default_factory=dict)
    sentences: dict[str, SentenceRule] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not self.rules and not self.sentences


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


def _padded_box(left: int, top: int, width: int, height: int, kind: str = "TEXT_BOX") -> HighlightBox:
    """按形状尺寸比例外扩一点边距：大框到上限，小框按比例，避免把它撑变形。"""
    pad_x = min(PAD_X_EMU, max(0, width // 10))
    pad_y = min(PAD_Y_EMU, max(0, height // 10))
    return HighlightBox(
        left=max(0, left - pad_x),
        top=max(0, top - pad_y),
        width=width + pad_x * 2,
        height=height + pad_y * 2,
        kind=kind,
    )


def _kind_label(kind: str) -> str:
    """python-pptx 的 kind 形如 `TEXT_BOX (17)`，取前缀做中文标签。"""
    prefix = str(kind or "").split(" ", 1)[0].strip()
    return _KIND_LABELS.get(prefix, "元素")


def _kind_prefix(kind: str) -> str:
    return str(kind or "").split(" ", 1)[0].strip()


def _box_of(raw: dict[str, Any], kind: str | None = None) -> HighlightBox | None:
    try:
        left = int(raw.get("left") or 0)
        top = int(raw.get("top") or 0)
        width = int(raw.get("width") or 0)
        height = int(raw.get("height") or 0)
    except (TypeError, ValueError):
        return None
    if width <= 0 or height <= 0:
        return None
    return _padded_box(left, top, width, height, kind if kind is not None else str(raw.get("kind") or ""))


def iter_elements(layout: Any) -> list[ElementRef]:
    """枚举页面可高亮元素，id 由 layout 内序号确定性生成（旧数据同样适用）。

    - `s0`、`s1` …：顶层形状（文本框/图片/图表/组合/表格整表）
    - `s3.r2c1`：第 3 个形状里表格的第 2 行第 1 列单元格
    """
    refs: list[ElementRef] = []
    for index, shape in enumerate(iter_shapes(layout)):
        box = _box_of(shape)
        if box is None:
            continue
        shape_id = f"s{index}"
        refs.append(
            ElementRef(
                element_id=shape_id,
                kind=str(shape.get("kind") or ""),
                text=str(shape.get("text") or ""),
                box=box,
            )
        )
        cells = shape.get("cells")
        if not isinstance(cells, list):
            continue
        for cell in cells:
            if not isinstance(cell, dict):
                continue
            cell_box = _box_of(cell, "CELL")
            if cell_box is None:
                continue
            try:
                row = int(cell.get("row") or 0)
                col = int(cell.get("col") or 0)
            except (TypeError, ValueError):
                continue
            if row <= 0 or col <= 0:
                continue
            refs.append(
                ElementRef(
                    element_id=f"{shape_id}.r{row}c{col}",
                    kind="CELL",
                    text=str(cell.get("text") or ""),
                    box=cell_box,
                )
            )
    return refs


def element_index(layout: Any) -> dict[str, ElementRef]:
    """元素 id → 元素；讲稿绑定校验与出帧取坐标都走它。"""
    return {ref.element_id: ref for ref in iter_elements(layout)}


def element_catalog(layout: Any, max_items: int = ELEMENT_CATALOG_MAX) -> list[dict[str, str]]:
    """给讲稿 prompt 的元素清单：按面积倒序、限量、摘要截断。

    无文字的装饰形状不进清单（模型引用它也没意义），图片/表格/图表/组合除外。
    """
    candidates = [
        ref
        for ref in iter_elements(layout)
        if ref.text.strip() or _kind_prefix(ref.kind) in _VISUAL_KINDS or ref.kind == "CELL"
    ]
    candidates.sort(key=lambda ref: -ref.area)
    catalog: list[dict[str, str]] = []
    for ref in candidates[: max(0, max_items)]:
        text = re.sub(r"\s+", " ", ref.text).strip()
        if len(text) > ELEMENT_TEXT_CHARS:
            text = text[:ELEMENT_TEXT_CHARS] + "…"
        catalog.append(
            {
                "id": ref.element_id,
                "kind": _kind_label(ref.kind),
                "text": text or "（无文字）",
            }
        )
    return catalog


def kind_label(kind: str) -> str:
    """元素类型的中文标签（区域清单给前端展示用）。"""
    return _kind_label(kind)


def _sentence_key(text: str) -> str:
    """句级规则的键：去掉空白与标点，手改讲稿时只改标点也能对上。"""
    return re.sub(r"[\s\W_]+", "", normalize_text(text))


def _normalize_color(value: Any) -> str | None:
    """只接受 #RRGGBB（允许省略 #），其余返回 None 交给调用方丢弃。"""
    text = str(value or "").strip()
    if not text:
        return None
    if not text.startswith("#"):
        text = f"#{text}"
    return text.upper() if _HEX_COLOR_RE.match(text) else None


def _clamp_alpha(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return max(0, min(255, int(value)))
    except (TypeError, ValueError):
        return None


def _normalize_rect(raw: Any) -> tuple[float, float, float, float] | None:
    """手绘矩形必须是整页内的合法比例框，越界一律丢弃（宁可不画也不能画出界）。"""
    if not isinstance(raw, dict):
        return None
    try:
        x, y, width, height = (float(str(raw.get(key))) for key in ("x", "y", "w", "h"))
    except (TypeError, ValueError):
        return None
    if not (0.0 <= x < 1.0 and 0.0 <= y < 1.0 and width > 0 and height > 0):
        return None
    if x + width > 1.0001 or y + height > 1.0001:
        return None
    return (round(x, 6), round(y, 6), round(min(width, 1.0), 6), round(min(height, 1.0), 6))


def _clean_ids(raw: Any, allowed: set[str] | None) -> tuple[str, ...]:
    if not isinstance(raw, (list, tuple)):
        return ()
    ids: list[str] = []
    for value in raw:
        candidate = str(value or "").strip()
        if not candidate or candidate in ids:
            continue
        if allowed is not None and candidate not in allowed:
            continue
        ids.append(candidate)
    return tuple(ids)


def parse_region_config(stored: Any, layout: Any = None) -> RegionConfig:
    """把落库的区域 JSON 校验成可用配置。

    - layout 有形状时，元素 id 必须能在 layout 里找到，找不到就丢（宁可不亮也不能亮错）；
    - layout 缺失（纯图片页还没解析出形状）时只做结构校验，不丢 id，避免人工配置被清空；
    - 非法颜色、越界透明度、出界矩形一律丢弃或夹紧，坏值不进渲染。
    """
    if not isinstance(stored, dict):
        return RegionConfig()
    known = set(element_index(layout)) if iter_shapes(layout) else None

    rules: dict[str, RegionRule] = {}
    raw_regions = stored.get("regions")
    if isinstance(raw_regions, list):
        for item in raw_regions:
            if len(rules) >= MAX_REGIONS:
                break
            if not isinstance(item, dict):
                continue
            element_id = str(item.get("id") or "").strip()
            mode = str(item.get("mode") or "").strip().lower()
            if not element_id or element_id in rules or mode not in REGION_MODES:
                continue
            rect = _normalize_rect(item.get("rect"))
            if known is not None and rect is None and element_id not in known:
                continue
            rules[element_id] = RegionRule(
                element_id=element_id,
                mode=mode,
                color=_normalize_color(item.get("color")),
                fill_alpha=_clamp_alpha(item.get("fill_alpha")),
                rect=rect,
                shape_sha=str(item.get("shape_sha") or "").strip() or None,
            )

    allowed = None if known is None else known | set(rules)
    sentences: dict[str, SentenceRule] = {}
    raw_sentences = stored.get("sentences")
    if isinstance(raw_sentences, list):
        for item in raw_sentences:
            if len(sentences) >= MAX_SENTENCE_RULES:
                break
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            key = _sentence_key(text)
            if not key or key in sentences:
                continue
            sentences[key] = SentenceRule(
                text=text,
                targets=_clean_ids(item.get("targets"), allowed),
                mute=_clean_ids(item.get("mute"), allowed),
            )
    return RegionConfig(rules=rules, sentences=sentences)


def dump_region_config(config: RegionConfig) -> dict[str, Any] | None:
    """校验后的配置写回落库结构；空配置落 None，保持「未配置」语义。"""
    if config.is_empty:
        return None
    regions: list[dict[str, Any]] = []
    for rule in config.rules.values():
        item: dict[str, Any] = {"id": rule.element_id, "mode": rule.mode}
        if rule.color:
            item["color"] = rule.color
        if rule.fill_alpha is not None:
            item["fill_alpha"] = rule.fill_alpha
        if rule.rect is not None:
            x, y, width, height = rule.rect
            item["rect"] = {"x": x, "y": y, "w": width, "h": height}
        if rule.shape_sha:
            item["shape_sha"] = rule.shape_sha
        regions.append(item)
    sentences = [
        {"text": rule.text, "targets": list(rule.targets), "mute": list(rule.mute)}
        for rule in config.sentences.values()
        if rule.text
    ]
    return {"regions": regions, "sentences": sentences}


def _manual_entries(config: RegionConfig, layout: Any) -> list[tuple[str, HighlightBox]]:
    """手绘矩形 → EMU 框；坐标按整页比例现算，页图/版式换了才需要复核。"""
    size = slide_size(layout)
    if size is None:
        return []
    page_width, page_height = size
    entries: list[tuple[str, HighlightBox]] = []
    for element_id, rule in config.rules.items():
        if rule.rect is None or rule.mode == REGION_MODE_OFF:
            continue
        x, y, width, height = rule.rect
        entries.append(
            (
                element_id,
                HighlightBox(
                    left=int(x * page_width),
                    top=int(y * page_height),
                    width=max(1, int(width * page_width)),
                    height=max(1, int(height * page_height)),
                    kind="RECT",
                    mode=rule.mode,
                    color=rule.color,
                    fill_alpha=rule.fill_alpha,
                    shape_sha=rule.shape_sha,
                ),
            )
        )
    return entries


def _with_rule(box: HighlightBox, rule: RegionRule | None) -> HighlightBox:
    if rule is None:
        return box
    return replace(box, mode=rule.mode, color=rule.color, fill_alpha=rule.fill_alpha)


def _always_on_manual(segment: ScriptSegment, config: RegionConfig | None, layout: Any) -> list[HighlightBox]:
    """手绘框默认整页常亮；只有该句的 mute 点了它的 id 才跳过。"""
    if config is None or not config.rules:
        return []
    muted = set(segment.mute)
    return [box for element_id, box in _manual_entries(config, layout) if element_id not in muted]


def _geometry_keys(layout: Any) -> dict[tuple[int, int, int, int], str]:
    """几何 → 元素 id：字面兜底命中时反查 id，才能套上区域配置。"""
    return {(ref.box.left, ref.box.top, ref.box.width, ref.box.height): ref.element_id for ref in iter_elements(layout)}


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


def match_shapes(sentence: str, layout: Any, coverage_threshold: float = SHAPE_HIT_COVERAGE) -> list[HighlightBox]:
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
        if coverage < coverage_threshold:
            continue
        box = _box_of(shape)
        if box is not None:
            boxes.append(box)
    return boxes


def _dedupe_boxes(boxes: Sequence[HighlightBox]) -> list[HighlightBox]:
    """去重并丢掉被别的框完全包住的框（表格整表 + 单元格同时命中时只留外层）。"""
    seen: list[HighlightBox] = []
    for box in sorted(boxes, key=lambda item: -(item.width * item.height)):
        if any(
            other.left <= box.left
            and other.top <= box.top
            and other.left + other.width >= box.left + box.width
            and other.top + other.height >= box.top + box.height
            for other in seen
        ):
            continue
        seen.append(box)
    return seen


def _page_box(layout: Any) -> HighlightBox | None:
    """整页框：页面里一个能用的元素都没有时的最后兜底，保证画面一定有变化。"""
    size = slide_size(layout)
    if size is None:
        return None
    width, height = size
    if width <= 0 or height <= 0:
        return None
    return HighlightBox(
        left=0,
        top=0,
        width=width,
        height=height,
        kind="PAGE",
        mode=REGION_MODE_AREA,
        fill_alpha=PAGE_FALLBACK_FILL_ALPHA,
    )


def _guess_box(
    segment: ScriptSegment,
    layout: Any,
    rules: dict[str, RegionRule],
    muted: set[str],
) -> HighlightBox | None:
    """兜底猜测：本页还没被关掉的元素里，与本句字面重合度最高的那一个。

    门槛比正常字面匹配（`SHAPE_HIT_COVERAGE`）低一档：正常匹配是「讲到了就亮」，
    这里是「一个都没命中时至少亮一个最像的」。允许亮错，但调用方会把来源标成
    `guess`，用户能在区域面板里复核并改回不亮。
    """
    sentence_grams = _bigrams(segment.text)
    if not sentence_grams:
        return None
    best: ElementRef | None = None
    best_score = 0.0
    for ref in iter_elements(layout):
        if ref.element_id in muted:
            continue
        rule = rules.get(ref.element_id)
        if rule is not None and rule.mode == REGION_MODE_OFF:
            continue
        text = normalize_text(ref.text or "")
        if len(text) < 2:
            continue
        grams = _bigrams(text)
        if not grams:
            continue
        score = len(grams & sentence_grams) / len(grams)
        if score < FALLBACK_GUESS_COVERAGE:
            continue
        # 同分时取面积大的：标题/正文块通常比角落的小标签更可能是当前讲的内容
        if score > best_score or (best is not None and score == best_score and ref.area > best.area):
            best, best_score = ref, score
    if best is None:
        return None
    return _with_rule(best.box, rules.get(best.element_id))


def boxes_for_segment_with_source(
    segment: ScriptSegment,
    layout: Any,
    coverage_threshold: float = SHAPE_HIT_COVERAGE,
    config: RegionConfig | None = None,
) -> tuple[list[HighlightBox], str]:
    """返回 (框, 来源)。来源用于面板标注「兜底」，不进视觉指纹。

    命中优先级：模型绑定元素 → 字面匹配 → 本页最像的元素（`guess`）→ 整页淡底（`page`）。
    用户显式 `off` / 句级 `mute` 优先级最高：任何兜底都不覆盖它，所以收紧过的页
    不会因为兜底又被点亮。
    """
    rules = config.rules if config is not None else {}
    muted = set(segment.mute)
    index = element_index(layout)
    manual = _always_on_manual(segment, config, layout)
    if MUTE_WHOLE_SENTENCE in muted:
        # 句级全静音：整句一个字都不亮（面板上复核兜底结果后最常见的操作）
        return manual, ""
    # 用户显式关掉的区域一旦命中过，就不再往下兜底：否则「改回不亮」会被兜底又点亮，
    # 或者照亮另一个他没提的元素，反而更错。
    suppressed = False
    boxes: list[HighlightBox] = []
    if segment.targets:
        for target in segment.targets:
            if target in muted:
                suppressed = True
                continue
            rule = rules.get(target)
            if rule is not None and rule.mode == REGION_MODE_OFF:
                suppressed = True
                continue
            ref = index.get(target)
            if ref is None:
                continue
            boxes.append(_with_rule(ref.box, rule))
        if boxes:
            # 显式配过效果的框（如表格单元格）不能被外层大框「包含」掉，单独保留并画在上层
            explicit = [box for box in boxes if box.mode]
            auto = [box for box in boxes if not box.mode]
            return _dedupe_boxes(auto) + explicit + manual, "target"

    geometry = _geometry_keys(layout)
    matched: list[HighlightBox] = []
    for box in _dedupe_boxes(match_shapes(segment.text, layout, coverage_threshold)):
        element_id = geometry.get((box.left, box.top, box.width, box.height))
        if element_id and element_id in muted:
            suppressed = True
            continue
        rule = rules.get(element_id) if element_id else None
        if rule is not None and rule.mode == REGION_MODE_OFF:
            suppressed = True
            continue
        matched.append(_with_rule(box, rule))
    if matched:
        return matched + manual, "text"

    if muted:
        # 句级微调（把这句的某个元素或整句关掉）是用户对这句的显式决定：不再兜底。
        # 注意不能用「本页有任何 off 规则」来判断——那会让页内其它句子全部失去高亮，
        # 与「每句必有高亮」冲突；页级 off 的元素已由 `_guess_box` 排除，不会猜中。
        suppressed = True
    if suppressed:
        return manual, ""

    guess = _guess_box(segment, layout, rules, muted)
    if guess is not None:
        return [guess] + manual, "guess"
    if manual:
        # 手绘框本来就常亮，画面已经有变化，不必再整页铺底
        return manual, ""
    page = _page_box(layout)
    if page is not None:
        return [page], "page"
    return [], ""


def boxes_for_segment(
    segment: ScriptSegment,
    layout: Any,
    coverage_threshold: float = SHAPE_HIT_COVERAGE,
    config: RegionConfig | None = None,
) -> list[HighlightBox]:
    """先按元素 id 直取坐标，再用区域配置过滤/改写效果，最后补上整页常亮的手绘框。

    `off` 的区域一律不亮；`text`/`area` 把效果写进框本身，
    出帧时逐框取画法，不再由「是不是文本」硬判定。
    """
    boxes, _source = boxes_for_segment_with_source(segment, layout, coverage_threshold, config)
    return boxes


def build_plan(
    script_text: str,
    layout: Any,
    duration_ms: int,
    max_steps: int = 6,
    config: RegionConfig | None = None,
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
        sentence_boxes, fallback = boxes_for_segment_with_source(
            ScriptSegment(text=sentence), layout, SHAPE_HIT_COVERAGE, config
        )
        steps.append(
            HighlightStep(
                text=sentence,
                start_ms=cursor,
                end_ms=max(cursor, end),
                boxes=sentence_boxes,
                fallback=fallback,
            )
        )
        cursor = end

    return HighlightPlan(steps=steps, total_ms=duration_ms)


def _join_text(left: str, right: str) -> str:
    """拼接相邻段：中英混排时该有空格的地方补一个。"""
    if not left:
        return right
    if not right:
        return left
    if left[-1].isascii() and left[-1].isalnum() and right[0].isascii() and right[0].isalnum():
        return f"{left} {right}"
    return left + right


def _cap_segments(segments: list[ScriptSegment], max_steps: int) -> list[ScriptSegment]:
    """段数超上限时，反复合并最短的相邻两段（保留顺序与 targets/mute 并集）。"""
    capped = [segment for segment in segments if segment.text.strip()]
    limit = max(1, max_steps)
    while len(capped) > limit:
        index = min(range(len(capped) - 1), key=lambda i: len(capped[i].text) + len(capped[i + 1].text))
        merged = ScriptSegment(
            text=_join_text(capped[index].text, capped[index + 1].text),
            targets=tuple(dict.fromkeys(capped[index].targets + capped[index + 1].targets)),
            mute=tuple(dict.fromkeys(capped[index].mute + capped[index + 1].mute)),
        )
        capped[index : index + 2] = [merged]
    return capped


def _flatten(text: str) -> str:
    return re.sub(r"\s+", "", normalize_text(text))


def _stored_segments(stored: Any, known_ids: set[str]) -> list[ScriptSegment]:
    """校验落库段结构：文本必须非空，targets 只保留页面真实存在的元素 id。"""
    if not isinstance(stored, list):
        return []
    segments: list[ScriptSegment] = []
    for item in stored:
        text: str
        raw_targets: Any
        if isinstance(item, str):
            text, raw_targets = item, []
        elif isinstance(item, dict):
            text = str(item.get("text") or "")
            raw_targets = item.get("targets") or []
        else:
            continue
        text = text.strip()
        if not text:
            continue
        targets: list[str] = []
        if isinstance(raw_targets, (list, tuple)):
            for target in raw_targets:
                candidate = str(target or "").strip()
                if candidate and candidate in known_ids and candidate not in targets:
                    targets.append(candidate)
        segments.append(ScriptSegment(text=text, targets=tuple(targets)))
    return segments


def stored_segments_hit(stored: Any, script_text: str, layout: Any) -> bool:
    """落库段是否仍然与当前讲稿一致（用户手改讲稿后必须失效）。"""
    known = set(element_index(layout))
    segments = _stored_segments(stored, known)
    if not segments:
        return False
    joined = "".join(segment.text for segment in segments)
    return _flatten(joined) == _flatten(script_text or "")


def apply_sentence_rules(
    segments: Sequence[ScriptSegment],
    config: RegionConfig | None,
) -> list[ScriptSegment]:
    """把句级微调并进段序列：targets 整体替换自动绑定，mute 叠加。

    句级规则按「去空白去标点」的文本匹配，所以手改别的句子不会把整页规则冲掉；
    某句被改得完全对不上时该条规则自然失效（宁可回到自动，也不能按旧 text 亮错）。
    """
    if config is None or not config.sentences:
        return list(segments)
    merged: list[ScriptSegment] = []
    for segment in segments:
        rule = config.sentences.get(_sentence_key(segment.text))
        if rule is None:
            merged.append(segment)
            continue
        merged.append(
            ScriptSegment(
                text=segment.text,
                targets=rule.targets or segment.targets,
                mute=tuple(dict.fromkeys(segment.mute + rule.mute)),
            )
        )
    return merged


def resolve_segments(
    script_text: str,
    layout: Any,
    stored: Any = None,
    max_steps: int = 6,
    config: RegionConfig | None = None,
) -> list[ScriptSegment]:
    """讲稿 → 段序列。

    落库段与当前讲稿一致时直接采用（带上元素绑定）；否则按标点重新切句，
    重新切出的段没有绑定，出帧时会退回字面匹配 —— 手改讲稿后不会亮错。
    传了区域配置就把句级微调叠上去（音频分段不受影响，只有画面变化）。
    """
    if not (script_text or "").strip():
        return []
    known = set(element_index(layout))
    segments = _stored_segments(stored, known)
    if segments and _flatten("".join(segment.text for segment in segments)) == _flatten(script_text):
        return _cap_segments(apply_sentence_rules(segments, config), max_steps)
    sentences = split_sentences(script_text, max_steps)
    return _cap_segments(apply_sentence_rules([ScriptSegment(text=s) for s in sentences], config), max_steps)


def merge_short_steps(steps: list[HighlightStep], min_dwell_ms: int) -> list[HighlightStep]:
    """停留过短的段并入相邻段（合并时长与高亮框），避免画面高频闪烁。

    合并只改时间轴与框，不重新合成音频，所以总时长恒定。
    """
    if min_dwell_ms <= 0 or len(steps) < 2:
        return steps
    merged: list[HighlightStep] = []
    for step in steps:
        if merged and (step.duration_ms < min_dwell_ms or merged[-1].duration_ms < min_dwell_ms):
            previous = merged[-1]
            merged[-1] = HighlightStep(
                text=_join_text(previous.text, step.text),
                start_ms=previous.start_ms,
                end_ms=step.end_ms,
                boxes=_dedupe_boxes(list(previous.boxes) + list(step.boxes)),
                targets=tuple(dict.fromkeys(previous.targets + step.targets)),
                # 任一段是兜底就保留标记：合并后画面里仍然有猜出来的框
                fallback=previous.fallback or step.fallback,
            )
        else:
            merged.append(step)
    return merged


def build_plan_for_segments(
    segments: Sequence[ScriptSegment],
    layout: Any,
    segment_durations_ms: Sequence[int],
    total_ms: int,
    *,
    min_dwell_ms: int = 0,
    coverage_threshold: float = SHAPE_HIT_COVERAGE,
    config: RegionConfig | None = None,
) -> HighlightPlan:
    """按各段真实音频时长生成时间轴（末段吃掉取整余数，保证音画总长闭合）。"""
    total_ms = max(0, total_ms)
    if not segments or total_ms <= 0:
        return HighlightPlan(steps=[], total_ms=total_ms)

    steps: list[HighlightStep] = []
    cursor = 0
    for index, segment in enumerate(segments):
        if index == len(segments) - 1:
            end = total_ms
        else:
            duration = max(0, int(segment_durations_ms[index]) if index < len(segment_durations_ms) else 0)
            end = min(total_ms, cursor + duration)
        segment_boxes, fallback = boxes_for_segment_with_source(segment, layout, coverage_threshold, config)
        steps.append(
            HighlightStep(
                text=segment.text,
                start_ms=cursor,
                end_ms=max(cursor, end),
                boxes=segment_boxes,
                targets=segment.targets,
                fallback=fallback,
            )
        )
        cursor = end

    return HighlightPlan(steps=merge_short_steps(steps, min_dwell_ms), total_ms=total_ms)


def _box_signature(box: HighlightBox) -> str:
    """单个框的签名：几何 + 类型 + 区域效果（三态/颜色/底色透明度）。"""
    return f"{box.left},{box.top},{box.width},{box.height},{box.kind},{box.mode},{box.color},{box.fill_alpha}"


def plan_signature(plan: HighlightPlan) -> str:
    """视觉指纹：分段、时间轴、目标元素、区域效果与高亮框任何变化都要让缓存失效。

    区域三态/颜色/底色透明度都写进签名：只改「这块铺底色」而不动讲稿时，
    句子时间轴没变，漏了这几项旧片段就会被复用、改了配置看着像没生效。
    """
    raw = "|".join(
        f"{step.start_ms}-{step.end_ms}:{','.join(step.targets)}:{','.join(_box_signature(box) for box in step.boxes)}"
        for step in plan.steps
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def visual_fingerprint(plan: HighlightPlan, layout: Any, style: str) -> str:
    """片段缓存用的视觉指纹 = 分段映射 + 页面布局 + 高亮样式。

    只算 `plan_signature` 不够：同一句话换个样式（压暗/描边）或页面布局挪了位置，
    画面其实变了但句子时间轴没变，旧片段会被原样复用、高亮静默失效。
    表格行高变了同理，所以单元格几何也要进指纹。
    """
    layout_parts: list[str] = []
    for shape in iter_shapes(layout):
        layout_parts.append(
            f"{shape.get('kind')},{shape.get('left')},{shape.get('top')},{shape.get('width')},{shape.get('height')}"
        )
        cells = shape.get("cells")
        if not isinstance(cells, list):
            continue
        for cell in cells:
            if isinstance(cell, dict):
                layout_parts.append(f"c{cell.get('left')},{cell.get('top')},{cell.get('width')},{cell.get('height')}")
    raw = f"visual\n{plan_signature(plan)}\n{style}\n{'|'.join(layout_parts)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
