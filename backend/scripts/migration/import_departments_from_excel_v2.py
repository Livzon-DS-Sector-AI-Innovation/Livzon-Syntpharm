"""从 Excel 文件导入部门数据并更新设备关联（改进版）。"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pandas as pd
from sqlalchemy import select, update, func
from app.core.database import async_session_factory
from app.modules.equipment.models.equipment import Equipment
from app.modules.hr.models import HrDepartment


# Excel 中的原始部门名称到标准部门名称的映射
DEPT_MAPPING = {
    # 车间映射
    "头孢合成一车间": "201车间",
    "头孢合成二车间": "202车间",
    "头孢精制一车间": "301车间",
    "头孢精制二车间": "302车间",
    "头孢精制三车间": "303车间",
    "非头孢一车间": "101车间",
    "非头孢二车间": "102车间",
    "非头孢三车间": "103车间",
    "非头孢五车间": "105车间",
    "非头孢六车间": "106车间",
    "非头孢七车间": "107车间",
    
    # 职能部门映射
    "环保中心": "安全环保部",
    "安全中心": "安全环保部",
    "检验室": "质量控制部",
    "质量部": "质量保证部",
    "仪表电工班": "设备工程部",
    "机修班": "动力部",
    "制冷班": "动力部",
    "锅炉制水班": "动力部",
    "工程部": "设备工程部",
    "实验室": "技术研发部",
    "仓库": "生产部",
    "炊事班": "人事行政部",
    "头孢精制制造部": "头孢无菌制造部",
    "头孢合成制造部": "头孢无菌制造部",
    "生产管理部": "生产部",
}

# 溶剂回收车间各岗位统一映射为"溶剂回收车间"
SOLVENT_WORKSHOPS = [
    "溶剂回收车间-401岗",
    "溶剂回收车间-402岗",
    "溶剂回收车间-403岗",
    "溶剂回收车间-404岗",
    "溶剂回收车间-405岗",
]
for workshop in SOLVENT_WORKSHOPS:
    DEPT_MAPPING[workshop] = "溶剂回收车间"


def get_standard_dept(raw_dept: str, valid_depts: set) -> str | None:
    """将原始部门名称转换为标准部门名称。
    
    策略：
    1. 如果有映射规则，使用映射
    2. 如果本身就是有效部门名称，直接使用
    3. 否则返回 None
    """
    if not raw_dept or pd.isna(raw_dept):
        return None
    
    raw_dept = str(raw_dept).strip()
    
    # 先检查是否有映射规则
    if raw_dept in DEPT_MAPPING:
        return DEPT_MAPPING[raw_dept]
    
    # 再检查是否本身就是有效部门
    if raw_dept in valid_depts:
        return raw_dept
    
    return None


async def main():
    # 读取 Excel 文件
    excel_path = "/tmp/202606sbgz.xls"
    print(f"📊 读取 Excel 文件: {excel_path}")
    df = pd.read_excel(excel_path, header=4)
    print(f"   总行数: {len(df)}")
    
    async with async_session_factory() as db:
        try:
            # Step 1: 加载所有部门
            print("\n📊 步骤 1: 加载部门列表...")
            dept_result = await db.execute(select(HrDepartment.id, HrDepartment.name))
            dept_map = {row[1]: row[0] for row in dept_result.fetchall()}
            valid_depts = set(dept_map.keys())
            print(f"   找到 {len(dept_map)} 个部门: {sorted(valid_depts)}")
            
            # Step 2: 建立资产编号到标准部门的映射
            print("\n📊 步骤 2: 建立资产编号到部门的映射...")
            asset_to_dept = {}
            mapped_count = 0
            unmapped_depts = set()
            
            for _, row in df.iterrows():
                asset_no = row.get('资产编号')
                raw_dept = row.get('实物所在部门')
                
                if pd.notna(asset_no) and pd.notna(raw_dept):
                    standard_dept = get_standard_dept(raw_dept, valid_depts)
                    if standard_dept:
                        asset_to_dept[str(asset_no).strip()] = standard_dept
                        mapped_count += 1
                    else:
                        unmapped_depts.add(str(raw_dept).strip())
            
            print(f"   成功映射: {mapped_count} 条")
            if unmapped_depts:
                print(f"   无法映射的部门 ({len(unmapped_depts)} 个): {sorted(unmapped_depts)}")
            
            # Step 3: 获取所有设备
            print("\n📊 步骤 3: 更新设备部门关联...")
            equipment_result = await db.execute(
                select(Equipment.id, Equipment.asset_no)
            )
            equipments = equipment_result.fetchall()
            print(f"   找到 {len(equipments)} 台设备")
            
            # Step 4: 更新部门
            updated_count = 0
            not_found_in_excel = 0
            
            for equip_id, asset_no in equipments:
                if asset_no:
                    asset_str = str(asset_no).strip()
                    if asset_str in asset_to_dept:
                        dept_name = asset_to_dept[asset_str]
                        if dept_name in dept_map:
                            dept_id = dept_map[dept_name]
                            stmt = (
                                update(Equipment)
                                .where(Equipment.id == equip_id)
                                .values(department_id=dept_id)
                            )
                            await db.execute(stmt)
                            updated_count += 1
                    else:
                        not_found_in_excel += 1
            
            await db.commit()
            print(f"\n✅ 成功更新 {updated_count} 台设备的部门")
            print(f"   Excel 中找不到的设备: {not_found_in_excel} 台")
            
            # Step 5: 验证结果
            print("\n📊 步骤 5: 验证结果...")
            with_dept = await db.execute(
                select(func.count()).where(Equipment.department_id.isnot(None))
            )
            with_dept_count = with_dept.scalar()
            
            without_dept = await db.execute(
                select(func.count()).where(Equipment.department_id.is_(None))
            )
            without_dept_count = without_dept.scalar()
            
            print(f"   有部门的设备: {with_dept_count}")
            print(f"   无部门的设备: {without_dept_count}")
            
            # 按部门统计
            print("\n📊 部门分布统计:")
            for dept_name in sorted(dept_map.keys()):
                dept_id = dept_map[dept_name]
                count_result = await db.execute(
                    select(func.count()).where(Equipment.department_id == dept_id)
                )
                count = count_result.scalar()
                if count > 0:
                    print(f"   {dept_name}: {count} 台")
        
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
