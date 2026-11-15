"""按写入记录回放成稿：覆盖 → 追加（引用源不进正文，只在详情页右侧展示）。

保排版的关键不是「重新生成一份文档」，而是在母本原件的节点上改文字/插节点：

- 段落内多个 run（Word 常有）→ 值写入首个 run，其余 run 清空，字体/字号/加粗都保留；
- 母本里的 ``____`` 占位 → 只替换下划线，保住「品种名称：」这类标签；
- 多行值 → 复制原段落 pPr/rPr 逐行插入，不破坏段落间距与编号；
- 追加段落/表格行 → 一律 ``deepcopy`` 母本已有节点的 pPr/rPr/tr/tcPr，
  **不接受样式名参数、不新增样式**，因此「样式集合 ⊆ 母本样式集合」由代码保证；
- 回放顺序固定：先写母本既有位置，再按写入序号追加新段落/新行。
  这样插入造成的段落下标漂移不会影响后续写入（写入用的是原始下标）。
"""

from __future__ import annotations

import logging
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, cast

from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

from app.modules.research.report_gen.structure import fingerprint, open_document

logger = logging.getLogger(__name__)

GAP_PREFIX = "待补充："
DEFAULT_OWNER = "相关部门"

# 写入记录的种类（落库在 RdReportGenSlot.anchor.kind）
KIND_PARAGRAPH = "paragraph"
KIND_TABLE_CELL = "table_cell"
KIND_APPEND_PARAGRAPH = "append_paragraph"
KIND_APPEND_TABLE_ROWS = "append_table_rows"
KIND_REFERENCES = "references"

_WRITE_KINDS = (KIND_PARAGRAPH, KIND_TABLE_CELL)


@dataclass(slots=True)
class SlotFill:
    """回放所需的写入记录快照（与 ORM 行解耦，便于单测）。"""

    slot_key: str
    label: str
    anchor: dict[str, Any] | None
    location: str | None = None
    value: str | None = None
    state: str = "pending"
    source_name: str | None = None
    evidence: str | None = None
    owner_hint: str | None = None


@dataclass(slots=True)
class RenderOutput:
    document: bytes
    unresolved: list[str] = field(default_factory=list)
    filled: int = 0
    gaps: int = 0
    written: list[str] = field(default_factory=list)


def _kind(fill: SlotFill) -> str:
    anchor = fill.anchor if isinstance(fill.anchor, dict) else {}
    return str(anchor.get("kind") or KIND_PARAGRAPH)


def _seq(fill: SlotFill) -> int:
    anchor = fill.anchor if isinstance(fill.anchor, dict) else {}
    try:
        return int(anchor.get("seq") or 0)
    except (TypeError, ValueError):
        return 0


def _gap_text(fill: SlotFill, inline: bool = False) -> str:
    owner = (fill.owner_hint or DEFAULT_OWNER).strip() or DEFAULT_OWNER
    # 接在「品种名称：」后面时不重复冒号
    return f"待补充（{owner}）" if inline else f"{GAP_PREFIX}{owner}"


def _new_paragraph_like(source: Paragraph) -> Paragraph:
    """在 source 之后插入同格式空段落（沿用母本段落的 pPr）。"""
    new_p = OxmlElement("w:p")
    p_pr = source._p.pPr  # noqa: SLF001 - 需要复制段落属性（缩进/编号/间距）
    if p_pr is not None:
        new_p.append(deepcopy(p_pr))
    source._p.addnext(new_p)  # noqa: SLF001
    return Paragraph(new_p, source._parent)


def _set_paragraph_text(paragraph: Paragraph, value: str) -> None:
    """写入文本并保留段落与首个 run 的字体属性；多行按段落拆分。"""
    lines = value.split("\n")
    first_line = lines[0]
    runs = paragraph.runs
    if runs:
        template_run = runs[0]
        template_run.text = first_line
        for run in runs[1:]:
            run.text = ""
    else:
        template_run = paragraph.add_run(first_line)

    cursor = paragraph
    for line in lines[1:]:
        new_paragraph = _new_paragraph_like(cursor)
        new_run = new_paragraph.add_run(line)
        source_rpr = template_run._r.rPr  # noqa: SLF001
        if source_rpr is not None:
            new_run._r.insert(0, deepcopy(source_rpr))  # noqa: SLF001
        cursor = new_paragraph


