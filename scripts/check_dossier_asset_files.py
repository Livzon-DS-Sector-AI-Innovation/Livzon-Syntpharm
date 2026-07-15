#!/usr/bin/env python3
"""
dossier_writer 素材文件完整性检查脚本

检查内容：
1. chapter_assets 中每条记录的 file_path 是否在磁盘上真实存在
2. file_path 中的产品目录 ID 是否与 product_dossier_id 一致
3. storage 下是否存在数据库中没有的幽灵产品目录
4. 汇总报告

用法：
    cd dazah-backend
    # 使用默认数据库配置（从 .env 读取）
    python scripts/check_dossier_asset_files.py
    
    # 指定数据库 URL（例如连接到 Docker 数据库）
    DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/dazah \
        python scripts/check_dossier_asset_files.py
"""

import asyncio
import os
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 允许通过环境变量覆盖 DATABASE_URL
if "DATABASE_URL" in os.environ:
    os.environ["APP_DATABASE_URL"] = os.environ["DATABASE_URL"]

from sqlalchemy import text
from app.core.database import engine


async def check_asset_files():
    """检查素材文件完整性"""

    # file_path 在数据库中存储为 "storage/registration/..." 的相对路径
    # 需要基于项目根目录解析
    project_root = Path(__file__).resolve().parent.parent
    print(f"项目根目录: {project_root}")
    print(f"数据库 URL: {engine.url}")
    print()

    async with engine.begin() as conn:
        # ============================================================
        # 1. 查询所有未删除的素材记录
        # ============================================================
        result = await conn.execute(
            text("""
            SELECT
                ca.id AS asset_id,
                ca.original_filename,
                ca.file_path,
                ca.file_type,
                ca.chapter_id,
                dc.chapter_code,
                dc.product_dossier_id,
                pd.product_name,
                ca.created_at
            FROM dossier_writer.chapter_assets ca
            JOIN dossier_writer.dossier_chapters dc ON dc.id = ca.chapter_id
            JOIN dossier_writer.product_dossiers pd ON pd.id = dc.product_dossier_id
            WHERE ca.is_deleted = false
            ORDER BY ca.created_at DESC
        """)
        )
        assets = result.fetchall()

        print(f"{'=' * 80}")
        print(f"一、素材文件存在性检查（共 {len(assets)} 条记录）")
        print(f"{'=' * 80}")

        missing_count = 0
        path_mismatch_count = 0

        for row in assets:
            asset_id, filename, file_path, file_type, chapter_id, chapter_code, dossier_id, product_name, created_at = (
                row
            )

            # file_path 是相对路径，如 "storage/registration/..."
            full_path = project_root / file_path
            exists = full_path.exists()

            # 检查 file_path 中的产品目录 ID 是否与 product_dossier_id 一致
            path_parts = Path(file_path).parts
            path_dossier_id = None
            for i, part in enumerate(path_parts):
                if part == "products" and i + 1 < len(path_parts):
                    path_dossier_id = path_parts[i + 1]
                    break

            path_match = str(dossier_id) == path_dossier_id

            status = "✅" if exists else "❌"
            path_status = "✅" if path_match else "⚠️ 路径不匹配"

            if not exists:
                missing_count += 1
            if not path_match:
                path_mismatch_count += 1

            print(f"  {status} [{chapter_code}] {filename}")
            print(f"     数据库 file_path: {file_path}")
            print(f"     磁盘路径: {full_path}")
            print(f"     文件存在: {exists}  |  路径产品ID匹配: {path_status}")
            if not path_match:
                print(f"     DB product_dossier_id: {dossier_id}")
                print(f"     路径中的产品目录: {path_dossier_id}")
            print()

        # ============================================================
        # 2. 检查 storage 下的幽灵产品目录
        # ============================================================
        print(f"{'=' * 80}")
        print("二、幽灵产品目录检查")
        print(f"{'=' * 80}")

        products_dir = project_root / "storage" / "registration" / "dossier-writer" / "products"
        if not products_dir.exists():
            print(f"  产品目录不存在: {products_dir}")
        else:
            # 查询数据库中所有产品（含已删除）
            result = await conn.execute(
                text("""
                SELECT id, product_name, is_deleted
                FROM dossier_writer.product_dossiers
                ORDER BY created_at
            """)
            )
            db_products = {str(row[0]): (row[1], row[2]) for row in result.fetchall()}

            # 扫描磁盘
            disk_dirs = sorted([d.name for d in products_dir.iterdir() if d.is_dir()])

            ghost_count = 0
            for dirname in disk_dirs:
                if dirname in db_products:
                    name, deleted = db_products[dirname]
                    status = "🗑️ 已删除" if deleted else "✅ 正常"
                    # 统计该目录下的文件数
                    asset_dir = products_dir / dirname / "assets"
                    file_count = sum(1 for _ in asset_dir.rglob("*") if _.is_file()) if asset_dir.exists() else 0
                    print(f"  {status} {dirname} ({name}) — {file_count} 个素材文件")
                else:
                    ghost_count += 1
                    asset_dir = products_dir / dirname / "assets"
                    file_count = sum(1 for _ in asset_dir.rglob("*") if _.is_file()) if asset_dir.exists() else 0
                    print(f"  👻 幽灵目录 {dirname} — {file_count} 个文件（数据库中无此产品）")

            if ghost_count == 0:
                print("  无幽灵目录。")
            else:
                print(f"\n  共发现 {ghost_count} 个幽灵产品目录。")

        # ============================================================
        # 3. 汇总
        # ============================================================
        print()
        print(f"{'=' * 80}")
        print("三、汇总")
        print(f"{'=' * 80}")
        print(f"  素材记录总数: {len(assets)}")
        print(f"  文件缺失: {missing_count}")
        print(f"  路径产品ID不匹配: {path_mismatch_count}")

        if missing_count > 0:
            print()
            print("  ⚠️  存在文件缺失的素材记录，需要重新上传这些素材。")
        if path_mismatch_count > 0:
            print()
            print("  ⚠️  存在路径与数据库不一致的记录，可能需要修正 file_path。")


def main():
    asyncio.run(check_asset_files())


if __name__ == "__main__":
    main()
