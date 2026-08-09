"""add dossier unique indexes and cleanup

Revision ID: 0053_add_dossier_unique_indexes_and_cleanup
Revises: 0052_add_unique_constraints_dossier_writer
Create Date: 2026-08-05 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0053_add_dossier_unique_indexes_and_cleanup'
down_revision = '0052_add_unique_constraints_dossier_writer'
branch_labels = None
depends_on = None


def upgrade():
    # 1. 存量数据清理
    
    # 清理重复素材（保留最早一条未删除记录）
    op.execute("""
        UPDATE dossier_writer.chapter_assets a1
        SET is_deleted = true
        FROM dossier_writer.chapter_assets a2
        WHERE a1.id > a2.id
          AND a1.chapter_id = a2.chapter_id
          AND a1.original_filename = a2.original_filename
          AND NOT a1.is_deleted
          AND NOT a2.is_deleted;
    """)

    # 清理重复章节
    op.execute("""
        DELETE FROM dossier_writer.dossier_chapters a1
        USING dossier_writer.dossier_chapters a2
        WHERE a1.id > a2.id
          AND a1.product_dossier_id = a2.product_dossier_id
          AND a1.chapter_code = a2.chapter_code
          AND a1.chapter_code IS NOT NULL;
    """)

    # 2. 创建部分唯一索引
    
    # 素材表：同章节下同文件名（未删除）唯一
    op.create_index(
        "idx_chapter_assets_unique_active",
        "chapter_assets",
        ["chapter_id", "original_filename"],
        schema="dossier_writer",
        unique=True,
        postgresql_where=sa.text("NOT is_deleted"),
    )

    # 章节表：同品种下 chapter_code 唯一
    op.create_index(
        "uq_chapters_dossier_code",
        "dossier_chapters",
        ["product_dossier_id", "chapter_code"],
        schema="dossier_writer",
        unique=True,
        postgresql_where=sa.text("chapter_code IS NOT NULL"),
    )


def downgrade():
    op.drop_index("uq_chapters_dossier_code", schema="dossier_writer", table_name="dossier_chapters")
    op.drop_index("idx_chapter_assets_unique_active", schema="dossier_writer", table_name="chapter_assets")
