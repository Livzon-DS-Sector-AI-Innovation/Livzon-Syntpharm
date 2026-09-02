"""智能同步设备数据：支持全字段更新、位置迁移和软删除。"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pandas as pd
from sqlalchemy import select, update
from app.core.database import async_session_factory
from app.modules.equipment.models.equipment import Equipment, Location
from app.modules.hr.models import HrDepartment

# 部门映射表
DEPT_MAPPING = {
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
for i in range(401, 406):
    DEPT_MAPPING[f"溶剂回收车间-{i}岗"] = "溶剂回收车间"


def get_standard_dept(raw_dept, valid_depts):
    if not raw_dept or pd.isna(raw_dept):
        return None
    raw = str(raw_dept).strip()
    if raw in DEPT_MAPPING:
        return DEPT_MAPPING[raw]
    return raw if raw in valid_depts else None


async def main():
    excel_path = "/tmp/202606sbgz.xls"
    print(f"📊 开始智能同步: {excel_path}")
    df = pd.read_excel(excel_path, header=4)

    async with async_session_factory() as db:
        try:
            # 1. 加载基础数据
            dept_result = await db.execute(select(HrDepartment.id, HrDepartment.name))
            dept_map = {n: i for i, n in dept_result.fetchall()}
            valid_depts = set(dept_map.keys())

            loc_result = await db.execute(select(Location.id, Location.name))
            loc_map = {n: i for i, n in loc_result.fetchall()}

            # 2. 加载数据库现有活跃设备
            equip_result = await db.execute(select(Equipment))
            db_equips = {e.asset_no: e for e in equip_result.scalars().all()}

            updated, inserted, migrated, _skipped = 0, 0, 0, 0
            excel_assets = set()

            for _, row in df.iterrows():
                asset_no = str(row["资产编号"]).strip()
                if not asset_no:
                    continue
                excel_assets.add(asset_no)

                std_dept = get_standard_dept(row["实物所在部门"], valid_depts)
                dept_id = dept_map.get(std_dept) if std_dept else None

                loc_text = (
                    str(row["实物所在地点"]).strip()
                    if pd.notna(row["实物所在地点"]) and str(row["实物所在地点"]).strip() != "-"
                    else None
                )
                loc_id = loc_map.get(loc_text) if loc_text else None

                # 核心逻辑：查找匹配
                target_equip = None
                if asset_no in db_equips:
                    e = db_equips[asset_no]
                    # 情况 A: 完全匹配 (同资产、同部门、同位置)
                    if e.department_id == dept_id and e.location_id == loc_id:
                        target_equip = e
                    # 情况 B: 资产迁移 (同资产、不同位置) -> 更新旧记录
                    elif not e.is_deleted:
                        target_equip = e
                        migrated += 1

                if target_equip:
                    # 执行全字段更新
                    stmt = (
                        update(Equipment)
                        .where(Equipment.id == target_equip.id)
                        .values(
                            name=str(row["设备名称"]).strip(),
                            department_id=dept_id,
                            location_id=loc_id,
                            location_text=loc_text,
                            current_cost=float(row["当前成本"]) if pd.notna(row["当前成本"]) else None,
                            book_value=float(row["帐面净值"]) if pd.notna(row["帐面净值"]) else None,
                            status="在用",
                            is_deleted=False,
                            model=str(row["型号"]).strip() if pd.notna(row["型号"]) else None,
                            manufacturer=str(row["制造商"]).strip() if pd.notna(row["制造商"]) else None,
                            commissioning_date=row["启用日期"] if pd.notna(row["启用日期"]) else None,
                        )
                    )
                    await db.execute(stmt)
                    updated += 1
                else:
                    # 情况 C: 新增
                    new_e = Equipment(
                        asset_no=asset_no,
                        name=str(row["设备名称"]).strip(),
                        department_id=dept_id,
                        location_id=loc_id,
                        location_text=loc_text,
                        current_cost=float(row["当前成本"]) if pd.notna(row["当前成本"]) else None,
                        book_value=float(row["帐面净值"]) if pd.notna(row["帐面净值"]) else None,
                        status="在用",
                        is_deleted=False,
                    )
                    db.add(new_e)
                    inserted += 1

            # 3. 处理软删除 (Excel 里没有的活跃设备)
            deleted_count = 0
            for asset_no, e in db_equips.items():
                if asset_no not in excel_assets and not e.is_deleted:
                    await db.execute(update(Equipment).where(Equipment.id == e.id).values(is_deleted=True))
                    deleted_count += 1

            await db.commit()
            print(f"✅ 同步完成: 更新 {updated} | 迁移 {migrated} | 新增 {inserted} | 停用 {deleted_count}")

        except Exception as e:
            await db.rollback()
            print(f"❌ 错误: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
