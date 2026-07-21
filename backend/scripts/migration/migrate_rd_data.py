# ruff: noqa
"""
研发模块数据迁移脚本

将现有的打通路线和工艺优化记录关联到研发项目。

使用方法：
    cd ~/Livzon/dazah-backend
    python scripts/migrate_rd_data.py [--dry-run]

功能：
    1. 为每条打通路线/工艺优化记录创建或关联研发项目
    2. 创建对应的阶段记录
    3. 更新 project_id 外键
"""

import argparse
import asyncio
import sys
from datetime import datetime
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, ".")

from sqlalchemy import text

from app.core.database import async_engine


async def migrate_data(dry_run: bool = False):
    """执行数据迁移"""

    async with async_engine.begin() as conn:
        print("=" * 60)
        print("研发模块数据迁移")
        print("=" * 60)

        if dry_run:
            print("【DRY RUN 模式 - 不会实际修改数据】\n")

        # 1. 检查现有表和数据
        print("1. 检查数据...")

        # 检查打通路线数据
        try:
            result = await conn.execute(
                text("SELECT COUNT(*) FROM research.route_developments WHERE is_deleted = false")
            )
            route_count = result.scalar()
            print(f"   - 打通路线记录: {route_count} 条")
        except Exception as e:
            print(f"   - 打通路线表不存在或查询失败: {e}")
            route_count = 0

        # 检查工艺优化数据
        try:
            result = await conn.execute(
                text("SELECT COUNT(*) FROM research.process_optimizations WHERE is_deleted = false")
            )
            optimization_count = result.scalar()
            print(f"   - 工艺优化记录: {optimization_count} 条")
        except Exception as e:
            print(f"   - 工艺优化表不存在或查询失败: {e}")
            optimization_count = 0

        # 检查现有项目
        result = await conn.execute(text("SELECT COUNT(*) FROM research.rd_projects WHERE is_deleted = false"))
        project_count = result.scalar()
        print(f"   - 现有研发项目: {project_count} 条")

        if route_count == 0 and optimization_count == 0:
            print("\n没有需要迁移的数据。")
            return

        print()

        # 2. 为打通路线创建/关联项目
        if route_count > 0:
            print("2. 迁移打通路线数据...")

            result = await conn.execute(
                text("""
                SELECT id, product_name, route_name, created_at
                FROM research.route_developments
                WHERE is_deleted = false AND project_id IS NULL
                ORDER BY created_at
            """)
            )
            routes = result.fetchall()

            for route in routes:
                route_id, product_name, route_name, created_at = route

                if dry_run:
                    print(f"   [DRY RUN] 将为打通路线 '{product_name} - {route_name}' 创建项目")
                    continue

                # 创建新项目
                project_id = uuid4()
                await conn.execute(
                    text("""
                    INSERT INTO research.rd_projects
                    (id, name, api_name, status, current_stage, priority, start_date, created_at, updated_at, is_deleted)
                    VALUES (:id, :name, :api_name, 'active', 'route_dev', 'normal', :start_date, NOW(), NOW(), false)
                """),
                    {
                        "id": project_id,
                        "name": product_name,
                        "api_name": product_name,
                        "start_date": created_at.date() if created_at else datetime.now().date(),
                    },
                )

                # 更新打通路线的 project_id
                await conn.execute(
                    text("""
                    UPDATE research.route_developments
                    SET project_id = :project_id, updated_at = NOW()
                    WHERE id = :route_id
                """),
                    {"project_id": project_id, "route_id": route_id},
                )

                # 创建阶段记录
                stage_id = uuid4()
                await conn.execute(
                    text("""
                    INSERT INTO research.rd_stage_records
                    (id, project_id, stage, status, version, started_at, created_at, updated_at, is_deleted)
                    VALUES (:id, :project_id, 'route_dev', 'in_progress', 1, :started_at, NOW(), NOW(), false)
                """),
                    {
                        "id": stage_id,
                        "project_id": project_id,
                        "started_at": created_at,
                    },
                )

                print(f"   ✓ 创建项目 '{product_name}' (ID: {project_id})")

            print()

        # 3. 为工艺优化创建/关联项目
        if optimization_count > 0:
            print("3. 迁移工艺优化数据...")

            result = await conn.execute(
                text("""
                SELECT id, product_name, created_at, project_id
                FROM research.process_optimizations
                WHERE is_deleted = false
                ORDER BY created_at
            """)
            )
            optimizations = result.fetchall()

            for opt in optimizations:
                opt_id, product_name, created_at, existing_project_id = opt

                if existing_project_id:
                    if dry_run:
                        print(f"   [DRY RUN] 工艺优化 '{product_name}' 已关联项目 {existing_project_id}")
                    continue

                if dry_run:
                    print(f"   [DRY RUN] 将为工艺优化 '{product_name}' 创建项目")
                    continue

                # 创建新项目
                project_id = uuid4()
                await conn.execute(
                    text("""
                    INSERT INTO research.rd_projects
                    (id, name, api_name, status, current_stage, priority, start_date, created_at, updated_at, is_deleted)
                    VALUES (:id, :name, :api_name, 'active', 'optimization', 'normal', :start_date, NOW(), NOW(), false)
                """),
                    {
                        "id": project_id,
                        "name": product_name,
                        "api_name": product_name,
                        "start_date": created_at.date() if created_at else datetime.now().date(),
                    },
                )

                # 更新工艺优化的 project_id
                await conn.execute(
                    text("""
                    UPDATE research.process_optimizations
                    SET project_id = :project_id, updated_at = NOW()
                    WHERE id = :opt_id
                """),
                    {"project_id": project_id, "opt_id": opt_id},
                )

                # 创建阶段记录
                stage_id = uuid4()
                await conn.execute(
                    text("""
                    INSERT INTO research.rd_stage_records
                    (id, project_id, stage, status, version, started_at, created_at, updated_at, is_deleted)
                    VALUES (:id, :project_id, 'optimization', 'in_progress', 1, :started_at, NOW(), NOW(), false)
                """),
                    {
                        "id": stage_id,
                        "project_id": project_id,
                        "started_at": created_at,
                    },
                )

                print(f"   ✓ 创建项目 '{product_name}' (ID: {project_id})")

            print()

        if dry_run:
            print("【DRY RUN 完成 - 未实际修改数据】")
        else:
            print("=" * 60)
            print("迁移完成！")
            print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="研发模块数据迁移")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不实际修改数据")
    args = parser.parse_args()

    asyncio.run(migrate_data(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
