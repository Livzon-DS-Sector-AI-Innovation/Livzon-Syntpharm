"""Import gift inventory from a standard Excel template into PostgreSQL.

Usage:
    python scripts/import_gift_inventory_template.py <path_to_excel>

The Excel template should have headers in row 3 and data starting from row 4.
Expected columns: 物品名称, 规格, 计量单位, 月初库存, 本期入库/领用, 月底库存, 单价, 金额, 状态, 备注
"""

import asyncio
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import asyncpg
import pandas as pd

DB_URL = "postgresql://postgres:postgres@localhost:5432/dazah"


def parse_value(value, dtype=int, default=0):
    """Parse a cell value into int/float, handling NaN/empty."""
    import math
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return default
    try:
        if dtype == int:
            return int(float(value))
        return float(value)
    except (ValueError, TypeError):
        return default


def parse_string(value) -> str | None:
    """Parse a string value, returning None for empty/NaN."""
    import math
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    s = str(value).strip()
    return s if s and s.lower() != "nan" else None


async def import_from_excel(excel_path: Path, sheet_name: str = "库存导入模板"):
    df = pd.read_excel(excel_path, sheet_name=sheet_name, header=2)

    # Normalize column names
    col_map = {}
    for col in df.columns:
        col_str = str(col).strip().replace("*", "")
        col_map[col] = col_str
    df.rename(columns=col_map, inplace=True)

    # Drop empty rows
    df = df[df["物品名称"].notna() & (df["物品名称"] != "")]

    now = datetime.now(timezone.utc)
    rows = []
    for _, row in df.iterrows():
        name = parse_string(row.get("物品名称"))
        if not name:
            continue

        opening = parse_value(row.get("月初库存"), int, 0)
        incoming = parse_value(row.get("本期入库/领用"), int, None)
        closing = parse_value(row.get("月底库存"), int, 0)
        unit_price = parse_value(row.get("单价"), float, None)
        total = parse_value(row.get("金额"), float, None)
        status = parse_string(row.get("状态"))
        remark = parse_string(row.get("备注"))

        if not status:
            if closing == 0:
                status = "停用"
            elif closing < 5:
                status = "库存不足"
            else:
                status = "可用"

        rows.append(
            (
                uuid.uuid4(),
                name,
                parse_string(row.get("规格")),
                parse_string(row.get("计量单位")),
                opening,
                incoming,
                closing,
                unit_price,
                total,
                status,
                remark,
                now,
                now,
                False,
            )
        )

    conn = await asyncpg.connect(DB_URL)
    try:
        insert_sql = """
            INSERT INTO administration.gift_inventories
            (id, name, specification, unit, opening_stock, incoming_qty,
             closing_stock, unit_price, total_amount, status, remarks,
             created_at, updated_at, is_deleted)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        """
        for row in rows:
            await conn.execute(insert_sql, *row)
        print(f"Imported {len(rows)} records into administration.gift_inventories")
    finally:
        await conn.close()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python import_gift_inventory_template.py <path_to_excel>")
        sys.exit(1)

    excel_path = Path(sys.argv[1])
    if not excel_path.exists():
        print(f"File not found: {excel_path}")
        sys.exit(1)

    await import_from_excel(excel_path)


if __name__ == "__main__":
    asyncio.run(main())