def _dedupe_label(paragraph: Paragraph, value: str) -> str:
    """去掉模型重复带上的「标签：」前缀，避免渲染成「报告标题：报告标题：X」。"""
    from app.modules.research.report_gen.outline import BLANK_RE

    if not value:
        return value
    text = paragraph.text or ""
    match = BLANK_RE.search(text)
    if match is None:
        # 「标签：」段没有占位符，模型可能把标签一起带回来：去掉重复标签再追加
        prefix = text.strip()
        if prefix.endswith(("：", ":")) and value.startswith(prefix):
            return value[len(prefix) :].lstrip(" ：:")
        return value
    prefix = text[: match.start()].strip()
    if prefix and value.startswith(prefix):
        # 题注「表2 XXX…」/标签「品种名称：____」：模型把前缀一起带回来时去掉
        rest = value[len(prefix) :].lstrip(" 　：:，,、")
        if rest:
            return rest
    return value


def _fill_blank(paragraph: Paragraph, value: str) -> bool:
    """把值写进段落里的下划线占位，标签与首尾文字/字体原样保留；无占位返回 False。"""
    from app.modules.research.report_gen.outline import BLANK_RE

    for run in paragraph.runs:
        text = run.text or ""
        match = BLANK_RE.search(text)
        if match is None:
            continue
        first_line, *rest = value.split("\n")
        run.text = f"{text[: match.start()]}{first_line}{text[match.end() :]}"
        cursor = paragraph
        for line in rest:
            new_paragraph = _new_paragraph_like(cursor)
            new_run = new_paragraph.add_run(line)
            source_rpr = run._r.rPr  # noqa: SLF001
            if source_rpr is not None:
                new_run._r.insert(0, deepcopy(source_rpr))  # noqa: SLF001
            cursor = new_paragraph
        return True
    return False


def _append_paragraph_text(paragraph: Paragraph, value: str) -> bool:
    """把值接在「标签：」后面；标签、段落节点和首个 run 的字体保持不变。

    多行值只把首行接在标签后，其余行按同款段落另起，避免把整段标签冲掉。
    """
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    if not lines:
        return False
    text = paragraph.text or ""
    joiner = "" if text.endswith(("：", ":", " ", "　")) else " "
    runs = paragraph.runs
    if runs:
        runs[-1].text = f"{runs[-1].text or ''}{joiner}{lines[0]}"
    else:
        paragraph.add_run(f"{joiner}{lines[0]}")
    cursor = paragraph
    for line in lines[1:]:
        new_paragraph = _new_paragraph_like(cursor)
        new_paragraph.add_run(line)
        cursor = new_paragraph
    return True


# ----------------------------------------------------------------------
# 母本既有的位置：段落 / 表格单元格
# ----------------------------------------------------------------------
def _paragraph_at(document: Any, anchor: dict[str, Any]) -> Paragraph | None:
    index = anchor.get("index")
    if not isinstance(index, int):
        return None
    paragraphs = document.paragraphs
    if 0 <= index < len(paragraphs):
        return cast(Paragraph, paragraphs[index])
    return None


def _cell_at(document: Any, anchor: dict[str, Any]) -> Any | None:
    try:
        table = document.tables[int(anchor["table_index"])]
        return table.rows[int(anchor["row"])].cells[int(anchor["col"])]
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def _cell_paragraph_at(document: Any, anchor: dict[str, Any]) -> Paragraph | None:
    cell = _cell_at(document, anchor)
    if cell is None:
        return None
    paragraphs = cell.paragraphs
    para_index = int(anchor.get("para_index") or 0)
    if 0 <= para_index < len(paragraphs):
        return cast(Paragraph, paragraphs[para_index])
    return None


