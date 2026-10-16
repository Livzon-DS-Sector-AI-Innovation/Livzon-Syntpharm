"""Feishu spreadsheet cross-tab import adapter for energy data.

Parses cross-tab (交叉表) formatted spreadsheets from Feishu,
extracts workshop/date/energy values, and batch-creates records.

Supported cross-tab layouts:

Layout A — rows are workshop+energy, columns are date ranges::

    | 车间       | 能源类型 | 2026/05/01-06 | 2026/05/07-13 | ...
    | 固体制剂车间 | 电      | 1234.5        | 2345.6        |
    | 固体制剂车间 | 水      | 56.7          | 67.8          |

Layout B — rows are workshops, columns are date×energy grouped::

    | 车间       | 2026/05/01-06           | 2026/05/07-13           |
    |           | 电     | 水    | 汽      | 电     | 水    | 汽      |
    | 固体制剂车间 | 1234  | 56   | 78     | 2345  | 67   | 89     |
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.energy import repository as repo
from app.modules.energy.models import EnergyWorkshop
from app.modules.energy.schemas import EnergyMonthlyRecordCreate
from app.platform.integrations.feishu.spreadsheet import SpreadsheetClient

logger = logging.getLogger(__name__)

# ── Date range parsing ──

_DATE_RANGE_RE = re.compile(
    r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})"
    r"(?:\s*[-–~至]\s*(?:(\d{1,2})[/-])?(\d{1,2}))?"
)

_ENERGY_TYPE_MAP: dict[str, str] = {
    "电": "electricity",
    "电力": "electricity",
    "用电": "electricity",
    "electricity": "electricity",
    "水": "water",
    "用水": "water",
    "water": "water",
    "汽": "steam",
    "蒸汽": "steam",
    "steam": "steam",
    "天然气": "natural_gas",
    "燃气": "natural_gas",
    "natural_gas": "natural_gas",
}

_UNIT_MAP: dict[str, str] = {
    "electricity": "kWh",
    "water": "m³",
    "steam": "t",
    "natural_gas": "Nm³",
}


@dataclass
class DateRange:
    """A parsed date range from a column header."""

    start: date
    end: date

    def __str__(self) -> str:
        return f"{self.start.isoformat()}~{self.end.isoformat()}"


@dataclass
class ParsedRecord:
    """A single parsed energy record from the cross-tab."""

    workshop_name: str
    energy_type: str
    date_range: DateRange
    value: Decimal
    unit: str
    remark: str | None = None


@dataclass
class ImportResult:
    """Result of a feishu import operation."""

    workshops_created: int = 0
    workshops_existing: int = 0
    records_created: int = 0
    records_skipped: int = 0
    errors: list[str] = field(default_factory=list)


def parse_date_range(text: str) -> DateRange | None:
    """Parse date range from header text like '2026/05/01-06' or '5月1日-6日'.

    Supported formats:
    - ``2026/05/01-06`` → May 1 to May 6
    - ``2026/05/01-05/06`` → May 1 to May 6
    - ``2026/05/01~05/06`` → same
    - ``2026-05-01`` → single day
    """
    text = text.strip()
    match = _DATE_RANGE_RE.search(text)
    if not match:
        return None

    year = int(match.group(1))
    month = int(match.group(2))
    day_start = int(match.group(3))

    if match.group(5):
        # Has end day
        end_day = int(match.group(5))
        if match.group(4):
            # Has end month: "05/01-05/06" or "05/01-06" where group(4) is month
            end_month = int(match.group(4))
        else:
            # Just end day: "05/01-06" means day 1 to day 6 of same month
            end_month = month
    else:
        # Single date
        end_month = month
        end_day = day_start

    try:
        start = date(year, month, day_start)
        end = date(year, end_month, end_day)
    except ValueError:
        return None

    return DateRange(start=start, end=end)


def parse_energy_type(text: str) -> str | None:
    """Map Chinese/English energy type text to canonical type."""
    text = text.strip().lower()
    return _ENERGY_TYPE_MAP.get(text)


def _cell_str(cell: Any) -> str:
    """Convert a cell value to stripped string."""
    if cell is None:
        return ""
    return str(cell).strip()


def _cell_float(cell: Any) -> Decimal | None:
    """Convert a cell value to Decimal, returning None for empty/invalid."""
    text = _cell_str(cell)
    if not text or text in ("-", "/", "—", ""):
        return None
    try:
        return Decimal(text.replace(",", ""))
    except InvalidOperation:
        return None


# ── Cross-tab parsing ──


def _detect_layout(rows: list[list[Any]]) -> tuple[str, int]:
    """Detect the cross-tab layout and return (layout, header_row_index).

    Returns:
        Tuple of (layout_type, header_row_index).
        layout_type is "A" or "B".
    """
    for i, row in enumerate(rows[:5]):
        cells = [_cell_str(c) for c in row]
        # Layout A: header row has "车间" + "能源类型" + date ranges
        has_workshop = any("车间" in c for c in cells)
        has_energy_col = any("能源" in c for c in cells)
        has_date = any(parse_date_range(c) is not None for c in cells)

        if has_workshop and has_energy_col and has_date:
            return "A", i
        if has_workshop and has_date:
            # Could be layout A without energy column, or layout B top header
            # Check next row for sub-headers
            if i + 1 < len(rows):
                next_cells = [_cell_str(c) for c in rows[i + 1]]
                has_energy_sub = any(parse_energy_type(c) is not None for c in next_cells if c)
                if has_energy_sub:
                    return "B", i
            return "A", i

    # Default: assume layout A with header at row 0
    return "A", 0


def _find_col_indices(header_row: list[str], layout: str) -> tuple[int, int | None, list[int]]:
    """Find workshop_col, energy_col, and date_col_indices from header row.

    Returns:
        (workshop_col_idx, energy_col_idx_or_none, [date_col_indices])
    """
    workshop_col = -1
    energy_col = -1
    date_cols: list[int] = []

    for i, cell in enumerate(header_row):
        if "车间" in cell and workshop_col < 0:
            workshop_col = i
        elif "能源" in cell and energy_col < 0:
            energy_col = i
        elif parse_date_range(cell) is not None:
            date_cols.append(i)

    return workshop_col, energy_col if energy_col >= 0 else None, date_cols


def parse_cross_tab(rows: list[list[Any]]) -> list[ParsedRecord]:
    """Parse a cross-tab formatted spreadsheet into records.

    Args:
        rows: 2-D list of cell values from the spreadsheet.

    Returns:
        List of parsed records.
    """
    if not rows:
        return []

    layout, header_idx = _detect_layout(rows)
    header_cells = [_cell_str(c) for c in rows[header_idx]]
    workshop_col, energy_col, date_cols = _find_col_indices(header_cells, layout)

    if workshop_col < 0 or not date_cols:
        logger.warning("Cannot detect cross-tab layout. Header: %s", header_cells)
        return []

    records: list[ParsedRecord] = []

    if layout == "A":
        records = _parse_layout_a(rows, header_idx, workshop_col, energy_col, date_cols)
    else:
        # Layout B: need sub-header row for energy types
        sub_header_idx = header_idx + 1
        records = _parse_layout_b(rows, header_idx, sub_header_idx, workshop_col, date_cols)

    return records


def _parse_layout_a(
    rows: list[list[Any]],
    header_idx: int,
    workshop_col: int,
    energy_col: int | None,
    date_cols: list[int],
) -> list[ParsedRecord]:
    """Parse Layout A: each row is a workshop (optionally with energy type)."""
    records: list[ParsedRecord] = []
    header_cells = [_cell_str(c) for c in rows[header_idx]]

    # Pre-parse date ranges from headers
    date_ranges: dict[int, DateRange] = {}
    for col_idx in date_cols:
        dr = parse_date_range(header_cells[col_idx])
        if dr:
            date_ranges[col_idx] = dr

    # Track current workshop name for merged cells
    current_workshop = ""

    for row in rows[header_idx + 1 :]:
        cells = [_cell_str(c) for c in row]
        if not any(cells):
            continue

        # Workshop name
        ws_name = cells[workshop_col] if workshop_col < len(cells) else ""
        if ws_name:
            current_workshop = ws_name
        elif not current_workshop:
            continue

        # Energy type
        if energy_col is not None and energy_col < len(cells):
            energy_text = cells[energy_col]
            energy_type = parse_energy_type(energy_text)
            if energy_type is None:
                continue
        else:
            # No energy column — try to detect from context or default
            energy_type = "electricity"

        # Values for each date range
        for col_idx in date_cols:
            if col_idx >= len(cells):
                continue
            value = _cell_float(cells[col_idx])
            if value is None:
                continue
            dr = date_ranges.get(col_idx)
            if dr is None:
                continue

            records.append(
                ParsedRecord(
                    workshop_name=current_workshop,
                    energy_type=energy_type,
                    date_range=dr,
                    value=value,
                    unit=_UNIT_MAP.get(energy_type, ""),
                )
            )

    return records


def _parse_layout_b(
    rows: list[list[Any]],
    header_idx: int,
    sub_header_idx: int,
    workshop_col: int,
    date_cols: list[int],
) -> list[ParsedRecord]:
    """Parse Layout B: date ranges span multiple columns with energy sub-headers."""
    records: list[ParsedRecord] = []
    header_cells = [_cell_str(c) for c in rows[header_idx]]
    sub_header_cells = [_cell_str(c) for c in rows[sub_header_idx]]

    # Build date range mapping: for each column, determine which date range it belongs to
    # In Layout B, a date range header spans multiple columns (one per energy type)
    col_to_date_range: dict[int, DateRange] = {}
    current_date_range: DateRange | None = None

    for i, cell in enumerate(header_cells):
        dr = parse_date_range(cell)
        if dr:
            current_date_range = dr
        # All columns after a date header (until next date header) belong to that date range
        if current_date_range and i > workshop_col:
            col_to_date_range[i] = current_date_range

    # Now build col_info for columns that have energy types in sub-header
    col_info: dict[int, tuple[DateRange, str]] = {}
    for col_idx in col_to_date_range:
        if col_idx < len(sub_header_cells):
            energy_text = sub_header_cells[col_idx]
            energy_type = parse_energy_type(energy_text)
            if energy_type:
                dr = col_to_date_range[col_idx]
                col_info[col_idx] = (dr, energy_type)

    current_workshop = ""

    for row in rows[sub_header_idx + 1 :]:
        cells = [_cell_str(c) for c in row]
        if not any(cells):
            continue

        ws_name = cells[workshop_col] if workshop_col < len(cells) else ""
        if ws_name:
            current_workshop = ws_name
        elif not current_workshop:
            continue

        # Process all columns that have energy type info
        for col_idx, (dr, energy_type) in col_info.items():
            if col_idx >= len(cells):
                continue
            value = _cell_float(cells[col_idx])
            if value is None:
                continue

            records.append(
                ParsedRecord(
                    workshop_name=current_workshop,
                    energy_type=energy_type,
                    date_range=dr,
                    value=value,
                    unit=_UNIT_MAP.get(energy_type, ""),
                )
            )

    return records


# ── Import service ──


class FeishuEnergyImporter:
    """Import energy data from Feishu spreadsheets."""

    def __init__(self) -> None:
        self.spreadsheet = SpreadsheetClient()

    async def import_from_spreadsheet(
        self,
        db: AsyncSession,
        spreadsheet_token: str,
        sheet_id: str | None = None,
        *,
        source: str = "feishu",
        dry_run: bool = False,
    ) -> ImportResult:
        """Import energy data from a Feishu spreadsheet.

        Args:
            db: Database session.
            spreadsheet_token: Feishu spreadsheet token.
            sheet_id: Specific sheet ID. If None, uses the first sheet.
            source: Data source label.
            dry_run: If True, parse but don't write to database.

        Returns:
            ImportResult with counts and errors.
        """
        result = ImportResult()

        # 1. Read spreadsheet data
        try:
            if sheet_id:
                rows = await self.spreadsheet.read_sheet(spreadsheet_token, sheet_id)
            else:
                meta = await self.spreadsheet.get_sheet_meta(spreadsheet_token)
                if not meta:
                    result.errors.append("Spreadsheet has no sheets")
                    return result
                first_sheet_id = meta[0].get("sheet_id", "")
                rows = await self.spreadsheet.read_sheet(spreadsheet_token, first_sheet_id)
        except Exception as exc:
            result.errors.append(f"Failed to read spreadsheet: {exc}")
            logger.exception("Failed to read spreadsheet %s", spreadsheet_token)
            return result

        if not rows:
            result.errors.append("Spreadsheet is empty")
            return result

        # 2. Parse cross-tab
        parsed = parse_cross_tab(rows)
        if not parsed:
            result.errors.append(
                "No valid records parsed from cross-tab. Check that headers contain workshop names and date ranges."
            )
            return result

        logger.info("Parsed %d records from spreadsheet", len(parsed))

        if dry_run:
            result.records_created = len(parsed)
            return result

        # 3. Ensure workshops exist (auto-create by name)
        workshop_map = await self._ensure_workshops(db, parsed)

        # 4. Batch create monthly records
        record_data: list[EnergyMonthlyRecordCreate] = []
        for rec in parsed:
            workshop = workshop_map.get(rec.workshop_name)
            if workshop is None:
                result.errors.append(f"Workshop not found and could not be created: {rec.workshop_name}")
                result.records_skipped += 1
                continue

            record_data.append(
                EnergyMonthlyRecordCreate(
                    workshop_id=workshop.id,
                    energy_type=rec.energy_type,
                    record_date=rec.date_range.start,
                    date_range_end=rec.date_range.end,
                    value=float(rec.value),
                    unit=rec.unit,
                    source=source,
                    remark=rec.remark,
                )
            )

        if record_data:
            try:
                created, updated = await repo.batch_upsert_monthly_records(db, [r.model_dump() for r in record_data])
                result.records_created = len(created)
                result.records_skipped = updated
            except Exception as exc:
                result.errors.append(f"Batch upsert failed: {exc}")
                logger.exception("Batch upsert failed")

        return result

    async def _ensure_workshops(
        self,
        db: AsyncSession,
        records: list[ParsedRecord],
    ) -> dict[str, EnergyWorkshop]:
        """Ensure all referenced workshops exist, auto-create missing ones.

        Returns:
            Mapping of workshop_name -> EnergyWorkshop ORM object.
        """
        workshop_names = sorted({r.workshop_name for r in records})
        workshop_map: dict[str, EnergyWorkshop] = {}

        for name in workshop_names:
            # Try to find by name first
            existing = await repo.get_workshop_by_name(db, name)
            if existing:
                workshop_map[name] = existing
                continue

            # Auto-create with a generated code
            code = self._generate_code(name)
            # Check if code exists
            by_code = await repo.get_workshop_by_code(db, code)
            if by_code:
                workshop_map[name] = by_code
                continue

            from app.modules.energy.models import EnergyWorkshop

            new_ws = EnergyWorkshop(
                code=code,
                name=name,
                category="workshop",
                sort_order=0,
            )
            db.add(new_ws)
            await db.flush()
            workshop_map[name] = new_ws

        return workshop_map

    @staticmethod
    def _generate_code(name: str) -> str:
        """Generate a workshop code from name."""
        # Use pinyin first letter or just a sanitized prefix
        import hashlib

        clean = re.sub(r"[^\w]", "", name)
        if clean.isascii():
            base = clean[:6].upper()
        else:
            # For Chinese names, use a hash-based short code
            h = hashlib.md5(name.encode()).hexdigest()[:6].upper()
            base = f"WS{h}"
        return base
