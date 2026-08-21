"""Seed AI field configs for chapter 3.2.S.6 (包装系统) into dossier_writer.field_mappings.

幂等：按 (chapter_code, field_name) 匹配，存在则更新、不存在则插入。
绝不删除已有行 —— dossier_writer.field_fill_results 通过外键引用本表 id（ON DELETE CASCADE）。

Usage（推荐在 backend 容器内执行，asyncpg 与 DATABASE_URL 均已就绪）：
    docker exec -w /app erp-backend python scripts/seed/seed_s6_ai_config.py
若容器内未挂载仓库，则：
    docker cp backend/scripts/seed/seed_s6_ai_config.py erp-backend:/tmp/
    docker exec erp-backend python /tmp/seed_s6_ai_config.py
"""

import asyncio
import os
import uuid

import asyncpg

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

_raw_url = os.getenv(
    "DATABASE_URL",
    "postgresql://erp_user:change-me-in-production@localhost:5432/erp",
)
DATABASE_URL = _raw_url.replace("postgresql+asyncpg://", "postgresql://")

CHAPTER_CODE = "3.2.S.6"

# 数据来源：dossier_writer.field_mappings 现有 15 行实录 + 批次一新增「铝瓶质量标准图片」（附录3）。
# 新增行 sort_order=14，原「厂家报告单图片」顺移至 15、「厂内报告单图片」顺移至 16。
FIELD_CONFIGS = [
    {
        "field_name": "包装形式",
        "field_type": "text",
        "location_type": "paragraph",
        "location_hint": "包装材料类型章节中'包装形式'段落，冒号后填入",
        "extraction_prompt": "从原料药质量标准文档中提取'包装形式'字段值，通常在'5 包装形式：...'段落中",
        "source_type": "asset_extract",
        "source_category": "原料药质量标准",
        "appendix_slot": None,
        "sort_order": 1,
        "is_required": True,
    },
    {
        "field_name": "包装规格",
        "field_type": "text",
        "location_type": "paragraph",
        "location_hint": "包装材料类型章节中'包装规格'段落，冒号后填入",
        "extraction_prompt": "从原料药质量标准文档中提取'包装规格'字段值，通常在'6 规格：...'或'包装规格：...'段落中",
        "source_type": "asset_extract",
        "source_category": "原料药质量标准",
        "appendix_slot": None,
        "sort_order": 2,
        "is_required": True,
    },
    {
        "field_name": "包材类型",
        "field_type": "text",
        "location_type": "table",
        "location_hint": "包装信息表格中'包材类型'行的第二列",
        "extraction_prompt": "从包材质量标准文档中提取直接接触药品的包材类型，如'药用铝瓶Ⅰ'、'玻璃瓶'等",
        "source_type": "asset_extract",
        "source_category": "包材质量标准",
        "appendix_slot": None,
        "sort_order": 3,
        "is_required": True,
    },
    {
        "field_name": "厂内名称",
        "field_type": "text",
        "location_type": "table",
        "location_hint": "包装信息表格中'厂内名称'行的第二列",
        "extraction_prompt": "从包材质量标准文档中提取厂内使用的物料名称，通常在'物料代码'或'基本信息'段落中",
        "source_type": "asset_extract",
        "source_category": "包材质量标准",
        "appendix_slot": None,
        "sort_order": 4,
        "is_required": True,
    },
    {
        "field_name": "包材生产商",
        "field_type": "text",
        "location_type": "table",
        "location_hint": "包装信息表格中'包材生产商'行的第二列",
        "extraction_prompt": "从授权书中提取包材生产商的完整公司名称",
        "source_type": "asset_extract",
        "source_category": "授权书",
        "appendix_slot": None,
        "sort_order": 5,
        "is_required": True,
    },
    {
        "field_name": "包材登记号",
        "field_type": "text",
        "location_type": "table",
        "location_hint": "包装信息表格中'包材登记号'行的第二列",
        "extraction_prompt": "从授权书或包材相关证明材料中提取包材在CDE的登记号",
        "source_type": "asset_extract",
        "source_category": "授权书",
        "appendix_slot": None,
        "sort_order": 6,
        "is_required": True,
    },
    {
        "field_name": "执行质量标准号",
        "field_type": "text",
        "location_type": "table",
        "location_hint": "包装信息表格中'执行质量标准号'行的第二列",
        "extraction_prompt": "从包材质量标准文档中提取企业执行的质量标准编号，如 Q/HCH11-2017",
        "source_type": "asset_extract",
        "source_category": "包材质量标准",
        "appendix_slot": None,
        "sort_order": 7,
        "is_required": True,
    },
    {
        "field_name": "包装材料质量标准表",
        "field_type": "table",
        "location_type": "table",
        "location_hint": "包装材料质量标准章节中的检验项目表格",
        "extraction_prompt": (
            "从包材质量标准文档中提取完整的检验项目表格，包含序号、检验项目、企业内控标准等列，返回二维数组格式"
        ),
        "source_type": "asset_extract",
        "source_category": "包材质量标准",
        "appendix_slot": None,
        "sort_order": 8,
        "is_required": True,
    },
    {
        "field_name": "厂家报告单",
        "field_type": "text",
        "location_type": "table",
        "location_hint": "包装信息表格中'厂家报告单'行的第二列",
        "extraction_prompt": None,
        "source_type": "fixed",
        "source_category": None,
        "appendix_slot": None,
        "sort_order": 9,
        "is_required": False,
    },
    {
        "field_name": "自检报告单",
        "field_type": "text",
        "location_type": "table",
        "location_hint": "包装信息表格中'自检报告单'行的第二列",
        "extraction_prompt": None,
        "source_type": "fixed",
        "source_category": None,
        "appendix_slot": None,
        "sort_order": 10,
        "is_required": False,
    },
    {
        "field_name": "授权书图片",
        "field_type": "image_appendix",
        "location_type": "inline_image",
        "location_hint": "包装材料授权书章节中'图3.2.S.6-1'位置",
        "extraction_prompt": None,
        "source_type": "asset_image",
        "source_category": "授权书",
        "appendix_slot": None,
        "sort_order": 11,
        "is_required": True,
    },
    {
        "field_name": "营业执照图片",
        "field_type": "image_appendix",
        "location_type": "appendix",
        "location_hint": "附录1 营业执照位置",
        "extraction_prompt": None,
        "source_type": "asset_image",
        "source_category": "包材相关证明材料",
        "appendix_slot": "附录1",
        "sort_order": 12,
        "is_required": True,
    },
    {
        "field_name": "CDE公示图片",
        "field_type": "image_appendix",
        "location_type": "appendix",
        "location_hint": "附录2 CDE公示位置",
        "extraction_prompt": None,
        "source_type": "asset_image",
        "source_category": "包材相关证明材料",
        "appendix_slot": "附录2",
        "sort_order": 13,
        "is_required": True,
    },
    {
        "field_name": "铝瓶质量标准图片",
        "field_type": "image_appendix",
        "location_type": "appendix",
        "location_hint": "附录3 铝瓶（厂家）质量标准位置",
        "extraction_prompt": None,
        "source_type": "asset_image",
        "source_category": "质量标准",
        "appendix_slot": "附录3",
        "sort_order": 14,
        "is_required": True,
    },
    {
        "field_name": "厂家报告单图片",
        "field_type": "image_appendix",
        "location_type": "appendix",
        "location_hint": "附录4 厂家报告单位置",
        "extraction_prompt": None,
        "source_type": "asset_image",
        "source_category": "厂家报告单",
        "appendix_slot": "附录4",
        "sort_order": 15,
        "is_required": True,
    },
    {
        "field_name": "厂内报告单图片",
        "field_type": "image_appendix",
        "location_type": "appendix",
        "location_hint": "附录5 厂内报告单位置",
        "extraction_prompt": None,
        "source_type": "asset_image",
        "source_category": "包材相关证明材料",
        "appendix_slot": "附录5",
        "sort_order": 16,
        "is_required": True,
    },
]


