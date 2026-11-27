"""标准表 docx 解析。

样本结构：单表格、30 行 × 3 列（字段 | 类型/格式 | 说明）。
- 前 3 行是 品名 / 批号 / 生产日期，导入时跳过
- 其余行为检验项目，「说明」列用固定前缀写三层标准：
  `标准：xxx` / `企业内控：xxx` / `3σ标准：xxx`

**必须按底层 XML 取文本**：Word 的修订插入（w:ins）会把一段文字包起来，
常规的 run 遍历读不到（实测样本里「企业内控 ＜0.05EU/mg」的 `05` 就是这样丢的）。
这里遍历所有 w:t，w:ins 内计入、w:del / w:moveFrom 内排除。
"""

from __future__ import annotations

import io
import logging
import re
import zipfile
from dataclasses import dataclass, field

from lxml import etree  # type: ignore[import-untyped]

from app.modules.quality.qc_report.constants import STANDARD_TABLE_SKIP_FIELDS

logger = logging.getLogger(__name__)

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_DELETED_TAGS = (f"{_W}del", f"{_W}moveFrom")

# 三层标准的前缀。长前缀优先，避免「企业内控标准」被「标准」抢走
_LAYER_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("sigma", re.compile(r"(?:3\s*[σΣ]\s*标准|3\s*[σΣ])")),
    ("internal", re.compile(r"(?:企业内控标准|企业内控|内控标准|内控)")),
    ("legal", re.compile(r"(?:法定标准|标准)")),
)
_LAYER_SPLIT = re.compile(r"(?:3\s*[σΣ]\s*标准|3\s*[σΣ]|企业内控标准|企业内控|内控标准|内控|法定标准|标准)\s*[：:]")

# 项目名末尾括号里通常是单位
_TRAILING_PAREN = re.compile(r"（([^（）]*)[）)]\s*$|\(([^()]*)\)\s*$")

# 说明列里「结果应为：符合规定/不符合规定」是给检验员看的验收口径，
# 不属于标准值本身；留在文本里会让它与结果表的「应符合规定」被判成不一致。
_EXPECTED_NOTE = re.compile(r"[。；;，,]?\s*结果(?:应为|要求|判定)[：:].*$")


class DocxParseError(ValueError):
    """标准表结构不符合预期。"""


@dataclass
class ParsedStandardItem:
    """标准表里的一行检验项目。"""

    item_no: int
    item_name: str
    raw_type: str | None
    unit: str | None
    legal_text: str | None
    internal_text: str | None
    sigma_text: str | None
    raw_note: str | None = None
    extra: dict[str, str] = field(default_factory=dict)


@dataclass
class ParsedStandard:
    """标准表解析结果。"""

    items: list[ParsedStandardItem]
    columns: list[str]
    sheet_title: str | None = None


def _has_deleted_ancestor(node: etree._Element) -> bool:
    parent = node.getparent()
    while parent is not None:
        if parent.tag in _DELETED_TAGS:
            return True
        if parent.tag == f"{_W}tc":
            break
        parent = parent.getparent()
    return False


def _cell_text(tc: etree._Element) -> str:
    """取单元格全部可见文本（含修订插入，排除修订删除）。"""
    parts: list[str] = []
    for node in tc.iter(f"{_W}t"):
        if _has_deleted_ancestor(node):
            continue
        if node.text:
            parts.append(node.text)
    # 段内换行还原为空格，避免限值被拆断
    return re.sub(r"\s+", " ", "".join(parts)).strip()


def _iter_rows(tbl: etree._Element) -> list[list[str]]:
    rows: list[list[str]] = []
    for tr in tbl.findall(f"{_W}tr"):
        cells = [_cell_text(tc) for tc in tr.findall(f"{_W}tc")]
        if any(cells):
            rows.append(cells)
    return rows


def _pick_main_table(root: etree._Element) -> etree._Element | None:
    """取行数最多的表格，容忍文档里存在封面信息表。"""
    best: etree._Element | None = None
    best_rows = 0
    for tbl in root.iter(f"{_W}tbl"):
        row_count = len(tbl.findall(f"{_W}tr"))
        if row_count > best_rows:
            best, best_rows = tbl, row_count
    return best


