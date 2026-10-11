"""从设备记录的 category_description 恢复分类数据。

此脚本会：
1. 提取所有唯一的 category_description
2. 批量创建分类记录
3. 建立分类关联表（equipment_category_links）
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlalchemy import select, update
from app.core.database import async_session_factory
from app.modules.equipment.models.equipment import EquipmentCategory, EquipmentCategoryLink, Equipment


def parse_category_hierarchy(description: str) -> tuple[str, str | None]:
    """解析分类描述，提取一级和二级分类。

    例如："固定资产.机器设备" -> ("固定资产", "机器设备")
    """
    if not description or "." not in description:
        return (description or "未分类", None)

    parts = description.split(".", 1)
    return (parts[0].strip(), parts[1].strip() if len(parts) > 1 else None)


async def main():
    async with async_session_factory() as db:
        try:
            # Step 1: 获取所有唯一的 category_description
            print("📊 步骤 1: 提取唯一的分类描述...")
            result = await db.execute(
                select(Equipment.category_description).where(Equipment.category_description.isnot(None)).distinct()
            )
            descriptions = [row[0] for row in result.fetchall()]
            print(f"   找到 {len(descriptions)} 个唯一分类描述")

            if not descriptions:
                print("❌ 没有找到分类数据，退出")
                return

            # Step 2: 解析分类层级
            print("\n📊 步骤 2: 解析分类层级...")
            categories = {}  # name -> {code, parent_name}
            for desc in descriptions:
                level1, level2 = parse_category_hierarchy(desc)

                # 添加一级分类
                if level1 not in categories:
                    categories[level1] = {"name": level1, "parent_id": None}

                # 添加二级分类
                if level2 and level2 not in categories:
                    categories[level2] = {"name": level2, "parent_name": level1}

            print(f"   解析出 {len(categories)} 个分类（含层级）")

            # Step 3: 检查现有分类
            print("\n📊 步骤 3: 检查现有分类...")
            existing_result = await db.execute(select(EquipmentCategory.id, EquipmentCategory.name))
            existing_categories = {row[1]: row[0] for row in existing_result.fetchall()}
            print(f"   数据库中已有 {len(existing_categories)} 个分类")

            # Step 4: 创建缺失的分类记录
            print("\n📊 步骤 4: 创建缺失的分类记录...")
            new_categories = []
            name_to_obj = {}

            for idx, (name, info) in enumerate(categories.items(), start=1):
                if name not in existing_categories:
                    code = f"CAT-{idx:04d}"
                    parent_id = None

                    # 如果有父分类，先查找或创建
                    if "parent_name" in info:
                        parent_name = info["parent_name"]
                        if parent_name in existing_categories:
                            parent_id = existing_categories[parent_name]
                        elif parent_name in name_to_obj:
                            parent_id = name_to_obj[parent_name].id

                    new_cat = EquipmentCategory(
                        name=name,
                        code=code,
                        parent_id=parent_id,
                        description="从设备数据自动恢复",
                    )
                    new_categories.append(new_cat)
                    name_to_obj[name] = new_cat

            if new_categories:
                db.add_all(new_categories)
                await db.commit()
                print(f"   ✅ 创建了 {len(new_categories)} 个新分类")

                # 重新加载以获取 ID
                for cat in new_categories:
                    await db.refresh(cat)
                    name_to_obj[cat.name] = cat
            else:
                print("   ℹ️  所有分类已存在，无需创建")

            # Step 5: 建立完整的名称到 ID 映射
            print("\n📊 步骤 5: 建立名称到 ID 的映射...")
            all_categories_result = await db.execute(select(EquipmentCategory.id, EquipmentCategory.name))
            name_to_id = {row[1]: row[0] for row in all_categories_result.fetchall()}
            print(f"   映射表包含 {len(name_to_id)} 个分类")

            # Step 6: 创建设备分类关联
            print("\n📊 步骤 6: 创建设备分类关联...")

            # 先清空现有的关联（避免重复）
            await db.execute(update(EquipmentCategoryLink).values(is_deleted=True))
            await db.commit()

            # 为每个设备创建分类关联
            linked_count = 0
            devices = await db.execute(select(Equipment.id, Equipment.category_description))

            for device_id, desc in devices.fetchall():
                if not desc:
                    continue

                level1, level2 = parse_category_hierarchy(desc)

                # 优先使用二级分类，如果没有则使用一级分类
                target_category = level2 or level1

                if target_category in name_to_id:
                    category_id = name_to_id[target_category]

                    # 检查是否已有关联
                    existing_link = await db.execute(
                        select(EquipmentCategoryLink).where(
                            EquipmentCategoryLink.equipment_id == device_id,
                            EquipmentCategoryLink.category_id == category_id,
                            ~EquipmentCategoryLink.is_deleted,
                        )
                    )

                    if not existing_link.scalar_one_or_none():
                        link = EquipmentCategoryLink(
                            equipment_id=device_id,
                            category_id=category_id,
                        )
                        db.add(link)
                        linked_count += 1

            await db.commit()
            print(f"   ✅ 创建了 {linked_count} 个设备分类关联")

            # Step 7: 验证结果
            print("\n📊 步骤 7: 验证结果...")
            total_categories = await db.execute(select(EquipmentCategory))
            total_categories_count = len(total_categories.scalars().all())

            total_links = await db.execute(select(EquipmentCategoryLink).where(~EquipmentCategoryLink.is_deleted))
            total_links_count = len(total_links.scalars().all())

            devices_with_category = await db.execute(
                select(Equipment).join(EquipmentCategoryLink).where(~EquipmentCategoryLink.is_deleted)
            )
            devices_with_category_count = len(devices_with_category.scalars().all())

            print(f"   分类总数: {total_categories_count}")
            print(f"   分类关联数: {total_links_count}")
            print(f"   有分类的设备: {devices_with_category_count}")

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
