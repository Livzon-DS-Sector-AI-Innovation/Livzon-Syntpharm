"""从 departments.json 种子数据导入部门。"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlalchemy import select
from app.core.database import async_session_factory
from app.platform.identity.models import Department


async def main():
    # 读取种子数据
    seed_file = os.path.join(os.path.dirname(__file__), "..", "seed", "departments.json")
    with open(seed_file, encoding="utf-8") as f:
        departments_data = json.load(f)

    print(f"📊 读取到 {len(departments_data)} 个部门种子数据")

    async with async_session_factory() as db:
        try:
            # 检查现有部门
            existing_result = await db.execute(select(Department.code))
            existing_codes = {row[0] for row in existing_result.fetchall()}
            print(f"   数据库中已有 {len(existing_codes)} 个部门")

            # 创建缺失的部门
            new_departments = []
            for dept_data in departments_data:
                if dept_data["code"] not in existing_codes:
                    dept = Department(
                        id=dept_data["id"],
                        name=dept_data["name"],
                        code=dept_data["code"],
                        description=dept_data.get("description"),
                    )
                    new_departments.append(dept)

            if new_departments:
                db.add_all(new_departments)
                await db.commit()
                print(f"\n✅ 成功导入 {len(new_departments)} 个部门")

                for dept in new_departments:
                    print(f"   - {dept.name} ({dept.code})")
            else:
                print("\nℹ️  所有部门已存在，无需导入")

            # 验证结果
            total = await db.execute(select(Department))
            total_count = len(total.scalars().all())
            print(f"\n📊 数据库中共有 {total_count} 个部门")

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
