"""根据设备位置文本自动分配部门。"""

import asyncio
import sys
import os
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlalchemy import select, update
from app.core.database import async_session_factory
from app.modules.equipment.models.equipment import Equipment, Location
from app.modules.hr.models import HrDepartment


# 位置关键词到部门的映射规则
LOCATION_TO_DEPT_RULES = [
    # 车间类
    (r'101车间', '101车间'),
    (r'102车间', '102车间'),
    (r'103车间', '103车间'),
    (r'105车间', '105车间'),
    (r'106车间', '106车间'),
    (r'107车间', '107车间'),
    (r'201车间', '201车间'),
    (r'202车间', '202车间'),
    (r'301车间', '301车间'),
    (r'302车间', '302车间'),
    (r'303车间', '303车间'),
    (r'非头孢', '非头孢制造部'),
    (r'头孢合成', '头孢无菌制造部'),
    (r'头孢精制', '头孢无菌制造部'),
    (r'溶剂回收', '溶剂回收车间'),
    
    # 职能部门
    (r'动力', '动力部'),
    (r'制水', '动力部'),
    (r'锅炉', '动力部'),
    (r'制冷', '动力部'),
    
    (r'设备工程', '设备工程部'),
    (r'机修', '设备工程部'),
    (r'仪表', '设备工程部'),
    (r'电工', '设备工程部'),
    
    (r'质检\|QC\|化验\|检验', '质量控制部'),
    (r'QA\|质保', '质量保证部'),
    
    (r'安全\|环保\|安环', '安全环保部'),
    
    (r'研发\|实验\|研究', '技术研发部'),
    
    (r'财务', '财务部'),
    
    (r'采购', '采购部'),
    
    (r'注册', '注册部'),
    
    (r'仓库\|仓储\|库', '仓储部'),
    
    (r'人事\|行政\|人力\|HR\|食堂\|炊事', '人事行政部'),
    
    (r'生产', '生产部'),
    
    (r'销售', '头孢销售部'),
]


def match_department(location_text: str) -> str | None:
    """根据位置文本匹配部门名称。"""
    if not location_text or location_text == '-':
        return None
    
    for pattern, dept_name in LOCATION_TO_DEPT_RULES:
        if re.search(pattern, location_text):
            return dept_name
    
    return None


async def main():
    async with async_session_factory() as db:
        try:
            # Step 1: 加载所有部门
            print("📊 步骤 1: 加载部门列表...")
            dept_result = await db.execute(select(HrDepartment.id, HrDepartment.name))
            dept_map = {row[1]: row[0] for row in dept_result.fetchall()}
            print(f"   找到 {len(dept_map)} 个部门")
            
            # Step 2: 获取所有未分配部门的设备
            print("\n📊 步骤 2: 查找未分配部门的设备...")
            equipment_result = await db.execute(
                select(Equipment.id, Equipment.location_text)
                .where(Equipment.department_id.is_(None))
                .where(Equipment.location_text.isnot(None))
                .where(Equipment.location_text != '-')
            )
            equipments = equipment_result.fetchall()
            print(f"   找到 {len(equipments)} 台未分配部门的设备")
            
            if not equipments:
                print("✅ 所有设备都已分配部门")
                return
            
            # Step 3: 匹配并更新
            print("\n📊 步骤 3: 匹配部门并更新...")
            updated_count = 0
            unmatched_locations = set()
            
            for equip_id, location_text in equipments:
                dept_name = match_department(location_text)
                
                if dept_name and dept_name in dept_map:
                    dept_id = dept_map[dept_name]
                    stmt = (
                        update(Equipment)
                        .where(Equipment.id == equip_id)
                        .values(department_id=dept_id)
                    )
                    await db.execute(stmt)
                    updated_count += 1
                else:
                    unmatched_locations.add(location_text)
            
            await db.commit()
            print(f"\n✅ 成功更新 {updated_count} 台设备的部门")
            
            if unmatched_locations:
                print(f"\n⚠️  有 {len(unmatched_locations)} 个位置无法匹配部门:")
                for loc in sorted(list(unmatched_locations)[:20]):
                    print(f"   - {loc}")
            
            # Step 4: 验证结果
            print("\n📊 步骤 4: 验证结果...")
            with_dept = await db.execute(
                select(Equipment).where(Equipment.department_id.isnot(None))
            )
            with_dept_count = len(with_dept.scalars().all())
            
            without_dept = await db.execute(
                select(Equipment).where(Equipment.department_id.is_(None))
            )
            without_dept_count = len(without_dept.scalars().all())
            
            print(f"   有部门的设备: {with_dept_count}")
            print(f"   无部门的设备: {without_dept_count}")
        
        except Exception as e:
            await db.rollback()
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            await db.close()


if __name__ == "__main__":
    asyncio.run(main())
