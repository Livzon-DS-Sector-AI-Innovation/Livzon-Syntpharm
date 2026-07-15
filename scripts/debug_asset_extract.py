#!/usr/bin/env python3
"""
素材文件解析诊断脚本
用于验证文件解析器本身能否读出文本，不调用前端、LLM、API
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, "/app")


async def debug_asset_extract(asset_id: str):
    """诊断单个素材文件的解析"""
    from sqlalchemy import select

    from app.core.database import async_session_factory
    from app.modules.registration.dossier_writer.asset_text_extractor import AssetTextExtractor
    from app.modules.registration.dossier_writer.models import ChapterAsset

    print(f"\n{'=' * 80}")
    print(f"诊断素材文件: {asset_id}")
    print(f"{'=' * 80}\n")

    # 1. 从数据库读取记录
    async with async_session_factory() as session:
        stmt = select(ChapterAsset).where(ChapterAsset.id == asset_id)
        result = await session.execute(stmt)
        asset = result.scalar_one_or_none()

        if not asset:
            print(f"❌ 数据库中未找到素材: {asset_id}")
            return

        print("✅ 数据库记录:")
        print(f"   - ID: {asset.id}")
        print(f"   - 文件名: {asset.original_filename}")
        print(f"   - 文件类型: {asset.file_type}")
        print(f"   - 文件大小: {asset.file_size} bytes")
        print(f"   - 数据库路径: {asset.file_path}")

        # 2. 解析真实路径
        file_path = Path(asset.file_path)
        if not file_path.is_absolute():
            file_path = Path("/app") / file_path

        print(f"   - 容器内路径: {file_path}")

        # 3. 检查文件是否存在
        if not file_path.exists():
            print(f"\n❌ 文件不存在: {file_path}")
            return

        file_size = file_path.stat().st_size
        print("\n✅ 文件存在:")
        print(f"   - 实际大小: {file_size} bytes")

        # 4. 调用解析器
        print("\n🔍 开始解析文件...")
        extractor = AssetTextExtractor()

        try:
            result = extractor.extract(file_path)

            print("\n✅ 解析结果:")
            print(f"   - 成功: {result.get('success', False)}")
            print(f"   - 文本长度: {len(result.get('text', ''))} 字符")
            print(f"   - 段落数: {len(result.get('paragraphs', []))}")
            print(f"   - 表格数: {len(result.get('tables', []))}")

            if result.get("error"):
                print("\n❌ 错误信息:")
                print(f"   {result.get('error')}")

            # 5. 输出文本预览
            text = result.get("text", "")
            if text:
                preview = text[:500]
                print("\n📄 文本预览 (前500字符):")
                print(f"{'-' * 80}")
                print(preview)
                print(f"{'-' * 80}")
            else:
                print("\n⚠️  未提取到文本内容")

        except Exception as e:
            print("\n❌ 解析异常:")
            print(f"   - 异常类型: {type(e).__name__}")
            print(f"   - 异常信息: {str(e)}")
            import traceback

            traceback.print_exc()


def main():
    if len(sys.argv) < 2:
        print("用法: python debug_asset_extract.py <asset_id>")
        print("示例: python debug_asset_extract.py fb492ba5-93e1-447b-a693-7ab24c8d2ef0")
        sys.exit(1)

    asset_id = sys.argv[1]
    asyncio.run(debug_asset_extract(asset_id))


if __name__ == "__main__":
    main()
