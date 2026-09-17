"""docx 锚点定位与文本写入原语。

设计约束：定位失败必须显式抛 AnchorUnresolved，绝不允许退化成「让模型猜位置」——
填错格子比留空更难发现。写入一律保留原有 run 格式（字体/字号/样式不动），
这是「模板样式零改动」这条需求的实现基础。
"""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Literal

from docx.document import Document as DocxDocument
from docx.oxml import parse_xml
from docx.oxml.ns import qn
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from app.modules.research.doc_gen.grid import (
    cell_text,
    distinct_row_cells,
    normalize,
    row_grid_cells,
)
from app.modules.research.doc_gen.template_spec import Anchor, Slot, TableSpec

_BLANK_P = parse_xml('<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>')


class AnchorUnresolvedError(Exception):
    """锚点在母本中无法定位。"""

    def __init__(self, slot_key: str, reason: str) -> None:
        super().__init__(f"填充项 {slot_key} 未能在模板原件中定位：{reason}")
        self.slot_key = slot_key
        self.reason = reason


@dataclass(slots=True)
class CellTarget:
    """单个单元格（col 为网格列号，合并单元格按起始列计）。"""

    table: Table
    row: int
    col: int


@dataclass(slots=True)
class ParagraphTarget:
    """段落；mode 决定写入方式。"""

    paragraph: Paragraph
    mode: Literal["after_label", "replace", "append_after"]
    label: str = ""


@dataclass(slots=True)
class GlobalTarget:
    """全文占位关键词（如 XXXX）。"""

    paragraphs: list[Paragraph] = field(default_factory=list)
    keyword: str = ""


@dataclass(slots=True)
class RowsTarget:
    """表格数据区。"""

    table: Table
    header_rows: int
    template_row: int
    data_rows: list[int]
    columns: dict[str, int]
    total_row: int | None = None


Target = CellTarget | ParagraphTarget | GlobalTarget | RowsTarget


def body_paragraphs(doc: DocxDocument) -> list[Paragraph]:
    """正文段落（不含表格内段落）。"""
    return list(doc.paragraphs)


