"""docx 表格网格寻址与文本归一化（最底层，不依赖包内其他模块）。"""

from __future__ import annotations

import re

from docx.table import Table, _Cell, _Row

_WS = re.compile(r"\s+")


def normalize(text: str) -> str:
    """归一化空白，便于跨 run/单元格的稳定文本比较。"""
    return _WS.sub("", text or "").strip()


def cell_text(cell: _Cell) -> str:
    """单元格文本（归一化）。"""
    return normalize(cell.text)


def distinct_row_cells(row: _Row) -> list[_Cell]:
    """行内去重后的单元格序列（合并单元格在 python-docx 中会重复出现）。"""
    cells: list[_Cell] = []
    for cell in row.cells:
        if not cells or cells[-1]._tc is not cell._tc:
            cells.append(cell)
    return cells


def cell_span(cell: _Cell) -> int:
    """单元格横跨的网格列数。"""
    return max(1, int(cell._tc.grid_span or 1))


def row_grid_cells(row: _Row) -> list[tuple[_Cell, int]]:
    """行内去重单元格及其网格起始列。"""
    out: list[tuple[_Cell, int]] = []
    col = 0
    for cell in row.cells:
        if out and out[-1][0]._tc is cell._tc:
            continue
        out.append((cell, col))
        col += cell_span(cell)
    return out


def cell_at_grid(table: Table, row_index: int, grid_col: int) -> _Cell | None:
    """按 (行, 网格列) 取单元格，自动处理跨列合并。"""
    rows = table.rows
    if row_index >= len(rows):
        return None
    for cell, start in row_grid_cells(rows[row_index]):
        if start <= grid_col < start + cell_span(cell):
            return cell
    return None


__all__ = ["cell_at_grid", "cell_span", "cell_text", "distinct_row_cells", "normalize", "row_grid_cells"]
