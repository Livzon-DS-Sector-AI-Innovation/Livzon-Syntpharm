"""智能导入设备：支持恢复已删除的设备。"""

import asyncio
import sys
import os
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pandas as pd
from sqlalchemy import select, update, func
from app.core.database import async_session_factory
from app.modules.equipment.models.equipment import Equipment, Location
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
    """将原始部门名称转换为标准部门名称。"""
    if not raw_dept or pd.isna(raw_dept):
        return None

    raw_dept = str(raw_dept).strip()

    if raw_dept in DEPT_MAPPING:
        return DEPT_MAPPING[raw_dept]

    if raw_dept in valid_depts:
        return raw_dept

    return None


async def main():
    excel_path = "/tmp/202606sbgz.xls"
    print(f"📊 读取 Excel 文件: {excel_path}")
    df = pd.read_excel(excel_path, header=4)
    print(f"   总行数: {len(df)}")

    async with async_session_factory() as db:
        try:
            # Step 1: 加载部门和位置
            print("\n📊 步骤 1: 加载部门和位置...")
            dept_result = await db.execute(select(HrDepartment.id, HrDepartment.name))
            dept_map = {row[1]: row[0] for row in dept_result.fetchall()}
            valid_depts = set(dept_map.keys())

            loc_result = await db.execute(select(Location.id, Location.name))
            loc_map = {row[1]: row[0] for row in loc_result.fetchall()}
            print(f"   部门: {len(dept_map)} 个, 位置: {len(loc_map)} 个")

            # Step 2: 获取所有设备（包括已删除的）
            print("\n📊 步骤 2: 加载所有设备...")
            existing_result = await db.execute(
                select(
                    Equipment.id,
                    Equipment.asset_no,
                    Equipment.department_id,
                    Equipment.location_id,
                    Equipment.is_deleted,
                )
            )

            # 建立两个索引：
            # 1. 活跃设备索引（用于快速查找）
            active_equipments = {}
            # 2. 所有设备索引（包括已删除，用于恢复）
            all_equipments_by_key = {}

            for equip_id, asset_no, dept_id, loc_id, is_deleted in existing_result.fetchall():
                key = (str(asset_no).strip(), dept_id, loc_id)
                all_equipments_by_key[key] = (equip_id, is_deleted)

                if not is_deleted:
                    active_equipments[key] = equip_id

            print(f"   总设备: {len(all_equipments_by_key)} 条")
            print(f"   活跃设备: {len(active_equipments)} 条")

            # Step 3: 处理 Excel 数据
            print("\n📊 步骤 3: 处理 Excel 数据...")
            inserted_count = 0
            restored_count = 0
            skipped_count = 0
            error_count = 0

            for idx, row in df.iterrows():
                try:
                    asset_no = str(row.get("资产编号", "")).strip()
                    name = str(row.get("设备名称", "")).strip()
                    raw_dept = row.get("实物所在部门")
                    location_text = str(row.get("实物所在地点", "")).strip()

                    if not asset_no or not name:
                        skipped_count += 1
                        continue

                    # 获取标准部门
                    standard_dept = get_standard_dept(raw_dept, valid_depts)
                    dept_id = dept_map.get(standard_dept) if standard_dept else None

                    # 获取位置 ID
                    loc_id = loc_map.get(location_text) if location_text and location_text != "-" else None

                    # 检查是否已存在
                    key = (asset_no, dept_id, loc_id)

                    if key in all_equipments_by_key:
                        equip_id, is_deleted = all_equipments_by_key[key]

                        if is_deleted:
                            # 设备已删除，恢复它
                            stmt = (
                                update(Equipment)
                                .where(Equipment.id == equip_id)
                                .values(
                                    is_deleted=False,
                                    name=name,
                                    location_text=location_text if location_text else None,
                                )
                            )
                            await db.execute(stmt)
                            restored_count += 1
                        else:
                            # 设备已存在且活跃，跳过
                            skipped_count += 1
                    else:
                        # 不存在，插入新记录
                        new_equip = Equipment(
                            id=uuid.uuid4(),
                            asset_no=asset_no,
                            name=name,
                            department_id=dept_id,
                            location_id=loc_id,
                            location_text=location_text if location_text else None,
                            status="在用",
                            equipment_class="C",
                            importance="低",
                            is_deleted=False,
                        )
                        db.add(new_equip)
                        inserted_count += 1

                        # 添加到索引
                        all_equipments_by_key[key] = (new_equip.id, False)

                except Exception as e:
                    error_count += 1
                    if error_count <= 5:
                        print(f"   ❌ 行 {idx + 1} 错误: {e}")

            await db.commit()

            print("\n✅ 导入完成:")
            print(f"   新增设备: {inserted_count} 台")
            print(f"   恢复已删除设备: {restored_count} 台")
            print(f"   已存在跳过: {skipped_count} 台")
            print(f"   错误: {error_count} 条")

            # Step 4: 验证结果
            print("\n📊 步骤 4: 验证结果...")
            total = await db.execute(select(func.count()).where(not Equipment.is_deleted))
            total_count = total.scalar()
            print(f"   数据库活跃设备数: {total_count}")

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