def iter_all_paragraphs(doc: DocxDocument) -> list[Paragraph]:
    """正文 + 所有表格单元格内的段落。"""
    paragraphs = list(doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in distinct_row_cells(row):
                paragraphs.extend(cell.paragraphs)
    return paragraphs


def table_header_text(table: Table, header_rows: int = 1) -> str:
    """表头区文本拼接，用于按表头识别表格。"""
    parts: list[str] = []
    for row in list(table.rows)[:header_rows]:
        for cell in distinct_row_cells(row):
            parts.append(cell_text(cell))
    return "|".join(parts)


def find_table(doc: DocxDocument, header_contains: list[str], table: TableSpec | None = None) -> Table:
    """按表头文本定位表格；多个命中时取第一个，无命中抛错。"""
    headers = [normalize(h) for h in header_contains if normalize(h)]
    if not headers:
        raise ValueError("find_table 需要至少一个表头关键词")
    rows = (table.header_rows if table is not None else 1) or 1
    for cand in doc.tables:
        head = normalize(table_header_text(cand, rows))
        if all(h in head for h in headers):
            return cand
    # 兜底：有些表头跨多行，扩大扫描范围再试一次
    for cand in doc.tables:
        head = normalize(table_header_text(cand, 3))
        if all(h in head for h in headers):
            return cand
    raise LookupError(f"未找到表头包含 {header_contains} 的表格")


def paragraph_label_matches(text: str, label: str, mode: str) -> bool:
    """段落标签匹配：exact 要求「标签：」整段仅此内容，避免「名称：」误命中「其他名称：」。"""
    text_n, label_n = normalize(text), normalize(label)
    if mode == "exact":
        return text_n in {label_n, f"{label_n}:", f"{label_n}："}
    if mode == "prefix":
        return text_n.startswith(label_n)
    return label_n in text_n


def find_paragraph_by_label(
    doc: DocxDocument, label: str, mode: str = "exact", skip_tables: bool = True
) -> Paragraph | None:
    """按标签定位正文段落。"""
    source: list[Paragraph] = list(doc.paragraphs) if skip_tables else iter_all_paragraphs(doc)
    for para in source:
        if paragraph_label_matches(para.text, label, mode):
            return para
    return None


def run_color(run: Run) -> str:
    """取 run 的字体颜色十六进制，无颜色时返回空串。"""
    rgb = run.font.color.rgb if run.font.color is not None else None
    return str(rgb) if rgb is not None else ""


def find_paragraphs_by_color(doc: DocxDocument, color: str) -> list[Paragraph]:
    """按字体颜色定位段落（母本用蓝色标记给人看的提示语）。"""
    hits: list[Paragraph] = []
    for para in doc.paragraphs:
        for run in para.runs:
            if run_color(run).upper() == color.upper():
                hits.append(para)
                break
    return hits


def find_heading(doc: DocxDocument, heading: str, level: int | None = None) -> Paragraph | None:
    """按标题文本定位（自动编号导致标题本身不含编号，因此用归一化包含匹配）。"""
    target = normalize(heading)
    for para in doc.paragraphs:
        if not target:
            break
        text_n = normalize(para.text)
        if text_n == target and (level is None or _heading_level(para) in {level, 0, None}):
            return para
    for para in doc.paragraphs:
        if normalize(para.text) == target:
            return para
    return None


def _heading_level(para: Paragraph) -> int | None:
    """从样式名推断标题级别。"""
    name = para.style.name if para.style is not None else ""
    match = re.search(r"(\d+)$", str(name))
    return int(match.group(1)) if match else None


def paragraphs_after_heading(doc: DocxDocument, heading: str, level: int | None = None) -> list[Paragraph]:
    """取某标题之后、下一标题之前的段落。"""
    paras = doc.paragraphs
    start = None
    for idx, para in enumerate(paras):
        if normalize(para.text) == normalize(heading):
            start = idx
            break
    if start is None:
        return []
    out: list[Paragraph] = []
    for para in paras[start + 1 :]:
        if _heading_level(para) is not None:
            break
        out.append(para)
    return out


def existing_header_parts(doc: DocxDocument) -> list[Any]:
    """返回母本中真实存在的页眉 part。

    注意：不能直接访问 section.first_page_header / even_page_header，python-docx
    会在访问时「创建」空白页眉 part，从而改动包结构（违反样式零改动）。
    """
    parts: list[Any] = []
    seen: set[int] = set()
    for section in doc.sections:
        for ref in section._sectPr.xpath("./w:headerReference"):
            rid = ref.get(qn("r:id"))
            if not rid:
                continue
            part = doc.part.related_parts[rid]
            if id(part) in seen:
                continue
            seen.add(id(part))
            parts.append(part)
    return parts


def header_paragraphs(doc: DocxDocument, contains: str) -> list[Paragraph]:
    """页眉中按文本定位段落（受控编码/版本号所在位置）。"""
    needle = normalize(contains)
    hits: list[Paragraph] = []
    for part in existing_header_parts(doc):
        for p_element in part._element.xpath(".//w:p"):
            para = Paragraph(p_element, part)
            if needle and needle in normalize(para.text):
                hits.append(para)
    return hits


def header_grid_map(table: Table, header_rows: int) -> list[tuple[int, str]]:
    """表头区的 (网格列, 文本) 列表。"""
    pairs: list[tuple[int, str]] = []
    for row_index in range(min(header_rows, len(table.rows))):
        for cell, grid in row_grid_cells(table.rows[row_index]):
            text = cell_text(cell)
            if text:
                pairs.append((grid, text))
    return pairs


def column_index_map(table: Table, spec: TableSpec, columns: list[tuple[str, str]]) -> dict[str, int]:
    """列 key → 网格列号；优先按列标签匹配表头，匹配不到再按声明顺序对齐。"""
    header_rows = max(1, spec.header_rows)
    pairs = header_grid_map(table, header_rows)
    mapping: dict[str, int] = {}
    used: set[int] = set()
    for key, label in columns:
        want = normalize(label or key)
        if not want:
            continue
        for grid, text in pairs:
            if grid in used:
                continue
            if text == want or want in text:
                mapping[key] = grid
                used.add(grid)
                break
    if len(mapping) < len(columns):
        data_cells = row_grid_cells(table.rows[min(header_rows, len(table.rows) - 1)])
        fallback_grids = [grid for _cell, grid in data_cells]
        for order, (key, _label) in enumerate(columns):
            if key not in mapping and order < len(fallback_grids):
                mapping[key] = fallback_grids[order]
    return mapping


def _is_total_row(row_cell_texts: list[str], label: str | None) -> bool:
    if not label:
        return False
    return any(normalize(label) in t for t in row_cell_texts if t)


def analyze_data_area(table: Table, spec: TableSpec, columns: list[tuple[str, str]]) -> RowsTarget:
    """识别表头 / 数据行 / 合计行，给出可用于克隆的模板行。"""
    rows = list(table.rows)
    if len(rows) <= spec.header_rows:
        raise LookupError("表格没有数据行区域")
    mapping = column_index_map(table, spec, columns)
    total_row: int | None = None
    data_rows: list[int] = []
    for idx in range(spec.header_rows, len(rows)):
        texts = [cell_text(c) for c in distinct_row_cells(rows[idx])]
        if _is_total_row(texts, spec.total_row_label):
            total_row = idx
            continue
        data_rows.append(idx)
    if not data_rows:
        raise LookupError("表格数据区为空，无法确定模板行")
    return RowsTarget(
        table=table,
        header_rows=spec.header_rows,
        template_row=data_rows[0],
        data_rows=data_rows,
        columns=mapping,
        total_row=total_row,
    )


def resolve_slot(doc: DocxDocument, slot: Slot) -> list[Target]:
    """解析一个槽位的全部锚点；任一锚点未命中即视为该槽位未命中。"""
    targets: list[Target] = []
    for anchor in slot.anchors:
        targets.append(resolve_anchor(doc, slot, anchor))
    return targets


def resolve_anchor(doc: DocxDocument, slot: Slot, anchor: Anchor) -> Target:
    """把单个锚点解析为可写入目标。"""
    slot_key = slot.key
    """按锚点类型分发定位。"""
    try:
        if anchor.type == "global_variable":
            keyword = anchor.keyword or ""
            hits = [p for p in iter_all_paragraphs(doc) if keyword and keyword in p.text]
            if not hits:
                raise LookupError(f"未找到占位关键词 {keyword!r}")
            return GlobalTarget(paragraphs=hits, keyword=keyword)
        if anchor.type == "table_cell":
            return _resolve_table_cell(doc, slot_key, anchor)
        if anchor.type == "table_rows":
            table = find_table(doc, anchor.table_header)
            spec = slot.table or TableSpec()
            return analyze_data_area(table, spec, [(c.key, c.label) for c in slot.columns])
        if anchor.type == "paragraph_after_label":
            label = anchor.paragraph_label or slot.label
            para = find_paragraph_by_label(doc, label, anchor.paragraph_match)
            if para is None:
                raise LookupError(f"未找到标签段落 {label!r}")
            return ParagraphTarget(paragraph=para, mode="after_label", label=label)
        if anchor.type in {"replace_paragraph", "section_body", "image_placeholder"}:
            para = _resolve_paragraph_anchor(doc, slot, anchor)
            if anchor.type == "section_body":
                return ParagraphTarget(paragraph=para, mode="append_after")
            if anchor.type == "image_placeholder":
                # 图片占位保留「结构式：」这类标签，只在冒号后写占位提示，由人工贴图
                label = anchor.paragraph_label or slot.label
                return ParagraphTarget(paragraph=para, mode="after_label", label=label)
            return ParagraphTarget(paragraph=para, mode="replace")
        if anchor.type == "header_field":
            paras = header_paragraphs(doc, anchor.header_contains or slot.label)
            if not paras:
                raise LookupError(f"页眉未找到 {anchor.header_contains!r}")
            return ParagraphTarget(
                paragraph=paras[0], mode="after_label", label=anchor.header_contains or slot.label
            )
        raise LookupError(f"未知锚点类型 {anchor.type}")
    except LookupError as exc:
        raise AnchorUnresolvedError(slot_key, str(exc)) from exc


def _resolve_table_cell(doc: DocxDocument, slot_key: str, anchor: Anchor) -> CellTarget:
    """定位单个单元格：优先表头 + 行标签，其次纯坐标（必须带 guard 校验）。"""
    table = find_table(doc, anchor.table_header)
    rows = list(table.rows)
    if anchor.row_index is not None and anchor.col_index is not None:
        cells = distinct_row_cells(rows[anchor.row_index])
        if anchor.col_index >= len(cells):
            raise LookupError(f"行 {anchor.row_index} 无第 {anchor.col_index} 列")
        row_text = "|".join(cell_text(c) for c in cells)
        if anchor.guard and normalize(anchor.guard) not in row_text:
            raise LookupError(f"坐标锚点 guard 校验失败，期望行内包含 {anchor.guard!r}")
        if anchor.col_index >= len(cells):
            raise LookupError("目标值单元格越界")
        return CellTarget(table=table, row=anchor.row_index, col=anchor.col_index)
    if anchor.row_label is None:
        raise LookupError("缺少 row_label 或坐标定义")
    label_n = normalize(anchor.row_label)
    for row_idx, row in enumerate(rows):
        grid_cells = row_grid_cells(row)
        hit_index = None
        for pos, (cell, _grid) in enumerate(grid_cells):
            text = cell_text(cell)
            if text == label_n if anchor.row_match == "exact" else label_n in text:
                hit_index = pos
                break
        if hit_index is None:
            continue
        if anchor.guard and normalize(anchor.guard) not in "|".join(cell_text(c) for c, _g in grid_cells):
            raise LookupError(f"行锚点 guard 校验失败，期望包含 {anchor.guard!r}")
        col = _pick_column(grid_cells, hit_index, anchor)
        if col is None:
            raise LookupError(f"行 {anchor.row_label!r} 中未找到目标列")
        return CellTarget(table=table, row=row_idx, col=col)
    raise LookupError(f"未找到行标签 {anchor.row_label!r}")


def _pick_column(grid_cells: list[tuple[_Cell, int]], label_pos: int, anchor: Anchor) -> int | None:
    """确定值所在网格列：显式列号 > 列头文本 > 标签右侧首个单元格。"""
    if anchor.col_index is not None:
        return anchor.col_index
    if anchor.column_header:
        want = normalize(anchor.column_header)
        for cell, grid in grid_cells:
            text = cell_text(cell)
            if text == want or (want and want in text):
                return grid
    if label_pos + 1 < len(grid_cells):
        return grid_cells[label_pos + 1][1]
    return None


def _resolve_paragraph_anchor(doc: DocxDocument, slot: Slot, anchor: Anchor) -> Paragraph:
    """段落类锚点：显式标签 > 颜色提示语 > 章节标题后首段。"""
    if anchor.paragraph_label:
        para = find_paragraph_by_label(doc, anchor.paragraph_label, anchor.paragraph_match)
        if para is None:
            raise LookupError(f"未找到段落 {anchor.paragraph_label!r}")
        return para
    if anchor.color:
        paras = [p for p in find_paragraphs_by_color(doc, anchor.color) if normalize(p.text)]
        if anchor.heading:
            paras = [p for p in paras if _near_heading(doc, p, anchor.heading)]
        if not paras:
            raise LookupError(f"未找到颜色 {anchor.color} 的提示语段落")
        return paras[0]
    if anchor.heading:
        body = paragraphs_after_heading(doc, anchor.heading, anchor.heading_level)
        if not body:
            # 母本中该章节下没有预留正文段落（如 6.1 质量标准信息），补一个默认样式段落
            head = find_heading(doc, anchor.heading, anchor.heading_level)
            if head is None:
                raise LookupError(f"未找到章节标题 {anchor.heading!r}")
            return new_paragraph_after(head)
        idx = min(anchor.after_heading, len(body) - 1)
        return body[idx]
    raise LookupError("段落锚点缺少 paragraph_label / color / heading")


def new_paragraph_after(paragraph: Paragraph) -> Paragraph:
    """在指定段落之后插入一个空的默认样式段落（不引入新样式）。"""
    new_p = deepcopy(_BLANK_P)
    paragraph._p.addnext(new_p)
    return Paragraph(new_p, paragraph._parent)


def _near_heading(doc: DocxDocument, para: Paragraph, heading: str) -> bool:
    """判断提示语段落是否紧跟在指定标题之后。"""
    paras = doc.paragraphs
    try:
        pos = paras.index(para)
    except ValueError:
        return False
    for back in range(1, 4):
        if pos - back < 0:
            break
        if normalize(paras[pos - back].text) == normalize(heading):
            return True
    return False
