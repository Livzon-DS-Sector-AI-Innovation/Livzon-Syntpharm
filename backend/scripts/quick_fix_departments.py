"""快速补全部门 ID 的脚本。"""
import asyncio
import sys
sys.path.insert(0, '/home/zhuangweizi/Livzon-Syntpharm/backend')

import xlrd
from app.core.database import async_session_factory
from app.modules.equipment.api.batch_import import map_department_name_v3
from sqlalchemy import select
from app.modules.equipment.models.equipment import Equipment

async def run():
    excel_path = '/home/zhuangweizi/.codex/202606sbgz.xls'
    wb = xlrd.open_workbook(excel_path)
    ws = wb.sheet_by_index(0)
    headers = ws.row_values(4)
    
    updated = 0
    
    async with async_session_factory() as db:
        for r in range(5, ws.nrows):
            asset_no = str(ws.cell_value(r, headers.index("资产编号"))).strip()
            dept_raw = ws.cell_value(r, headers.index("实物所在部门"))
            
            if not asset_no: continue
            
            # 1. 找到数据库里的设备
            result = await db.execute(select(Equipment).where(Equipment.asset_no == asset_no))
            eq = result.scalar_one_or_none()
            
            if eq and dept_raw:
                # 2. 映射部门
                dept_name, dept_id = await map_department_name_v3(dept_raw, db)
                
                # 3. 如果数据库里没部门，就填进去
                if dept_id and not eq.department_id:
                    eq.department_id = dept_id
                    updated += 1
                    
            if (r + 1) % 500 == 0: 
                await db.commit()
                print(f"已处理 {r+1} 条...")

        await db.commit()
        
    print(f"\n🎉 部门补全完成！共更新: {updated} 条")

if __name__ == "__main__":
    asyncio.run(run())