def _cell_fingerprint_match(document: Any, anchor: dict[str, Any]) -> Paragraph | None:
    """表格单元格的指纹兜底：母本换版后行列可能错位，按原文在同表内重找。

    只在原文非空时启用：空单元格的指纹彼此相同，按指纹找会随机落到别的空格，
    比「找不到」更糟（会写错位置且无人察觉）。
    """
    expected = str(anchor.get("text") or "").strip()
    expected_fp = anchor.get("fingerprint")
    if not expected or not expected_fp:
        return None
    table_index = anchor.get("table_index")
    if not isinstance(table_index, int):
        return None
    try:
        table = document.tables[table_index]
    except (IndexError, TypeError):
        return None

    seen: set[str] = set()
    try:
        rows = list(table.rows)
    except (AttributeError, IndexError):
        return None
    for row in rows:
        try:
            cells = list(row.cells)
        except (AttributeError, IndexError):
            continue
        for cell in cells:
            tc = cell._tc  # noqa: SLF001 - 合并单元格去重
            marker = tc.getroottree().getpath(tc)
            if marker in seen:
                continue
            seen.add(marker)
            for paragraph in cell.paragraphs:
                if fingerprint((paragraph.text or "").strip()) == expected_fp:
                    return cast(Paragraph, paragraph)
    return None


def _filled_text(expected_text: str, written: str) -> str:
    """占位段写入后应有的整段文本：母本原文里的 ``____`` 换成写入值首行。"""
    from app.modules.research.report_gen.outline import BLANK_RE

    first_line = written.split("\n")[0].strip()
    match = BLANK_RE.search(expected_text)
    if match is None:
        return first_line
    return f"{expected_text[: match.start()]}{first_line}{expected_text[match.end() :]}"


def _appended_text(expected_text: str, written: str) -> str:
    """「标签：」段追加后的整段文本；冒号后不留空格，其他情况补一个空格。"""
    first_line = written.split("\n")[0].strip()
    label = expected_text.strip()
    joiner = "" if label.endswith(("：", ":")) else " "
    return f"{label}{joiner}{first_line}"


def _text_matches(
    text: str,
    *,
    expected_text: str,
    expected_fp: str | None,
    written: str | None,
    append: bool = False,
) -> bool:
    """锚点匹配：母本原文指纹命中，或当前文本等于「该处已写入」的样子。

    只比母本指纹会让「下划线占位段写完之后」再也定位不到自己——它的文本已经变了，
    人工编辑与还原都会报「成品里找不到这个位置」。
    """
    if not expected_text or fingerprint(text) == expected_fp:
        return True
    if not written:
        return False
    first_line = written.split("\n")[0].strip()
    if not first_line:
        return False
    if text == first_line:
        return True
    if append and text == _appended_text(expected_text, written):
        return True
    return text == _filled_text(expected_text, written).strip()


def _locate(document: Any, anchor: dict[str, Any] | None, *, written: str | None = None) -> Paragraph | None:
    """按锚点定位目标段落；索引失效时用指纹兜底。"""
    if not isinstance(anchor, dict):
        return None
    kind = anchor.get("kind") or KIND_PARAGRAPH
    append = bool(anchor.get("append"))
    if kind == KIND_TABLE_CELL:
        paragraph = _cell_paragraph_at(document, anchor)
        expected_text = str(anchor.get("text") or "").strip()
        expected_fp = anchor.get("fingerprint")
        if paragraph is not None:
            text = (paragraph.text or "").strip()
            # 原文非空时校验指纹；空位（槽位本身为空）不校验，直接写入
            if _text_matches(
                text, expected_text=expected_text, expected_fp=expected_fp, written=written, append=append
            ):
                return paragraph
        return _cell_fingerprint_match(document, anchor)
    if kind != KIND_PARAGRAPH:
        return None

    paragraph = _paragraph_at(document, anchor)
    expected_text = str(anchor.get("text") or "").strip()
    expected_fp = anchor.get("fingerprint")
    if paragraph is not None:
        text = (paragraph.text or "").strip()
        if _text_matches(
            text, expected_text=expected_text, expected_fp=expected_fp, written=written, append=append
        ):
            return paragraph

    paragraphs = document.paragraphs
    index = anchor.get("index")
    if isinstance(index, int):
        for offset in range(1, 4):
            for candidate_index in (index - offset, index + offset):
                if 0 <= candidate_index < len(paragraphs):
                    if fingerprint((paragraphs[candidate_index].text or "").strip()) == expected_fp:
                        return cast(Paragraph, paragraphs[candidate_index])

    if expected_fp:
        for candidate in paragraphs:
            if fingerprint((candidate.text or "").strip()) == expected_fp:
                return cast(Paragraph, candidate)
    return None


