import asyncio
import pandas as pd
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from app.core.config import settings
from app.modules.equipment.repository import get_equipment_by_asset_no


async def debug_import():
    # 假设你的 Excel 文件在 fixtures 下
    df = pd.read_excel("backend/tests/fixtures/equipment_import_sample.xlsx")

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    skipped_rows = []

    async with async_session() as db:
        for index, row in df.iterrows():
            asset_no = str(row.get("资产编号", "")).strip()

            # 检查是否重复
            existing = await get_equipment_by_asset_no(db, asset_no)
            if existing:
                skipped_rows.append(f"Row {index + 2}: Skipped (Duplicate asset_no: {asset_no})")
                continue

            # 检查关键字段
            if not asset_no or not row.get("资产说明"):
                skipped_rows.append(f"Row {index + 2}: Skipped (Missing required fields)")

    print("\n=== Debug Result ===")
    print(f"Total rows: {len(df)}")
    print(f"Skipped rows: {len(skipped_rows)}")
    for msg in skipped_rows:
        print(msg)


if __name__ == "__main__":
    asyncio.run(debug_import())
