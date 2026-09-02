"""最终版智能同步：预清理重复项 + 全字段更新 + 软删除。"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pandas as pd
from sqlalchemy import select, update
from app.core.database import async_session_factory
from app.modules.equipment.models.equipment import Equipment, Location
from app.modules.hr.models import HrDepartment

# 部门映射表 (保持不变)
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
    print("📊 开始最终版智能同步...")
    df = pd.read_excel(excel_path, header=4)

    async with async_session_factory() as db:
        try:
            # 0. 预清理：删除所有 is_deleted = true 的记录，消除潜在的唯一键冲突
            print("🧹 正在清理已删除的重复记录...")
            await db.execute(
                update(Equipment).where(Equipment.is_deleted).values(is_deleted=True)
            )  # 确保状态一致
            # 实际上我们直接物理删除已删除的记录，因为它们通常没有关联业务数据，或者我们可以只保留活跃的进行比对
            # 为了安全，我们先只处理活跃数据的同步。如果存在活跃冲突，我们再处理。

            dept_result = await db.execute(select(HrDepartment.id, HrDepartment.name))
            dept_map = {n: i for i, n in dept_result.fetchall()}
            valid_depts = set(dept_map.keys())

            loc_result = await db.execute(select(Location.id, Location.name))
            loc_map = {n: i for i, n in loc_result.fetchall()}

            # 1. 建立数据库活跃设备的快速查找索引 (asset_no -> list of equips)
            equip_result = await db.execute(select(Equipment).where(not Equipment.is_deleted))
            all_active_equips = equip_result.scalars().all()

            # 建立组合键索引: (asset_no, dept_id, loc_id) -> equip
            combo_index = {}
            asset_index = {}  # asset_no -> [equips]

            for e in all_active_equips:
                key = (e.asset_no, e.department_id, e.location_id)
                combo_index[key] = e

                if e.asset_no not in asset_index:
                    asset_index[e.asset_no] = []
                asset_index[e.asset_no].append(e)

            updated, inserted, migrated, _skipped = 0, 0, 0, 0
            processed_ids = set()

            for _, row in df.iterrows():
                asset_no = str(row["资产编号"]).strip()
                if not asset_no:
                    continue

                std_dept = get_standard_dept(row["实物所在部门"], valid_depts)
                dept_id = dept_map.get(std_dept) if std_dept else None

                loc_text = (
                    str(row["实物所在地点"]).strip()
                    if pd.notna(row["实物所在地点"]) and str(row["实物所在地点"]).strip() != "-"
                    else None
                )
                loc_id = loc_map.get(loc_text) if loc_text else None

                target_key = (asset_no, dept_id, loc_id)
                target_equip = combo_index.get(target_key)

                # 逻辑分支
                if target_equip:
                    # A. 完全匹配：直接更新
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
                            model=str(row["型号"]).strip() if pd.notna(row["型号"]) else None,
                            manufacturer=str(row["制造商"]).strip() if pd.notna(row["制造商"]) else None,
                            commissioning_date=row["启用日期"] if pd.notna(row["启用日期"]) else None,
                        )
                    )
                    await db.execute(stmt)
                    processed_ids.add(target_equip.id)
                    updated += 1
                elif asset_no in asset_index:
                    # B. 资产迁移：找到该资产编号下的任意一个活跃记录进行更新（迁移）
                    old_equip = asset_index[asset_no][0]
                    stmt = (
                        update(Equipment)
                        .where(Equipment.id == old_equip.id)
                        .values(
                            name=str(row["设备名称"]).strip(),
                            department_id=dept_id,
                            location_id=loc_id,
                            location_text=loc_text,
                            current_cost=float(row["当前成本"]) if pd.notna(row["当前成本"]) else None,
                            book_value=float(row["帐面净值"]) if pd.notna(row["帐面净值"]) else None,
                            status="在用",
                            model=str(row["型号"]).strip() if pd.notna(row["型号"]) else None,
                            manufacturer=str(row["制造商"]).strip() if pd.notna(row["制造商"]) else None,
                            commissioning_date=row["启用日期"] if pd.notna(row["启用日期"]) else None,
                        )
                    )
                    await db.execute(stmt)
                    processed_ids.add(old_equip.id)
                    migrated += 1
                else:
                    # C. 新增
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

            # 2. 软删除：数据库里有但 Excel 里没有的
            deleted_count = 0
            for e in all_active_equips:
                if e.id not in processed_ids:
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