# ----------------------------------------------------------------------
# 追加：段落 / 表格行 / 引用源
# ----------------------------------------------------------------------
def _paragraph_element(ref: Paragraph, text: str) -> Any:
    """按 ref 段落的 pPr 与首个 run 的 rPr 造一个新段落元素（不新增样式）。"""
    new_p = OxmlElement("w:p")
    p_pr = ref._p.pPr  # noqa: SLF001
    if p_pr is not None:
        new_p.append(deepcopy(p_pr))
    run = OxmlElement("w:r")
    if ref.runs:
        r_pr = ref.runs[0]._r.rPr  # noqa: SLF001
        if r_pr is not None:
            run.append(deepcopy(r_pr))
    node = OxmlElement("w:t")
    node.set(qn("xml:space"), "preserve")
    node.text = text
    run.append(node)
    new_p.append(run)
    return new_p


def _apply_appends(document: Any, fills: list[SlotFill], unresolved: list[str]) -> int:
    """回放「在母本某段之后插入新段落」，按写入序号排序，支持链式追加。"""
    positions: dict[str, Paragraph] = {f"p{index}": item for index, item in enumerate(document.paragraphs)}
    cursor: dict[str, Paragraph] = {}
    written = 0

    for fill in sorted(fills, key=_seq):
        value = (fill.value or "").strip()
        if not value:
            # 没有正文的追加记录不该在成稿里留空段
            unresolved.append(fill.slot_key)
            continue
        anchor = fill.anchor if isinstance(fill.anchor, dict) else {}
        parent_key = str(anchor.get("after") or "")
        parent = cursor.get(parent_key) or positions.get(parent_key)
        if parent is None:
            unresolved.append(fill.slot_key)
            logger.warning(
                "report-gen append anchor unresolved",
                extra={"slot_key": fill.slot_key, "after": parent_key},
            )
            continue

        clone_index = anchor.get("clone_from")
        ref = parent
        if isinstance(clone_index, int) and 0 <= clone_index < len(document.paragraphs):
            ref = document.paragraphs[clone_index]

        last = parent
        for line in value.split("\n"):
            new_p = _paragraph_element(ref, line)
            last._p.addnext(new_p)  # noqa: SLF001
            last = Paragraph(new_p, ref._parent)
        positions[fill.slot_key] = last
        cursor[parent_key] = last
        written += 1

    return written


def _clear_paragraph(paragraph: Paragraph) -> None:
    for run in paragraph.runs:
        run.text = ""


def _set_cell_text(cell: Any, text: str) -> None:
    """写单元格首段，清掉模板行里剩余的示例文字（保留段落节点，避免破坏 tcPr）。"""
    paragraphs = cell.paragraphs
    if not paragraphs:
        paragraph = cell.add_paragraph()
        paragraph.add_run(text)
        return
    _set_paragraph_text(paragraphs[0], text)
    for extra in paragraphs[1:]:
        _clear_paragraph(extra)


def _fill_row(row: Any, cells: list[str]) -> None:
    """按列写一行；合并单元格会重复出现，同一 tc 只写一次。"""
    seen: set[str] = set()
    index = 0
    for cell in row.cells:
        tc = cell._tc  # noqa: SLF001
        marker = tc.getroottree().getpath(tc)
        if marker in seen:
            continue
        seen.add(marker)
        if index < len(cells):
            _set_cell_text(cell, cells[index])
        index += 1


