"""检验结果表 xlsx 解析。

样本结构：单 sheet，A 列批号，第 1 行表头，第 3/4/5 行分别是
**法定标准 / 3σ 标准 / 企业内控标准**，第 7 行起为数据。

每列读它**自己那一列**的标准（而不是按项目名去别处找），
这是「溶液颜色」色系列能拿到「黄色、黄绿色或橙黄色」、
色号列拿到「≤Y7/YG7/OY7」的原因。

合并表头（K1:L1、S1:V1、W1:Z1）按列展开：每个物理列都保留，
合并区内后续列沿用主表头名，并记录 `column_group_start` 供前端跨列渲染。

标准行同样存在合并（K4:N4），合并区内非左上角的单元格读不到值，
因此标准取值走 `_merged_value()`，合并区内各列共享左上角的值。
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field

import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.workbook.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

logger = logging.getLogger(__name__)

# A 列出现这些内容说明不是数据行
_MARKER_KEYWORDS = ("法定标准", "企业内控", "考核标准", "年版", "药典", "标准依据")

_BATCH_COLUMN_CANDIDATES = ("批号", "batch_no", "批 号", "lot_no")


class XlsxParseError(ValueError):
    """结果表结构不符合预期。"""


@dataclass
class ColumnHeader:
    """结果表的一列。"""

    index: int  # 1-based 列号
    letter: str
    name: str  # 用于展示与匹配的列名（= Excel 表头原文）
    raw_name: str | None = None  # 表头原始值
    merged_from: str | None = None  # 若来自合并表头，记录主表头名
    # 所属表头组的首列列号：合并区内取合并区首列，其余取自身列号。
    # 前端据此把同一组的相邻列画成一个跨列大表头。
    group_start: int | None = None
    # 合并组内续列的子列名（如 毛 / 点（总数≤5个）/ 备注），非续列或该格是标准文本则为空
    sub_label: str | None = None
    # 该列自己的三层标准，取本列第 3/4/5 行的原文（不是按项目名去别处找）
    legal_text: str | None = None  # 第 3 行：法定标准
    sigma_text: str | None = None  # 第 4 行：3σ 标准
    internal_text: str | None = None  # 第 5 行：企业内控标准


@dataclass
class ParsedBatchRow:
    """结果表的一行数据。"""

    row_number: int
    batch_no: str
    values: dict[int, str | None] = field(default_factory=dict)  # 列号 -> 原文


@dataclass
class ParsedSheet:
    headers: list[ColumnHeader]
    rows: list[ParsedBatchRow]
    sheet_title: str
    batch_column: int
    data_start_row: int


def _stringify(value: object) -> str | None:
    """把单元格值转成干净字符串，整数型浮点去掉 .0。"""
    if value is None:
        return None
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, float):
        if value != value:  # NaN
            return None
        if value.is_integer():
            return str(int(value))
        text = f"{value:.10f}".rstrip("0").rstrip(".")
        return text or "0"
    text = str(value).replace("\u3000", " ").strip()
    return text or None


def _load_first_sheet(content: bytes) -> tuple[Workbook, Worksheet]:
    try:
        workbook = openpyxl.load_workbook(io.BytesIO(content), data_only=True, read_only=False)
    except Exception as exc:  # openpyxl 对损坏文件抛的异常类型不统一
        raise XlsxParseError("文件不是有效的 Excel（xlsx），或文件已损坏") from exc
    if not workbook.sheetnames:
        raise XlsxParseError("Excel 里没有工作表")
    return workbook, workbook[workbook.sheetnames[0]]


_STANDARD_PREFIXES = ("≤", "≥", "＜", "＞", "<", ">", "=", "±")


def _read_sub_label(ws: Worksheet, col: int) -> str | None:
    """合并组续列的子列名：取第 5 行的文字（如 毛 / 点（总数≤5个）/ 备注）。

    该格若是标准文本（`一致`、`/`、比较符开头、纯数字），说明它是限值而不是子列名，返回 None。
    """
    value = _stringify(ws.cell(5, col).value)
    if not value:
        return None
    if value in ("/", "／", "一致") or value.startswith("一致"):
        return None
    if value.startswith(_STANDARD_PREFIXES):
        return None
    if re.fullmatch(r"[\d.\s%％]+", value):
        return None
    return value[:64]


def _build_headers(ws: Worksheet) -> list[ColumnHeader]:
    """构建每列的表头。

    列名一律取 Excel 表头原文，不自造 `-2`、`（AC列）` 这类后缀：

    - 第 1 行有值：用它，`group_start` = 自身列号
    - 落在第 1 行合并区：沿用合并区首列的表头名，`group_start` = 合并区首列，
      续列从第 5 行读子列名（毛 / 点 / 备注）
    - 表头为空且不在合并区：沿用上一列表头名（Excel 里是视觉延续），
      `group_start` = 自身列号，因此**不会被并进上一组**（如不溶性微粒的 AB / AC）
    """
    merged_anchor: dict[int, tuple[str, int, int]] = {}
    for merged in ws.merged_cells.ranges:
        if merged.min_row != 1 or merged.max_row != 1:
            continue
        anchor_value = _stringify(ws.cell(1, merged.min_col).value) or ""
        if not anchor_value:
            continue
        for col in range(merged.min_col, merged.max_col + 1):
            merged_anchor[col] = (anchor_value, merged.min_col, col - merged.min_col)

    headers: list[ColumnHeader] = []
    last_name: str | None = None
    for col in range(1, ws.max_column + 1):
        raw = _stringify(ws.cell(1, col).value)
        sub_label: str | None = None
        if raw:
            name = raw
            group_start = col
            merged_from = None
        elif col in merged_anchor:
            anchor, group_min, offset = merged_anchor[col]
            name = anchor
            group_start = group_min
            merged_from = anchor
            if offset > 0:
                sub_label = _read_sub_label(ws, col)
        elif last_name:
            name = last_name
            group_start = col
            merged_from = last_name
        else:
            name = f"{get_column_letter(col)}列"
            group_start = col
            merged_from = None
        last_name = name
        headers.append(
            ColumnHeader(
                index=col,
                letter=get_column_letter(col),
                name=name,
                raw_name=raw,
                merged_from=merged_from,
                group_start=group_start,
                sub_label=sub_label,
            )
        )
    return headers


def _locate_batch_column(headers: list[ColumnHeader]) -> int:
    for header in headers:
        compact = header.name.replace(" ", "")
        for candidate in _BATCH_COLUMN_CANDIDATES:
            if compact == candidate.replace(" ", ""):
                return header.index
    # 默认第一列
    return headers[0].index if headers else 1


def _locate_data_start(ws: Worksheet, batch_col: int) -> int:
    """跳过药典来源行与三层标准行，找到第一条数据行的行号。

    样本第 4 行 A 列有个 `3a`（补充标准标记），不能被当成批号，
    所以前 10 行额外排除过短的值。
    """
    for row in range(2, min(ws.max_row, 40) + 1):
        value = _stringify(ws.cell(row, batch_col).value)
        if not value:
            continue
        if any(keyword in value for keyword in _MARKER_KEYWORDS):
            continue
        if row <= 10 and len(value) < 4:
            continue
        return row
    return int(ws.max_row) + 1


def _merged_value(ws: Worksheet, row: int, column: int) -> str | None:
    """取单元格文本；若为空且落在合并区内，取合并区左上角的值。

    样本里 `K4:N4` 是合并单元格，3σ 的值写在 K4，
    色号列（L）要能读到它，所以合并区内各列共享左上角的值。
    """
    value = _stringify(ws.cell(row, column).value)
    if value is not None:
        return value
    for merged in ws.merged_cells.ranges:
        if merged.min_row <= row <= merged.max_row and merged.min_col <= column <= merged.max_col:
            return _stringify(ws.cell(merged.min_row, merged.min_col).value)
    return None


def _locate_standard_rows(ws: Worksheet, data_start_row: int) -> dict[str, int]:
    """按 A 列关键词定位三层标准行，不硬编码行号。

    样本里 A3=`法定标准`、A4=`3a`、A5=`企业内控`、A6=`考核标准`。
    定义为空或识别不到时该层整体留空，绝不因此阻塞导入。
    """
    found: dict[str, int] = {}
    last_row = min(data_start_row - 1, ws.max_row)
    for row in range(1, last_row + 1):
        raw = _stringify(ws.cell(row, 1).value)
        if not raw:
            continue
        text = raw.replace(" ", "").replace("\u3000", "")
        # 第 2 行是药典来源，长句里也含「企业内控标准」字样，必须先排除，
        # 否则会被误认成内控行（样本原文含「企业内控标准QS-C011014-04」）。
        if len(text) > 8 or "药典" in text or "年版" in text:
            continue
        if "考核" in text:
            # 考核标准不属于三层体系，直接跳过
            continue
        if "法定" in text:
            found.setdefault("legal", row)
        elif "内控" in text:
            found.setdefault("internal", row)
        elif "3σ" in text or re.fullmatch(r"3[σaA]?", text):
            found.setdefault("sigma", row)
    return found


def parse_result_xlsx(content: bytes) -> ParsedSheet:
    """解析检验结果表。"""
    workbook, ws = _load_first_sheet(content)
    try:
        headers = _build_headers(ws)
        batch_col = _locate_batch_column(headers)
        start_row = _locate_data_start(ws, batch_col)
        if start_row > ws.max_row:
            raise XlsxParseError("结果表里没有找到数据行（批号列全为空或只有标准行）")

        # 每列读自己那一列的法定 / 3σ / 内控标准
        standard_rows = _locate_standard_rows(ws, start_row)
        for header in headers:
            if header.index == batch_col:
                continue
            if "legal" in standard_rows:
                header.legal_text = _merged_value(ws, standard_rows["legal"], header.index)
            if "sigma" in standard_rows:
                header.sigma_text = _merged_value(ws, standard_rows["sigma"], header.index)
            if "internal" in standard_rows:
                header.internal_text = _merged_value(ws, standard_rows["internal"], header.index)

        rows: list[ParsedBatchRow] = []
        for row in range(start_row, ws.max_row + 1):
            batch_no = _stringify(ws.cell(row, batch_col).value)
            if not batch_no:
                continue
            if any(keyword in batch_no for keyword in _MARKER_KEYWORDS):
                continue
            values: dict[int, str | None] = {}
            for header in headers:
                if header.index == batch_col:
                    continue
                values[header.index] = _stringify(ws.cell(row, header.index).value)
            rows.append(ParsedBatchRow(row_number=row, batch_no=batch_no, values=values))

        if not rows:
            raise XlsxParseError("结果表里没有解析到任何批次数据")
    finally:
        workbook.close()

    logger.info(
        "qc_report result xlsx parsed",
        extra={
            "sheet": ws.title,
            "column_count": len(headers),
            "row_count": len(rows),
            "data_start_row": start_row,
            "standard_rows": standard_rows,
        },
    )
    return ParsedSheet(
        headers=headers,
        rows=rows,
        sheet_title=ws.title,
        batch_column=batch_col,
        data_start_row=start_row,
    )


__all__ = [
    "ColumnHeader",
    "ParsedBatchRow",
    "ParsedSheet",
    "XlsxParseError",
    "parse_result_xlsx",
]
