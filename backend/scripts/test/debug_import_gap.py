import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

import pandas as pd
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings
from app.modules.equipment.models import Equipment
from sqlalchemy import select

async def debug_import():
    # 请确认你的 Excel 文件路径，这里假设在 fixtures 下
    excel_path = 'backend/tests/fixtures/equipment_import_sample.xlsx'
    if not os.path.exists(excel_path):
        print(f"Error: File {excel_path} not found.")
        return

    df = pd.read_excel(excel_path)
    print(f"Excel total rows: {len(df)}")
    
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    skipped_details = []
    
    async with async_session() as db:
        for index, row in df.iterrows():
            # 模拟 batch_import.py 中的清洗逻辑
            asset_no = str(row.get('资产编号', '')).strip() if pd.notna(row.get('资产编号')) else ""
            asset_name = str(row.get('资产说明', '')).strip() if pd.notna(row.get('资产说明')) else ""
            
            reason = None
            
            # 1. 检查关键字段缺失
            if not asset_no or not asset_name:
                reason = "Missing required fields (asset_no or name)"
            
            # 2. 检查重复 (如果字段不缺的话)
            if not reason and asset_no:
                stmt = select(Equipment).where(Equipment.asset_no == asset_no)
                result = await db.execute(stmt)
                if result.scalars().first():
                    reason = f"Duplicate asset_no: {asset_no}"
            
            if reason:
                # Excel 行号通常是 index + 2 (因为第一行是表头)
                skipped_details.append(f"Row {index + 2}: {reason}")

    print(f"\n=== Debug Result ===")
    print(f"Total skipped: {len(skipped_details)}")
    for msg in skipped_details:
        print(msg)

if __name__ == "__main__":
    asyncio.run(debug_import())