def _apply_table_rows(document: Any, fills: list[SlotFill], unresolved: list[str]) -> int:
    """回放「往表格追加行」：深拷贝母本模板行（含 tcPr/边框/行高）后追加。"""
    written = 0
    for fill in sorted(fills, key=_seq):
        anchor = fill.anchor if isinstance(fill.anchor, dict) else {}
        table_index = anchor.get("table_index")
        if not isinstance(table_index, int):
            unresolved.append(fill.slot_key)
            continue
        try:
            table = document.tables[table_index]
        except (IndexError, TypeError):
            unresolved.append(fill.slot_key)
            logger.warning("report-gen table rows anchor unresolved", extra={"slot_key": fill.slot_key})
            continue

        clone_row = anchor.get("clone_from_row")
        # 工具描述里 clone_from_row 是「默认取最后一行」：没给或越界时按最后一行克隆，
        # 不能退回 add_row()——那会丢掉 tcPr（边框/行高/底色），追加行看起来像另一张表。
        if not isinstance(clone_row, int) or not (0 <= clone_row < len(table.rows)):
            clone_row = len(table.rows) - 1 if table.rows else None
        template_tr = table.rows[clone_row]._tr if clone_row is not None else None  # noqa: SLF001

        rows = anchor.get("rows")
        if not isinstance(rows, list):
            rows = []
        for row_data in rows:
            if not isinstance(row_data, dict):
                continue
            cells = [str(item) for item in (row_data.get("cells") or [])]
            if template_tr is not None:
                table._tbl.append(deepcopy(template_tr))  # noqa: SLF001
                row = table.rows[-1]
            else:
                row = table.add_row()
            _fill_row(row, cells)
        written += 1
    return written


def render_document(
    template_bytes: bytes,
    slots: list[SlotFill],
    *,
    meta: dict[str, Any] | None = None,
) -> RenderOutput:
    """在母本上回放全部写入记录，返回 docx 字节与覆盖率。

    ``meta`` 仅用于日志（哪份报告出了多少），不再产对照表。
    """
    document = open_document(template_bytes)
    unresolved: list[str] = []
    written: list[str] = []
    filled = 0
    gaps = 0

    writes = [fill for fill in slots if _kind(fill) in _WRITE_KINDS]
    appends = [fill for fill in slots if _kind(fill) == KIND_APPEND_PARAGRAPH]
    row_appends = [fill for fill in slots if _kind(fill) == KIND_APPEND_TABLE_ROWS]

    for fill in writes:
        value = (fill.value or "").strip()
        needs_value = bool(value) and fill.state in ("filled", "conflict", "pending")
        target = _locate(document, fill.anchor)
        if target is None:
            if fill.slot_key not in unresolved:
                unresolved.append(fill.slot_key)
            logger.warning(
                "report-gen slot anchor unresolved",
                extra={"slot_key": fill.slot_key, "kind": _kind(fill)},
            )
            continue
        if needs_value:
            value = _dedupe_label(target, value)
        fill_value = value if needs_value else _gap_text(fill)
        blank_filled = _fill_blank(target, value if needs_value else _gap_text(fill, inline=True))
        if not blank_filled and needs_value and (fill.anchor or {}).get("append"):
            # 「标签：」段：值接在冒号后，不能整段覆盖（否则标签会被冲掉）
            _append_paragraph_text(target, value)
        elif not blank_filled:
            _set_paragraph_text(target, fill_value)
        written.append(fill.slot_key)
        if needs_value:
            filled += 1
        else:
            gaps += 1

    filled += _apply_appends(document, appends, unresolved)
    written.extend(fill.slot_key for fill in appends if fill.slot_key not in unresolved)
    filled += _apply_table_rows(document, row_appends, unresolved)
    written.extend(fill.slot_key for fill in row_appends if fill.slot_key not in unresolved)

    output = RenderOutput(
        document=_save(document),
        unresolved=unresolved,
        filled=filled,
        gaps=gaps,
        written=written,
    )
    logger.info(
        "report-gen document rendered",
        extra={
            "title": (meta or {}).get("title"),
            "records": len(slots),
            "filled": filled,
            "gaps": gaps,
            "unresolved": len(unresolved),
        },
    )
    return output


def _save(document: Any) -> bytes:
    from io import BytesIO

    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


__all__ = [
    "GAP_PREFIX",
    "KIND_APPEND_PARAGRAPH",
    "KIND_APPEND_TABLE_ROWS",
    "KIND_PARAGRAPH",
    "KIND_REFERENCES",
    "KIND_TABLE_CELL",
    "RenderOutput",
    "SlotFill",
    "render_document",
]
