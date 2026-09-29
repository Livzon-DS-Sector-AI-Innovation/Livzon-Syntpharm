"""docx 母本 → 全内容 Markdown（基于已有 python-docx 依赖，零新增包）。

定位：交付物模板页「模板 Markdown」弹窗的数据源——把 Word 模板文档整体解析为
Markdown 全文（标题、段落、列表、表格按文档流顺序输出），而不是填写项骨架。

设计约束：
- 按 ``body`` 子元素顺序遍历，段落与表格交错不错位（python-docx 的
  ``doc.paragraphs``/``doc.tables`` 分离迭代做不到这一点）。
- 标题识别只认样式（``Heading 1``–``Heading 6`` / 中文 ``标题 1``–``标题 6`` /
  ``Title``），不做「加粗短行猜标题」的启发式，避免把强调文字误判成章节。
- 表格输出 GFM：首行为表头；单元格内换行转 ``<br>``、竖线转义；合并单元格
  在 python-docx 中按重复文本展开，此处原样保留（母本表格以展示为准）。
- 页眉页脚、图片、批注、目录域不进入文本视图。

只读转换、不落库；成文链路（锚点回填母本 docx）与本文件无关。
"""

from __future__ import annotations

import io
import re

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

# 样式名 → 标题级别：兼容英文 Word 与中文版式（"标题 1"/"标题1"）
_HEADING_RE = re.compile(r"^(?:heading|标题)\s*([1-6])\s*$", re.IGNORECASE)
_TITLE_STYLES = {"title", "标题"}
# 列表样式（除 numPr 外的兜底识别，如 "List Paragraph" 系）
_LIST_STYLE_RE = re.compile(r"^(list|列表)", re.IGNORECASE)

_MULTI_BLANK_RE = re.compile(r"\n{3,}")

# 正文文本里会被误当 Markdown 语法的字符：反斜杠、反引号、星号/下划线（强调）、
# 尖括号（HTML/自动链接，rehype-raw 下还有注入风险）、方括号（链接）。母本正文常见
# 涂黑公司名 ``****``、``*100%`` 等，不转义就会被当成强调符——星号被吃掉并错加粗斜体。
_MD_ESCAPE_RE = re.compile(r"([\\`*_<>[\]])")


def _escape_md_text(text: str) -> str:
    """转义文本 run 里的 Markdown 语法字符；结构标记（# 标题、- 列表、| 表格、<br>）由调用方在转义之后再加。"""
    return _MD_ESCAPE_RE.sub(r"\\\1", text)


def _heading_level(style_name: str | None) -> int:
    """样式名映射标题级别；非标题样式返回 0。"""
    if not style_name:
        return 0
    name = style_name.strip()
    match = _HEADING_RE.match(name)
    if match:
        return int(match.group(1))
    if name.lower() in _TITLE_STYLES:
        return 1
    return 0


def _is_list_item(para: Paragraph) -> bool:
    """项目符号/编号列表：优先看 numPr，其次看列表样式名。"""
    ppr = para._p.pPr
    if ppr is not None and ppr.numPr is not None:
        return True
    style_name = para.style.name if para.style is not None else None
    return bool(style_name and _LIST_STYLE_RE.match(style_name.strip()))


def _paragraph_lines(para: Paragraph) -> list[str]:
    text = para.text.strip()
    if not text:
        return []
    text = _escape_md_text(text)
    level = _heading_level(para.style.name if para.style is not None else None)
    if level:
        return ["", f"{'#' * level} {text}", ""]
    prefix = "- " if _is_list_item(para) else ""
    return [f"{prefix}{text}", ""]


def _cell_text(raw: str) -> str:
    """单元格文本压平：先转义正文语法字符，再换行转 <br>、竖线转义，避免撑破 GFM 表格。"""
    text = re.sub(r"\s*\n\s*", "<br>", _escape_md_text(raw.strip()))
    return text.replace("|", "\\|")


def _table_lines(table: Table) -> list[str]:
    rows = list(table.rows)
    if not rows:
        return []
    width = max(len(row.cells) for row in rows)
    if width == 0:
        return []
    lines: list[str] = [""]
    for index, row in enumerate(rows):
        cells = [_cell_text(cell.text) for cell in row.cells]
        cells += [""] * (width - len(cells))
        lines.append("| " + " | ".join(cells) + " |")
        if index == 0:
            lines.append("| " + " | ".join(["---"] * width) + " |")
    lines.append("")
    return lines


def render_docx_markdown(data: bytes) -> str:
    """把 docx 字节流转为全内容 Markdown 文本。

    损坏/非法 docx 会抛 ``docx`` 底层异常（zipfile.BadZipFile、ValueError 等），
    由调用方决定回退策略（本模块不做吞异常的兜底）。
    """
    doc = Document(io.BytesIO(data))
    lines: list[str] = []
    for child in doc.element.body.iterchildren():
        if child.tag == qn("w:p"):
            lines.extend(_paragraph_lines(Paragraph(child, doc)))
        elif child.tag == qn("w:tbl"):
            lines.extend(_table_lines(Table(child, doc)))
    text = _MULTI_BLANK_RE.sub("\n\n", "\n".join(lines)).strip()
    return f"{text}\n" if text else ""


__all__ = ["render_docx_markdown"]
