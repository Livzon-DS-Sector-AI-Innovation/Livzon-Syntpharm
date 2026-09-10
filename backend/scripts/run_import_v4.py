"""执行 v4 导入逻辑的独立脚本。"""
import asyncio
import sys
import os
sys.path.insert(0, '/home/zhuangweizi/Livzon-Syntpharm/backend')

import xlrd
from app.core.database import async_session_factory
from app.modules.equipment.service.import_engine import find_existing_equipment
from app.modules.equipment import repository as repo
from app.modules.equipment.api.batch_import import map_department_name_v3

async def run():
    excel_path = '/home/zhuangweizi/.codex/202606sbgz.xls'
    if not os.path.exists(excel_path):
        print("❌ Excel 文件不存在")
        return

    wb = xlrd.open_workbook(excel_path)
    ws = wb.sheet_by_index(0)
    headers = ws.row_values(4)

    created = updated = skipped = 0

    async with async_session_factory() as db:
        for r in range(5, ws.nrows):
            row = {str(headers[i]): ws.cell_value(r, i) for i in range(len(headers))}

            asset_no = str(row.get("资产编号", "")).strip() or None
            name = str(row.get("资产说明", "")).strip()
            dept_raw = row.get("实物所在部门")
            location_text = str(row.get("实物所在地点", "")).strip() or None

            if not name: continue

            # 映射部门
            dept_name, dept_id = await map_department_name_v3(dept_raw, db) if dept_raw else (None, None)

            # 解析成本
            try: current_cost = float(str(row.get("当前成本", "0")).replace("¥","").replace(",",""))
            except: current_cost = None

            try: book_value = float(str(row.get("帐面净值", "0")).replace("¥","").replace(",",""))
            except: book_value = None

            # 查找
            existing, strategy = await find_existing_equipment(db, asset_no, None, name, dept_id, location_text)

            if existing:
                # 强制更新逻辑
                changed = False
                if existing.current_cost != current_cost:
                    existing.current_cost = current_cost; changed = True
                if existing.book_value != book_value:
                    existing.book_value = book_value; changed = True
                if dept_id and existing.department_id != dept_id:
                    existing.department_id = dept_id; changed = True

                if changed: updated += 1
                else: skipped += 1
            else:
                # 创建新记录
                await repo.create_equipment(db, {
                    "asset_no": asset_no, "name": name, "department_id": dept_id,
                    "location_text": location_text, "current_cost": current_cost,
                    "book_value": book_value, "is_fixed_asset": bool(asset_no)
                })
                created += 1

            if (r + 1) % 100 == 0:
                await db.commit()
                print(f"已处理 {r+1} 条...")

        await db.commit()

    print(f"\n🎉 导入完成！新增: {created}, 更新: {updated}, 跳过: {skipped}")

if __name__ == "__main__":
    asyncio.run(run())
