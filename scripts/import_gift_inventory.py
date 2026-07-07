"""Import gift inventory from Excel into PostgreSQL."""

import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path

import asyncpg
import pandas as pd


DB_URL = "postgresql://postgres:postgres@localhost:5432/dazah"
EXCEL_PATH = Path(r"C:\Users\Administrator\Desktop\202603-04礼品酒水.xlsx")
SHEET_NAME = "2026-04库存"


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


async def import_data():
    df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME, header=1)

    # Clean data: drop rows with empty name
    df = df[df["物品名称"].notna() & (df["物品名称"] != "")]

    now = datetime.now(timezone.utc)
    rows = []
    for _, row in df.iterrows():
        name = str(row["物品名称"]).strip()
        if not name:
            continue

        opening = parse_value(row.get("月初库存"), int, 0)
        incoming = parse_value(row.get("3-4领用"), int, None)
        closing = parse_value(row.get("月底库存"), int, 0)
        unit_price = parse_value(row.get("单价"), float, None)
        total = parse_value(row.get("Unnamed: 9"), float, None)

        # Infer status from stock
        status = "可用"
        if closing == 0:
            status = "停用"
        elif closing < 5:
            status = "库存不足"

        remark = row.get("备注")
        if remark is not None and str(remark).strip():
            remark = str(remark).strip()
        else:
            remark = None

        spec = row.get("规格")
        if spec is not None and str(spec).strip():
            spec = str(spec).strip()
        else:
            spec = None

        unit = row.get("计量单位")
        if unit is not None and str(unit).strip():
            unit = str(unit).strip()
        else:
            unit = None

        rows.append(
            (
                uuid.uuid4(),
                name,
                spec,
                unit,
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
        # Clear existing data first
        await conn.execute("DELETE FROM administration.gift_inventories")

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


if __name__ == "__main__":
    asyncio.run(import_data())
