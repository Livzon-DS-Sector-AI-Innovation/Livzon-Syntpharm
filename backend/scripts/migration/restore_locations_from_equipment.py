"""从设备记录的 location_text 恢复位置数据。

此脚本会：
1. 提取所有唯一的 location_text
2. 批量创建位置记录
3. 通过精确匹配更新设备的 location_id
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlalchemy import select, update
from app.core.database import async_session_factory
from app.modules.equipment.models.equipment import Location, Equipment


async def main():
    async with async_session_factory() as db:
        try:
            # Step 1: 获取所有唯一的 location_text（排除 NULL 和 '-'）
            print("📊 步骤 1: 提取唯一的位置名称...")
            result = await db.execute(
                select(Equipment.location_text)
                .where(Equipment.location_text.isnot(None))
                .where(Equipment.location_text != '-')
                .distinct()
            )
            location_texts = [row[0] for row in result.fetchall()]
            print(f"   找到 {len(location_texts)} 个唯一位置名称")
            
            if not location_texts:
                print("❌ 没有找到位置数据，退出")
                return
            
            # Step 2: 检查哪些位置已存在
            print("\n📊 步骤 2: 检查现有位置...")
            existing_result = await db.execute(select(Location.code, Location.name))
            existing_locations = {row[1]: row[0] for row in existing_result.fetchall()}  # name -> code
            print(f"   数据库中已有 {len(existing_locations)} 个位置")
            
            # Step 3: 创建缺失的位置记录
            print("\n📊 步骤 3: 创建缺失的位置记录...")
            new_locations = []
            for idx, loc_name in enumerate(location_texts, start=1):
                if loc_name not in existing_locations:
                    # 生成代码：使用简单编码
                    code = f"LOC-{idx:04d}"
                    new_loc = Location(
                        name=loc_name,
                        code=code,
                        description=f"从设备数据自动恢复",
                    )
                    new_locations.append(new_loc)
            
            if new_locations:
                db.add_all(new_locations)
                await db.commit()
                print(f"   ✅ 创建了 {len(new_locations)} 个新位置")
                
                # 重新加载以获取 ID
                for loc in new_locations:
                    await db.refresh(loc)
            else:
                print("   ℹ️  所有位置已存在，无需创建")
            
            # Step 4: 建立名称到 ID 的映射
            print("\n📊 步骤 4: 建立名称到 ID 的映射...")
            all_locations_result = await db.execute(select(Location.id, Location.name))
            name_to_id = {row[1]: row[0] for row in all_locations_result.fetchall()}
            print(f"   映射表包含 {len(name_to_id)} 个位置")
            
            # Step 5: 更新设备的 location_id
            print("\n📊 步骤 5: 更新设备的 location_id...")
            updated_count = 0
            for loc_name, loc_id in name_to_id.items():
                stmt = (
                    update(Equipment)
                    .where(Equipment.location_text == loc_name)
                    .where(Equipment.location_id.is_(None))
                    .values(location_id=loc_id)
                )
                result = await db.execute(stmt)
                count = result.rowcount
                if count > 0:
                    updated_count += count
                    print(f"   ✓ {loc_name}: 更新了 {count} 台设备")
            
            await db.commit()
            print(f"\n✅ 完成！共更新了 {updated_count} 台设备的 location_id")
            
            # Step 6: 验证结果
            print("\n📊 步骤 6: 验证结果...")
            with_location = await db.execute(
                select(Equipment).where(Equipment.location_id.isnot(None))
            )
            with_location_count = len(with_location.scalars().all())
            
            without_location = await db.execute(
                select(Equipment).where(Equipment.location_id.is_(None))
            )
            without_location_count = len(without_location.scalars().all())
            
            print(f"   有 location_id 的设备: {with_location_count}")
            print(f"   无 location_id 的设备: {without_location_count}")
            
            if without_location_count > 0:
                print(f"\n⚠️  仍有 {without_location_count} 台设备未匹配到位置")
                print("   这些设备的 location_text 可能是:")
                unmatched = await db.execute(
                    select(Equipment.location_text)
                    .where(Equipment.location_id.is_(None))
                    .where(Equipment.location_text.isnot(None))
                    .where(Equipment.location_text != '-')
                    .distinct()
                    .limit(10)
                )
                for row in unmatched.fetchall():
                    print(f"     - {row[0]}")
        
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
