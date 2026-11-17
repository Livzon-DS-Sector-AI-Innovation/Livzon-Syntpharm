"""母本解析：把 Word 母本展开成「可写位置 + 章节树」。

设计要点：

- 本模块是**可写判定唯一真源**：工具层（写入前校验）与渲染层（回放前定位）共用同一份
  ``TemplateOutline``，不允许两处各判一套，否则「工具说能写、渲染时却拒绝」这类矛盾
  只能靠日志猜。
- 纯函数：只读 docx 对象，不碰数据库、不调模型。母本 97 段 + 12 表量级在毫秒级，
  所以工具运行时与每次出稿都重建一次，不需要缓存，也不存在缓存过期问题。
- 判定目标是「不破坏母本」：空段、带 ``____``/``XXX`` 占位的段落、以及
  「标签：」这种只差一个值的段落可写；标题、目录、已有完整文字、签字审批区一律拒绝，
  并给出可读原因回给模型——模型看得到原因才能换位，看不到原因只会原样重试，白烧轮次。
- 「标签：」段用 ``append=True`` 标出来：模型只给值，渲染时接在冒号后，标签本身不动。
- 页眉页脚天然不在 ``document.paragraphs`` 里，不需要额外排除；这里只用文档正文。
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from docx.oxml.ns import qn

from app.modules.research.report_gen.cell_semantics import expect_of
from app.modules.research.report_gen.structure import fingerprint

logger = logging.getLogger(__name__)

# 正文里的填空占位：连续下划线（半角/全角）或模板里常见的 XXX/XXXX。
# 命中时不整段覆盖，只替换占位部分，保住「品种名称：」「表2 XXX主要物料供应信息」
# 这类标签、题注与首尾格式。要求至少 3 个 X，避免把普通缩写 XX 当成占位。
BLANK_RE = re.compile(r"[_＿]{2,}|[XxＸｘ]{3,}")
# 标题类样式：Heading 1/标题 1/Title/TOC/目录。
_HEADING_STYLE_RE = re.compile(r"^(heading|标题|title|subtitle)\s*(\d+)?$", re.IGNORECASE)
_TOC_STYLE_RE = re.compile(r"^(toc|目录)", re.IGNORECASE)
# 固定章节白名单：整章禁写只认这些标题（归一化后精确匹配），不做关键词子串匹配。
# 子串匹配会把「产品目录」「数据审核」「工艺编制说明」这类正文整章锁死，
# 误伤面远大于收益（用户反馈的实际问题）。
_FIXED_TITLES = frozenset(
    {
        "目录",
        "附件",
        "附件清单",
        "附表",
        "附录",
        "修订记录",
        "修改记录",
        "变更历史",
        "版本历史",
        "签字页",
        "签署页",
        "审批页",
        "审批记录",
        "签字审批",
        "编制审核批准",
        "编制审核校对",
        "会签页",
        "签字栏",
        "审批栏",
    }
)
# 附件/附表/附录带编号（附件1、附表二、附录A）也算固定章节
_FIXED_NUMBERED_RE = re.compile(r"^(附件|附表|附录)[0-9A-Za-z一二三四五六七八九十百]{1,3}$")
# 签字审批类短标题由这些词用分隔符组合而成（编制/审核/批准、签字：会签）
_SIGNATURE_WORDS = frozenset(
    {"编制", "审核", "审批", "批准", "校对", "签字", "签署", "签名", "会签", "日期", "及", "和", "与"}
)
# 组合判定允许的填充词：让「目录（自动生成）」这类带说明的标题也能命中
_FIXED_FILLER_WORDS = frozenset({"清单", "表", "页", "记录", "栏", "自动生成"})
_TITLE_SPLIT_RE = re.compile(r"[：:、/｜|（）()【】\[\]·—\-\s]+")
_NUMBER_PREFIX_RE = re.compile(
    r"^(?:第[一二三四五六七八九十百千]+[章节部分篇]"
    r"|[（(][一二三四五六七八九十0-9]+[）)]"
    r"|[0-9]+(?:\.[0-9]+)*[、.．]?"
    r"|[一二三四五六七八九十]+[、.．])\s*"
)
# 交给模型看的原文截断：只要够判断「这是什么位置」，不把整篇母本塞进 context。
MAX_OUTLINE_TEXT = 80
MAX_CONTEXT_TEXT = 40
# 表头回溯：最多往上三层（多级表头够用），超过 16 字或带句末标点的当正文，不当表头。
MAX_HEADER_DEPTH = 3
MAX_HEADER_TEXT = 16
# 封面/标题页：整区不写正文。判定靠结构信号，不靠文字猜测——
# 线上曾把封面 p0~p9（十连空段）当正文空位，AI 直接在首页写了四段概述。
COVER_REASON = "这是封面/标题页的版式内容，不写正文；正文请写到章节标题下的可写位置"
# 封面上常见的字段名：出现即认为前置区是封面（不是正文）
_COVER_WORD_RE = re.compile(
    r"文件名称|文件编号|报告编号|编\s*号|版\s*本|版\s*次|密\s*级|编制|审核|批准|生效日期|日\s*期"
)
# 前置区出现这么多字的段落就按正文看，不判封面（避免把「正文从第一段开始」的模板锁死）
_COVER_MAX_PROSE_CHARS = 40
_COVER_MAX_PROSE_COUNT = 2
# 封面字段名只认短标签：整句正文里出现「日期」不算封面
_COVER_MAX_LABEL_CHARS = 20
_HEADER_SENTENCE_RE = re.compile(r"[。！？；]|[,，;]\s")
# 「商品名：制剂」「规格：片剂」这类「标签：值」是数据格，不是表头
_HEADER_LABEL_VALUE_RE = re.compile(r"[：:]")
_HEADER_CHAR_RE = re.compile(r"[0-9A-Za-z\u4e00-\u9fa5]")


@dataclass(slots=True)
class TemplateSection:
    """母本里的一个标题章节（按标题段落切分）。"""

    level: int
    title: str
    start: int
    end: int

    @property
    def label(self) -> str:
        if not self.title:
            return "（正文开头）"
        return self.title


@dataclass(slots=True)
class WritablePosition:
    """一个可写位置：正文段落或表格单元格。"""

    key: str
    kind: str  # paragraph / table_cell
    label: str
    style: str
    text: str
    index: int  # 段落下标；表格位置为 table_index
    row: int | None
    col: int | None
    para_index: int
    writable: bool
    reason: str | None
    context: str
    section: str
    fingerprint: str
    append: bool = False  # True=「标签：」段，写入时只接冒号后的值
    numbered: bool = False  # 标题段是否带 Word 自动编号（numPr）：增补子标题时用来去掉重复编号
    heading: int = 0  # 标题级别（1-9）；0=正文。样式名与大纲级别（w:outlineLvl）都算
    # 表格位置的语义（段落位置留空）：行标题、「A › B」多级列路径、合并跨度、期望内容类型。
    # 模型据此判断「这一格是什么」，写入校验据此判断「值能不能写」。
    row_hint: str = ""
    column_hint: str = ""
    row_span: int = 1
    col_span: int = 1
    expect: str = ""

    def brief(self) -> dict[str, Any]:
        item: dict[str, Any] = {
            "key": self.key,
            "where": self.label,
            "section": self.section or "（正文开头）",
            "style": self.style or "-",
            "text": _cut(self.text, MAX_OUTLINE_TEXT) or "（空）",
            "context": _cut(self.context, MAX_CONTEXT_TEXT) or "-",
            "writable": self.writable,
        }
        if self.append:
            item["append"] = True
        if self.heading:
            item["heading"] = self.heading
        if self.column_hint:
            item["column_hint"] = _cut(self.column_hint, MAX_CONTEXT_TEXT)
        if self.expect and self.expect != "text":
            item["expect"] = self.expect
        if self.row_span > 1 or self.col_span > 1:
            item["merged"] = f"{self.row_span}行×{self.col_span}列"
        if not self.writable and self.reason:
            item["reason"] = self.reason
        return item

    def anchor(self) -> dict[str, Any]:
        """落库锚点：渲染期据此定位；指纹用于母本换版后兜底。"""
        anchor: dict[str, Any] = {
            "kind": self.kind,
            "location": self.label,
            "text": self.text,
            "fingerprint": self.fingerprint,
        }
        if self.append:
            anchor["append"] = True
        if self.kind == "paragraph":
            anchor["index"] = self.index
        else:
            anchor["table_index"] = self.index
            anchor["row"] = self.row
            anchor["col"] = self.col
            anchor["para_index"] = self.para_index
        return anchor


@dataclass(slots=True)
class TemplateOutline:
    """母本全貌：位置清单与章节树。"""

    positions: list[WritablePosition] = field(default_factory=list)
    sections: list[TemplateSection] = field(default_factory=list)
    paragraph_count: int = 0
    table_count: int = 0

    @property
    def writable(self) -> list[WritablePosition]:
        return [item for item in self.positions if item.writable]

    @property
    def writable_total(self) -> int:
        return sum(1 for item in self.positions if item.writable)

    def by_key(self) -> dict[str, WritablePosition]:
        return {item.key: item for item in self.positions}

    def is_fixed_section(self, section: str | None) -> bool:
        """该章节是否属于目录/附件/变更历史/签字审批这类整章禁写区域。"""
        return is_fixed_title(section)

    def section_brief(self, limit: int = 40) -> list[dict[str, Any]]:
        """章节树摘要：每个章节多少可写位置，供模型一次看清该从哪入手。"""
        counts: dict[str, int] = {}
        tables: dict[str, int] = {}
        for position in self.positions:
            if not position.writable:
                continue
            counts[position.section] = counts.get(position.section, 0) + 1
            if position.kind == "table_cell":
                tables[position.section] = tables.get(position.section, 0) + 1
        brief: list[dict[str, Any]] = []
        for section in self.sections[:limit]:
            key = section.title
            if not counts.get(key):
                continue
            item: dict[str, Any] = {
                "section": section.label,
                "from_paragraph": section.start + 1,
                "writable": counts.get(key, 0),
            }
            if tables.get(key):
                item["of_which_cells"] = tables[key]
            brief.append(item)
        return brief


def _cut(text: str | None, limit: int) -> str:
    value = " ".join((text or "").split())
    return value if len(value) <= limit else value[:limit] + "…"


def _style_name(paragraph: Any) -> str:
    try:
        return paragraph.style.name or ""
    except AttributeError:  # 样式表缺失的极端文档
        return ""


def _numbered(paragraph: Any) -> bool:
    """标题段是否带自动编号：增补子标题时据此决定要不要剥掉模型自带的「4.5」。

    编号可能直接写在段落上，也可能来自样式（自定义标题样式常见），两处都要看。
    """
    try:
        p_pr = paragraph._p.pPr  # noqa: SLF001 - 自动编号属性只在底层元素上
    except AttributeError:
        p_pr = None
    if p_pr is not None and p_pr.numPr is not None:
        return True
    try:
        style_element = paragraph.style.element
    except (AttributeError, KeyError):
        return False
    style_p_pr = style_element.find(qn("w:pPr"))
    return style_p_pr is not None and style_p_pr.find(qn("w:numPr")) is not None


def heading_level(style: str | None) -> int | None:
    """标题级别：Heading 2 / 标题 2 → 2，Title → 1；普通样式返回 None。"""
    name = (style or "").strip()
    if not name:
        return None
    match = _HEADING_STYLE_RE.match(name)
    if match is None:
        return None
    digits = match.group(2)
    if digits:
        try:
            return max(1, int(digits))
        except ValueError:
            return 1
    return 1


def _outline_level_of(p_pr: Any) -> int | None:
    """``w:outlineLvl`` → 1-9；0 是正文级别、9 是 body text，均按无级别处理。"""
    if p_pr is None:
        return None
    node = p_pr.find(qn("w:outlineLvl"))
    if node is None:
        return None
    try:
        value = int(node.get(qn("w:val")) or "")
    except (TypeError, ValueError):
        return None
    return value + 1 if 0 <= value <= 8 else None


def paragraph_heading_level(paragraph: Any) -> int | None:
    """段落标题级别：先认样式名，再认段落/样式上的大纲级别。

    模板不一定用 ``Heading 2`` 这种样式名，中文模板常见「二级标题」「章节标题」这类
    自定义样式；只要它设了大纲级别，Word 的 TOC 域（``\\o``/``\\u``）就会收录，
    这里也必须按标题处理，否则新增子标题会找不到克隆源、目录也认不出新标题。
    """
    level = heading_level(_style_name(paragraph))
    if level is not None:
        return level
    try:
        level = _outline_level_of(paragraph._p.pPr)  # noqa: SLF001
    except AttributeError:
        level = None
    if level is not None:
        return level
    try:
        style_element = paragraph.style.element
    except (AttributeError, KeyError):
        return None
    return _outline_level_of(style_element.find(qn("w:pPr")))


def is_toc_style(style: str | None) -> bool:
    return bool(_TOC_STYLE_RE.match((style or "").strip()))


def _normalize_title(title: str | None) -> str:
    """标题归一化：去空白、去编号前缀与首尾标点，``6.1 目 录：`` → ``目录``。"""
    text = "".join((title or "").split())
    text = _NUMBER_PREFIX_RE.sub("", text)
    return text.strip(":：.。、,，;；-—_")


def is_fixed_title(title: str | None) -> bool:
    """章节标题是否属于整章禁写的固定章节（目录/附件/修订历史/签字审批）。

    只做归一化后的精确匹配（含「附件1」「目录（自动生成）」这类编号/说明形式），
    不做关键词子串匹配：后者会把「产品目录」「数据审核」「工艺编制说明」这类正文
    整章锁死。「附件1 稳定性试验方案」这种带正文标题的附件章不锁，交给逐段判定。
    """
    normalized = _normalize_title(title)
    if not normalized:
        return False
    if normalized in _FIXED_TITLES or _FIXED_NUMBERED_RE.match(normalized):
        return True
    segments = [item for item in _TITLE_SPLIT_RE.split(normalized) if item]
    if not segments:
        return False
    known = _FIXED_TITLES | _SIGNATURE_WORDS | _FIXED_FILLER_WORDS
    has_signal = any(item in _FIXED_TITLES or item in _SIGNATURE_WORDS for item in segments)
    return has_signal and all(item in known for item in segments)


def has_blank(text: str | None) -> bool:
    return bool(BLANK_RE.search(text or ""))


def is_toc_title(title: str | None) -> bool:
    """标题是不是「目录」本身：目录只锁条目，不能把后面的正文一起锁掉。"""
    return _normalize_title(title) == "目录"


def is_label_text(text: str | None) -> bool:
    """「标签：」段：只有标签、值还没填，模型给值即可，标签保持原样。"""
    raw = (text or "").strip()
    return bool(raw) and len(raw) <= 40 and raw.endswith(("：", ":"))


def judge_text(
    text: str | None,
    *,
    style: str,
    fixed_section: str | None,
    appendable: bool = True,
    heading: int | None = None,
) -> tuple[bool, str | None, bool]:
    """可写判定：返回 (是否可写, 拒绝原因, 是否标签追加)。

    工具与渲染共用这一份。``fixed_section`` 非空表示这段落在「固定章节」
    （附件/变更历史/签字审批区），直接拒绝。``appendable`` 只对正文段落开：
    表格单元格的「标签：」仍按固定文字处理，避免单元格里再拼一段。
    ``heading`` 是外部已算好的标题级别（样式名或大纲级别）；不传则只按样式名判断。
    """
    if fixed_section:
        return False, f"这属于「{fixed_section}」章节的版面或流程内容，不需要填写业务内容", False
    level = heading_level(style) if heading is None else heading
    if level is not None:
        return False, "这是标题，不能改写", False
    if is_toc_style(style):
        return False, "这是目录内容，不能改写", False
    raw = (text or "").strip()
    if not raw:
        return True, None, False
    if has_blank(raw):
        return True, None, False
    if appendable and is_label_text(raw):
        return True, None, True
    return False, "这里已经有完整内容，不需要 AI 填写；需要时可以直接编辑补写", False


def _context_before(texts: list[str], index: int) -> str:
    """取当前位置之前最近的非空文本：帮模型判断「这段该写什么」。"""
    for offset in range(index - 1, max(index - 6, -1), -1):
        candidate = texts[offset]
        if candidate:
            return candidate
    return ""


def body_table_starts(document: Any) -> list[int]:
    """表格在正文中的位置：返回每张表前面有多少个正文段落。

    ``document.paragraphs`` 不含表格内段落，因此按 body 子节点顺序数 ``w:p``
    得到的就是段落下标；表格的「上文位置」用它前面有多少段表示。

    详情页给逐处清单排序时也用这份顺序：只靠 ``outline.positions``（先段落后表格）
    会把表格全排到文末，章节内看起来就错位了。
    """
    para_count = 0
    table_starts: list[int] = []
    for child in document.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            para_count += 1
        elif tag == "tbl":
            table_starts.append(para_count)
    return table_starts


def _section_timeline(paragraphs: list[Any]) -> tuple[list[str], list[str | None], list[int | None]]:
    """逐段的「所属章节标题 / 固定章节名 / 标题级别」。

    ``固定章节名`` 非空表示该段位于目录、附件、变更历史、签字审批这类整章禁写的区域。
    """
    styles = [_style_name(item) for item in paragraphs]
    levels = [paragraph_heading_level(item) for item in paragraphs]
    titles: list[str] = [""] * len(paragraphs)
    blocks: list[str | None] = [None] * len(paragraphs)
    title = ""
    block: str | None = None
    in_toc = False
    for index, level in enumerate(levels):
        if level is not None:
            title = (paragraphs[index].text or "").strip()
            in_toc = is_toc_title(title)
            # 目录只锁 toc 样式与标题本身；后面的「品种简介」等正文不能跟着被锁
            block = title if is_fixed_title(title) and not in_toc else None
        elif in_toc and not is_toc_style(styles[index]):
            # 目录条目结束，后面是没有标题的正文：章节归到「正文开头」，别继续算目录
            in_toc = False
            title = ""
            block = None
        titles[index] = title
        blocks[index] = block
    return titles, blocks, levels


def _cover_region(texts: list[str], levels: list[int | None]) -> tuple[set[int], int | None]:
    """识别封面/标题页：返回（封面段落下标集合, 首个标题下标）。

    封面不是靠文字猜的，而是一组结构信号：

    - 第一个章节标题之前存在连续 ≥3 个空段落（线上事故形态：p0~p9 十连空）；
    - 该区出现「文件名称/文件编号/版本/密级/编制/审核/批准/日期」这类封面字段名；
    - 首个标题是「目录 / 修订记录 / 变更历史」这类前置标题（以目录开头的文档，其前必是封面）。

    反例保护，避免把「正文从第一段就开始」的模板整段锁死：前置区已有 ≥2 段长正文时
    按正文看（不判封面）；封面字段名只认短标签（≤20 字），避免正文里出现「日期」这类词被误判。
    """
    first_heading = next((index for index, level in enumerate(levels) if level is not None), None)
    if first_heading is None or first_heading == 0:
        return set(), first_heading

    region = list(range(0, first_heading))
    prose = [texts[index] for index in region if len(texts[index]) > _COVER_MAX_PROSE_CHARS]
    if len(prose) >= _COVER_MAX_PROSE_COUNT:
        return set(), first_heading

    longest_empty = 0
    empty_run = 0
    for index in region:
        empty_run = empty_run + 1 if not texts[index] else 0
        longest_empty = max(longest_empty, empty_run)

    has_cover_words = any(
        len(texts[index]) <= _COVER_MAX_LABEL_CHARS and _COVER_WORD_RE.search(texts[index]) for index in region
    )
    first_is_front_matter = is_toc_title(texts[first_heading]) or is_fixed_title(texts[first_heading])
    if not (longest_empty >= 3 or has_cover_words or first_is_front_matter):
        return set(), first_heading
    return set(region), first_heading


def _table_section(table_start: int, titles: list[str]) -> str:
    if table_start <= 0 or not titles:
        return ""
    return titles[min(table_start - 1, len(titles) - 1)]


def _meaningful_header(text: str | None) -> str:
    """能不能当「表头文字」用。

    合并表头的实际内容经常是 ``XXXX（原料药）``、``____`` 这类占位，或者干脆是一整句话；
    把它们当列语义回给模型，比不给还糟（模型会照着「XXXX（原料药）」瞎填）。
    """
    value = " ".join((text or "").split())
    if not value or len(value) > MAX_HEADER_TEXT:
        return ""
    if BLANK_RE.search(value):
        return ""
    if _HEADER_SENTENCE_RE.search(value) or _HEADER_LABEL_VALUE_RE.search(value):
        return ""
    if not _HEADER_CHAR_RE.search(value):
        return ""
    return value


def _row_hint(rows: list[list[Any]], row: int, col: int) -> str:
    """行标题：该行左侧最近的短标签（「技术部意见」「原研企业」）。"""
    line = rows[row] if row < len(rows) else []
    for index in range(min(col, len(line)) - 1, -1, -1):
        text = _meaningful_header(line[index].text)
        if text:
            return text
    return ""


def _column_hint(rows: list[list[Any]], row: int, col: int) -> str:
    """列路径：向上逐行取同列（含覆盖该列的合并格）的表头文字，最多三层。

    最近的一层放最后，拼成「自主研发成本 › 研发投入」这种从上到下的路径；
    遇到句子或占位就停（再往上已经不是表头了）。
    """
    parts: list[str] = []
    for index in range(row - 1, max(row - 1 - MAX_HEADER_DEPTH, -1), -1):
        line = rows[index] if index < len(rows) else []
        text = _meaningful_header(line[col].text) if col < len(line) else ""
        if not text or (parts and parts[-1] == text):
            continue
        parts.append(text)
    return " › ".join(reversed(parts))


def _table_grid(table: Any) -> tuple[list[list[Any]], dict[str, tuple[int, int, int, int]]]:
    """展开表格网格，并统计每个底层 ``w:tc`` 的首个坐标与行列跨度。

    python-docx 的 ``row.cells`` 已按网格展开合并单元格（同一个 ``w:tc`` 会重复出现），
    所以这里只用一次扫描：出现位置的最小 (行,列) 就是锚点，出现过的不同行数/列数就是跨度。
    与渲染侧 ``table.rows[r].cells[c]`` 用的是同一套网格坐标，key 不需要变。
    """
    rows: list[list[Any]] = []
    markers: list[list[str]] = []
    for row in table.rows:
        cells = list(row.cells)
        rows.append(cells)
        markers.append([cell._tc.getroottree().getpath(cell._tc) for cell in cells])  # noqa: SLF001

    spans: dict[str, tuple[int, int, int, int]] = {}
    for row_index, line in enumerate(markers):
        for col_index, marker in enumerate(line):
            if marker not in spans:
                spans[marker] = (row_index, col_index, 1, 1)
    for marker, (row0, col0, _, _) in list(spans.items()):
        hit_rows = {index for index, line in enumerate(markers) if marker in line}
        hit_cols = {index for index, item in enumerate(markers[row0]) if item == marker}
        spans[marker] = (row0, col0, len(hit_rows), len(hit_cols))
    return rows, spans


def _cell_label(
    table_index: int,
    row: int,
    col: int,
    row_hint: str,
    column_hint: str,
    row_span: int,
    col_span: int,
) -> str:
    """可读位置名：有语义时用「表3 · 技术部意见 · 研发投入」，没有就退回行列号。"""
    parts = [f"表{table_index + 1}"]
    if row_hint:
        parts.append(row_hint)
    if column_hint:
        parts.append(column_hint)
    if len(parts) == 1:
        parts.append(f"第{row + 1}行第{col + 1}列")
    label = " · ".join(parts)
    if col_span > 1:
        label += f"（合并 {col_span} 列）"
    elif row_span > 1:
        label += f"（合并 {row_span} 行）"
    return label


def _is_label_column(rows: list[list[Any]], col: int) -> bool:
    """最左列是不是「行标题列」：该列非空的格全是短标签（技术部意见/原研企业这类）。

    行标题列里的空格是版面留白，不是要填的位置——让模型去写，它就会把值塞进标题栏。
    """
    texts: list[str] = []
    for line in rows:
        if col >= len(line):
            continue
        text = (line[col].text or "").strip()
        if text:
            texts.append(text)
    if len(texts) < 2:
        return False
    return all(bool(_meaningful_header(text)) for text in texts)


def _blank_cell_count(cells: list[Any], fixed_section: str | None) -> int:
    """该行有几个「空的、样式上允许写」的独立单元格（合并区只算一个）。

    用来识别「一排空格但看不出列含义」的数据行：合并区若按网格位置计数，
    一个跨 9 列的意见格会被数成 9 个空格，反而把它自己判成数据行。
    """
    count = 0
    seen: set[str] = set()
    for cell in cells:
        if (cell.text or "").strip():
            continue
        tc = cell._tc  # noqa: SLF001 - 按底层 w:tc 去重，避免合并区重复计数
        marker = tc.getroottree().getpath(tc)
        if marker in seen:
            continue
        seen.add(marker)
        paragraph = cell.paragraphs[0] if cell.paragraphs else None
        style = _style_name(paragraph) if paragraph is not None else ""
        writable, _, _ = judge_text("", style=style, fixed_section=fixed_section, appendable=False)
        if writable:
            count += 1
    return count


def _cell_positions(
    table: Any,
    table_index: int,
    section: str,
    fixed_section: str | None,
    *,
    cover: bool = False,
) -> list[WritablePosition]:
    """展开一张表的单元格：合并区域按底层 w:tc 去重，并带上行标题/列路径语义。"""
    items: list[WritablePosition] = []
    try:
        rows, spans = _table_grid(table)
    except (AttributeError, IndexError):  # 结构怪异的表不让整次生成挂掉，退化为不产出位置
        return items

    # 每行有多少个「空的、本可写」的格：用来识别「一排空格但看不出列含义」的数据行
    blank_per_row = [_blank_cell_count(line, fixed_section) for line in rows]
    label_column = _is_label_column(rows, 0)

    seen: set[str] = set()
    for row_index, cells in enumerate(rows):
        for col_index, cell in enumerate(cells):
            tc = cell._tc  # noqa: SLF001 - 合并单元格去重需要底层 w:tc 节点
            marker = tc.getroottree().getpath(tc)
            if marker in seen:
                continue
            seen.add(marker)
            _row0, _col0, row_span, col_span = spans.get(marker, (row_index, col_index, 1, 1))

            paragraph = cell.paragraphs[0] if cell.paragraphs else None
            style = _style_name(paragraph) if paragraph is not None else ""
            text = (cell.text or "").strip()
            writable, reason, _append = judge_text(text, style=style, fixed_section=fixed_section, appendable=False)

            row_hint = _row_hint(rows, row_index, col_index)
            # 键值行（左侧标签 + 右侧一个跨列的值格）的列语义来自标签本身：
            # 再往上找表头只会拿到上一块表的「药品名称」，反倒把意见栏指错方向。
            column_hint = "" if col_span > 1 and col_index > 0 else _column_hint(rows, row_index, col_index)

            # 行标题列里的空格是版面留白，不是要填的位置
            if cover:
                # 封面表也是版面（抬头、文件名称、签字栏）：整表禁写，原因与封面段落一致
                writable = False
                reason = COVER_REASON
            elif writable and not text and col_index == 0 and label_column:
                writable = False
                reason = "这一列是每行的标题栏，不需要填写内容"

            # 一排空格又没有任何列语义：宁可不可写，也不能让模型按顺序把值塞进去
            if writable and not text and not column_hint and blank_per_row[row_index] >= 3:
                writable = False
                reason = "这一行有多列空格，但看不出每列要填什么；先不要按顺序填，请确认列含义后再写，或留空由人工补"

            label = _cell_label(table_index, row_index, col_index, row_hint, column_hint, row_span, col_span)
            if cover:
                label = f"封面 · {label}"

            items.append(
                WritablePosition(
                    key=f"t{table_index}r{row_index}c{col_index}",
                    kind="table_cell",
                    label=label,
                    style=style,
                    text=text,
                    index=table_index,
                    row=row_index,
                    col=col_index,
                    para_index=0,
                    writable=writable,
                    reason=reason,
                    context=row_hint or column_hint,
                    section=section,
                    fingerprint=fingerprint(text),
                    row_hint=row_hint,
                    column_hint=column_hint,
                    row_span=row_span,
                    col_span=col_span,
                    expect=expect_of(row_hint, column_hint),
                )
            )
    return items


def build_outline(document: Any) -> TemplateOutline:
    """一次性构建母本全貌。"""
    paragraphs = list(document.paragraphs)
    titles, blocks, levels = _section_timeline(paragraphs)
    texts = [(item.text or "").strip() for item in paragraphs]

    outline = TemplateOutline(paragraph_count=len(paragraphs), table_count=len(document.tables))

    # 封面/标题页：整区不写正文（标签段除外），避免 AI 把概述写进首页留白
    cover, first_heading = _cover_region(texts, levels)
    if cover:
        logger.info(
            "cover region detected",
            extra={"cover_paragraphs": len(cover), "biz_module": "research"},
        )

    for index, paragraph in enumerate(paragraphs):
        style = _style_name(paragraph)
        text = texts[index]
        writable, reason, append = judge_text(text, style=style, fixed_section=blocks[index], heading=levels[index])
        in_cover = index in cover
        if in_cover and not append:
            # 封面只禁「写整段正文」：「文件编号：____」这类标签段仍要能补值
            writable = False
            reason = COVER_REASON
        outline.positions.append(
            WritablePosition(
                key=f"p{index}",
                kind="paragraph",
                label=f"封面第{index + 1}段" if in_cover else f"正文第{index + 1}段",
                style=style,
                text=text,
                index=index,
                row=None,
                col=None,
                para_index=0,
                writable=writable,
                reason=reason,
                context=_context_before(texts, index),
                section=titles[index],
                fingerprint=fingerprint(text),
                append=append,
                numbered=_numbered(paragraph),
                heading=levels[index] or 0,
            )
        )

    table_starts = body_table_starts(document)
    for table_index, table in enumerate(document.tables):
        start = table_starts[table_index] if table_index < len(table_starts) else 0
        section = _table_section(start, titles)
        fixed = section if section and is_fixed_title(section) else None
        # 表在第一个标题之前（start <= 首个标题下标）= 封面表
        table_in_cover = bool(cover) and first_heading is not None and start <= first_heading
        outline.positions.extend(_cell_positions(table, table_index, section, fixed, cover=table_in_cover))

    # 章节树：标题段落切分，end 取下一个标题前一段
    current: TemplateSection | None = None
    for index, level in enumerate(levels):
        if level is None:
            continue
        if current is not None:
            current.end = index - 1
        current = TemplateSection(level=level, title=texts[index], start=index, end=len(paragraphs) - 1)
        outline.sections.append(current)

    return outline


__all__ = [
    "BLANK_RE",
    "COVER_REASON",
    "MAX_OUTLINE_TEXT",
    "TemplateOutline",
    "TemplateSection",
    "WritablePosition",
    "body_table_starts",
    "build_outline",
    "has_blank",
    "heading_level",
    "is_fixed_title",
    "is_toc_style",
    "judge_text",
    "paragraph_heading_level",
]
