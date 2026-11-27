"""检验数据导出为 xlsx（按判定等级给单元格上底色）。"""

from __future__ import annotations

import io
import logging
import uuid
from datetime import datetime

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.modules.quality.qc_report.constants import (
    LEVEL_INTERNAL,
    LEVEL_LABELS,
    LEVEL_OOS,
    LEVEL_PENDING,
    LEVEL_TREND,
)
from app.modules.quality.qc_report.models import QcItem
from app.modules.quality.qc_report.repository import (
    get_batches_page,
    get_product,
    get_values_by_batch_ids,
    list_items,
)

logger = logging.getLogger(__name__)

MAX_EXPORT_ROWS = 50000

_FILLS = {
    LEVEL_OOS: PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid"),
    LEVEL_INTERNAL: PatternFill(start_color="FFD9B3", end_color="FFD9B3", fill_type="solid"),
    LEVEL_TREND: PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid"),
}
_FONTS = {
    LEVEL_OOS: Font(color="9C0006", size=10),
    LEVEL_INTERNAL: Font(color="B45309", size=10),
    LEVEL_TREND: Font(color="8A6D00", size=10),
    LEVEL_PENDING: Font(color="A4A097", size=10, italic=True),
}
_HEADER_FILL = PatternFill(start_color="F6F5F4", end_color="F6F5F4", fill_type="solid")


async def export_product_xlsx(
    db: AsyncSession,
    product_id: uuid.UUID,
    batch_no: str | None = None,
    level: str | None = None,
) -> tuple[bytes, str]:
    """导出当前筛选结果为 xlsx，返回 (文件内容, 建议文件名)。"""
    product = await get_product(db, product_id)
    if product is None:
        raise NotFoundException("品种", str(product_id))

    items = [item for item in await list_items(db, product_id) if item.is_enabled]
    batches, total = await get_batches_page(db, product_id, 1, MAX_EXPORT_ROWS, batch_no, level)
    values = await get_values_by_batch_ids(db, [batch.id for batch in batches])
    grouped: dict[uuid.UUID, dict[uuid.UUID, tuple[str | None, str]]] = {}
    for value in values:
        grouped.setdefault(value.batch_id, {})[value.item_id] = (value.actual_value, value.level)

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = product.name[:28] or "检验数据"

    # 表头按 column_group_start 还原 Excel 的合并样式：
    # 合并组跨列（可见异物初检占 4 列），独立列纵向合并占满两行
    has_sub_header = any(item.sub_label for item in items)
    header_rows = 2 if has_sub_header else 1
    data_start_row = header_rows + 1
    header_font = Font(bold=True, size=10, color="1A1A1A")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    def write_header(row: int, column: int, value: str) -> None:
        cell = sheet.cell(row=row, column=column, value=value)
        cell.font = header_font
        cell.fill = _HEADER_FILL
        cell.alignment = header_align

    write_header(1, 1, "批号")
    if has_sub_header:
        sheet.merge_cells(start_row=1, start_column=1, end_row=2, end_column=1)

    groups: list[list[QcItem]] = []
    for item in items:
        key = item.column_group_start or item.sort_order
        if groups and (groups[-1][0].column_group_start or groups[-1][0].sort_order) == key:
            groups[-1].append(item)
        else:
            groups.append([item])

    column = 2
    for group in groups:
        head = group[0]
        span = len(group)
        if span > 1:
            sheet.merge_cells(start_row=1, start_column=column, end_row=1, end_column=column + span - 1)
            write_header(1, column, head.item_name)
            if has_sub_header:
                for offset, member in enumerate(group):
                    write_header(2, column + offset, member.sub_label or "")
        else:
            if has_sub_header:
                sheet.merge_cells(start_row=1, start_column=column, end_row=2, end_column=column)
            write_header(1, column, head.item_name)
        column += span

    total_columns = column - 1

    for row_index, batch in enumerate(batches, start=data_start_row):
        batch_values = grouped.get(batch.id, {})
        batch_cell = sheet.cell(row=row_index, column=1, value=batch.batch_no)
        batch_cell.font = Font(size=10, bold=True)
        for column_index, item in enumerate(items, start=2):
            actual, value_level = batch_values.get(item.id, (None, LEVEL_PENDING))
            # 空值与界面保持一致，用短横线而不是「待检」，避免两边口径不同
            cell = sheet.cell(row=row_index, column=column_index, value=actual if actual else "—")
            cell.alignment = Alignment(horizontal="center", vertical="center")
            if value_level in _FILLS:
                cell.fill = _FILLS[value_level]
            if value_level in _FONTS:
                cell.font = _FONTS[value_level]

    sheet.freeze_panes = f"B{data_start_row}"
    sheet.column_dimensions["A"].width = 16
    for column_index in range(2, total_columns + 1):
        sheet.column_dimensions[get_column_letter(column_index)].width = 14
    sheet.row_dimensions[1].height = 34
    if has_sub_header:
        sheet.row_dimensions[2].height = 20

    # 末尾附一行图例，避免收到文件的人不知道底色含义
    legend_row = data_start_row + len(batches) + 1
    sheet.cell(row=legend_row, column=1, value="图例").font = Font(bold=True, size=9)
    for offset, level_key in enumerate((LEVEL_OOS, LEVEL_INTERNAL, LEVEL_TREND), start=2):
        cell = sheet.cell(row=legend_row, column=offset, value=LEVEL_LABELS[level_key])
        cell.fill = _FILLS[level_key]
        cell.font = _FONTS[level_key]

    buffer = io.BytesIO()
    workbook.save(buffer)
    workbook.close()

    stamp = datetime.now().strftime("%Y%m%d")
    file_name = f"{product.name}_检验数据_{stamp}.xlsx"
    logger.info(
        "qc_report exported",
        extra={"product_id": str(product_id), "batch_count": total, "column_count": total_columns},
    )
    return buffer.getvalue(), file_name


__all__ = ["export_product_xlsx"]