def _strip_expected_note(text: str) -> str:
    """去掉「结果应为：符合规定/不符合规定」这类验收口径，只留标准值。"""
    if not text:
        return text
    return _EXPECTED_NOTE.sub("", text).strip()


def _split_layers(note: str) -> tuple[str | None, str | None, str | None]:
    """把说明列切成 法定 / 内控 / 3σ 三段原文。"""
    if not note:
        return None, None, None

    matches = list(_LAYER_SPLIT.finditer(note))
    if not matches:
        # 没有前缀：整段当作法定标准
        return note.strip() or None, None, None

    buckets: dict[str, str] = {}
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(note)
        segment = _strip_expected_note(note[start:end].strip().strip("，,；;、 ").strip())
        keyword = match.group(0)
        layer = "legal"
        for name, pattern in _LAYER_PATTERNS:
            if pattern.match(keyword):
                layer = name
                break
        if segment and layer not in buckets:
            buckets[layer] = segment

    return buckets.get("legal"), buckets.get("internal"), buckets.get("sigma")


def _extract_unit(item_name: str) -> str | None:
    """从项目名末尾括号取单位，如「水分（%）」→ %。"""
    match = _TRAILING_PAREN.search(item_name)
    if not match:
        return None
    unit = (match.group(1) or match.group(2) or "").strip()
    if not unit or len(unit) > 16:
        return None
    # 括号里是条件（如 ≥10µm）而不是单位时忽略
    if re.fullmatch(r"[≥≤<>＜＞=+\-]?\s*\d+(?:\.\d+)?\s*[a-zA-Zµμ]*", unit):
        return None
    return unit


def parse_standard_docx(content: bytes) -> ParsedStandard:
    """解析标准表 docx。解析不出表格时抛 DocxParseError（由 API 转成可读错误）。"""
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            xml = archive.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError) as exc:
        raise DocxParseError("文件不是有效的 Word 文档（docx）") from exc

    try:
        root = etree.fromstring(xml)
    except etree.XMLSyntaxError as exc:
        raise DocxParseError("Word 文档内容损坏，无法解析") from exc

    table = _pick_main_table(root)
    if table is None:
        raise DocxParseError("Word 文档里没有找到表格，标准表需要是表格形式")

    rows = _iter_rows(table)
    if len(rows) < 2:
        raise DocxParseError("标准表行数过少，至少需要一行表头 + 一行项目")

    header = rows[0]
    columns = [cell for cell in header if cell]
    name_idx, type_idx, note_idx = 0, 1, 2
    # 按表头文字定位列，找不到再退回固定位置
    for idx, cell in enumerate(header):
        if "字段" in cell or "项目" in cell:
            name_idx = idx
        elif "类型" in cell or "格式" in cell:
            type_idx = idx
        elif "说明" in cell or "标准" in cell:
            note_idx = idx

    items: list[ParsedStandardItem] = []
    for order, row in enumerate(rows[1:], start=1):
        name = (row[name_idx] if name_idx < len(row) else "").strip()
        if not name:
            continue
        # 跳过基础字段行（品名 / 批号 / 生产日期）
        if any(skip in name for skip in STANDARD_TABLE_SKIP_FIELDS) and len(name) <= 6:
            continue
        raw_type = (row[type_idx] if type_idx < len(row) else "").strip() or None
        note = (row[note_idx] if note_idx < len(row) else "").strip() or None
        legal, internal, sigma = _split_layers(note or "")
        items.append(
            ParsedStandardItem(
                item_no=len(items) + 1,
                item_name=name,
                raw_type=raw_type,
                unit=_extract_unit(name),
                legal_text=legal,
                internal_text=internal,
                sigma_text=sigma,
                raw_note=note,
            )
        )

    if not items:
        raise DocxParseError("标准表里没有解析到任何检验项目")

    logger.info(
        "qc_report standard docx parsed",
        extra={"item_count": len(items), "row_count": len(rows)},
    )
    return ParsedStandard(items=items, columns=columns)


__all__ = [
    "DocxParseError",
    "ParsedStandard",
    "ParsedStandardItem",
    "parse_standard_docx",
]