async def seed_field_configs(conn: asyncpg.Connection) -> None:
    """Upsert field configs for chapter 3.2.S.6 (never deletes)."""
    inserted = 0
    updated = 0

    for cfg in FIELD_CONFIGS:
        existing = await conn.fetchrow(
            """
            SELECT id FROM dossier_writer.field_mappings
            WHERE chapter_code = $1 AND field_name = $2 AND is_deleted = FALSE
            """,
            CHAPTER_CODE,
            cfg["field_name"],
        )

        if existing:
            # 不触碰 fixed_value 列（保持库中现值）
            await conn.execute(
                """
                UPDATE dossier_writer.field_mappings
                SET field_type = $2,
                    location_type = $3,
                    location_hint = $4,
                    extraction_prompt = $5,
                    source_type = $6,
                    source_category = $7,
                    appendix_slot = $8,
                    sort_order = $9,
                    is_required = $10,
                    updated_at = NOW()
                WHERE id = $1
                """,
                existing["id"],
                cfg["field_type"],
                cfg["location_type"],
                cfg["location_hint"],
                cfg["extraction_prompt"],
                cfg["source_type"],
                cfg["source_category"],
                cfg["appendix_slot"],
                cfg["sort_order"],
                cfg["is_required"],
            )
            updated += 1
        else:
            await conn.execute(
                """
                INSERT INTO dossier_writer.field_mappings
                    (id, chapter_code, field_name, field_type, location_type,
                     location_hint, extraction_prompt, source_type, source_category,
                     appendix_slot, sort_order, is_required, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW(), NOW())
                """,
                uuid.uuid4(),
                CHAPTER_CODE,
                cfg["field_name"],
                cfg["field_type"],
                cfg["location_type"],
                cfg["location_hint"],
                cfg["extraction_prompt"],
                cfg["source_type"],
                cfg["source_category"],
                cfg["appendix_slot"],
                cfg["sort_order"],
                cfg["is_required"],
            )
            inserted += 1

    print(f"[OK] chapter {CHAPTER_CODE}: {inserted} inserted, {updated} updated")


async def main() -> None:
    print("Connecting to database...")
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await seed_field_configs(conn)

        total = await conn.fetchval(
            """
            SELECT COUNT(*) FROM dossier_writer.field_mappings
            WHERE chapter_code = $1 AND is_deleted = FALSE
            """,
            CHAPTER_CODE,
        )
        print(f"[OK] Total rows for {CHAPTER_CODE}: {total} (expected 16)")
        print("\n[OK] Seed completed!")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
