"""完全重新导入设备数据：从 Excel 创建所有记录。"""

import asyncio
import sys
import os
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pandas as pd
from sqlalchemy import select
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
            # Step 1: 加载所有部门和位置到内存
            print("\n📊 步骤 1: 加载部门和位置...")

            dept_result = await db.execute(select(HrDepartment.id, HrDepartment.name))
            dept_map = {row[1]: row[0] for row in dept_result.fetchall()}
            valid_depts = set(dept_map.keys())
            print(f"   部门: {len(dept_map)} 个")

            loc_result = await db.execute(select(Location.id, Location.name))
            loc_map = {row[1]: row[0] for row in loc_result.fetchall()}
            print(f"   位置: {len(loc_map)} 个")

            # Step 2: 处理每一行 Excel 数据
            print("\n📊 步骤 2: 导入设备数据...")

            inserted_count = 0
            skipped_count = 0
            error_count = 0
            missing_dept = 0
            missing_loc = 0

            # 批量插入以提高性能
            batch_size = 100
            batch = []

            for idx, row in df.iterrows():
                try:
                    asset_no = str(row.get("资产编号", "")).strip()
                    name = str(row.get("设备名称", "")).strip()
                    raw_dept = row.get("实物所在部门")
                    location_text = str(row.get("实物所在地点", "")).strip()

                    if not asset_no or not name:
                        skipped_count += 1
                        continue

                    # 获取标准部门名称
                    standard_dept = get_standard_dept(raw_dept, valid_depts)

                    if not standard_dept:
                        missing_dept += 1
                        if missing_dept <= 5:
                            print(f"   ⚠️  行 {idx + 1}: 无法映射部门 '{raw_dept}'")
                        skipped_count += 1
                        continue

                    dept_id = dept_map.get(standard_dept)
                    if not dept_id:
                        missing_dept += 1
                        skipped_count += 1
                        continue

                    # 获取位置 ID
                    loc_id = None
                    if location_text and location_text != "-":
                        loc_id = loc_map.get(location_text)
                        if not loc_id:
                            missing_loc += 1
                            if missing_loc <= 5:
                                print(f"   ⚠️  行 {idx + 1}: 位置 '{location_text}' 不存在，将设为 NULL")

                    # 创建设备记录
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
                    batch.append(new_equip)

                    # 批量提交
                    if len(batch) >= batch_size:
                        db.add_all(batch)
                        await db.commit()
                        inserted_count += len(batch)
                        batch = []

                except Exception as e:
                    error_count += 1
                    if error_count <= 5:
                        print(f"   ❌ 行 {idx + 1} 错误: {e}")
                    await db.rollback()

            # 提交剩余的批次
            if batch:
                db.add_all(batch)
                await db.commit()
                inserted_count += len(batch)

            print("\n✅ 导入完成:")
            print(f"   成功导入: {inserted_count} 台")
            print(f"   跳过: {skipped_count} 条")
            print(f"   错误: {error_count} 条")
            print(f"   缺失部门: {missing_dept} 条")
            print(f"   缺失位置: {missing_loc} 条")

            # Step 3: 验证结果
            print("\n📊 步骤 3: 验证结果...")
            from sqlalchemy import func

            total = await db.execute(select(func.count()).where(not Equipment.is_deleted))
            total_count = total.scalar()
            print(f"   数据库活跃设备数: {total_count}")

            if total_count == len(df):
                print(f"   ✅ 完美！所有 {len(df)} 台设备都已导入")
            else:
                print(f"   ⚠️  期望 {len(df)} 台，实际 {total_count} 台")

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
