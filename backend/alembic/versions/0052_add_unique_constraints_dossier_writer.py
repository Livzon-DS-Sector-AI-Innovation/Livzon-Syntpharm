"""0052_add_unique_constraints_dossier_writer

Revision ID: 0052_add_unique_constraints_dossier_writer
Revises: 0051_add_scheduled_task_tables
Create Date: 2026-08-05 10:30:00.000000

Add partial unique indexes on (chapter_code, category_name) for asset_categories
and (chapter_code, field_name) for field_mappings, both scoped to non-deleted rows.
Duplicate cleanup runs before index creation.
"""
from collections.abc import Sequence

from alembic import op

revision: str = '0052_add_unique_constraints_dossier_writer'
down_revision: str | None = '0051_add_scheduled_task_tables'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CLEANUP_ASSET_CATEGORIES = """
WITH ranked AS (
    SELECT id, chapter_code, category_name,
           ROW_NUMBER() OVER (
               PARTITION BY chapter_code, category_name
               ORDER BY created_at ASC, id ASC
           ) AS rn
    FROM dossier_writer.asset_categories
    WHERE is_deleted = false
),
winners AS (SELECT id AS winner_id, chapter_code, category_name FROM ranked WHERE rn = 1),
losers  AS (SELECT id AS loser_id,  chapter_code, category_name FROM ranked WHERE rn > 1),
mapping AS (
    SELECT l.loser_id, w.winner_id
    FROM losers l
    JOIN winners w ON l.chapter_code = w.chapter_code AND l.category_name = w.category_name
)
UPDATE dossier_writer.chapter_assets
SET category_id = m.winner_id
FROM mapping m
WHERE dossier_writer.chapter_assets.category_id = m.loser_id
"""

DELETE_DUP_ASSET_CATEGORIES = """
DELETE FROM dossier_writer.asset_categories
WHERE id IN (
    SELECT id FROM (
        SELECT id,
               ROW_NUMBER() OVER (
                   PARTITION BY chapter_code, category_name
                   ORDER BY created_at ASC, id ASC
               ) AS rn
        FROM dossier_writer.asset_categories
        WHERE is_deleted = false
    ) sub
    WHERE rn > 1
)
"""

CLEANUP_FIELD_MAPPINGS = """
WITH ranked AS (
    SELECT id, chapter_code, field_name,
           ROW_NUMBER() OVER (
               PARTITION BY chapter_code, field_name
               ORDER BY created_at ASC, id ASC
           ) AS rn
    FROM dossier_writer.field_mappings
    WHERE is_deleted = false
),
winners AS (SELECT id AS winner_id, chapter_code, field_name FROM ranked WHERE rn = 1),
losers  AS (SELECT id AS loser_id,  chapter_code, field_name FROM ranked WHERE rn > 1),
mapping AS (
    SELECT l.loser_id, w.winner_id
    FROM losers l
    JOIN winners w ON l.chapter_code = w.chapter_code AND l.field_name = w.field_name
)
UPDATE dossier_writer.field_fill_results
SET field_mapping_id = m.winner_id
FROM mapping m
WHERE dossier_writer.field_fill_results.field_mapping_id = m.loser_id
"""

DELETE_DUP_FIELD_MAPPINGS = """
DELETE FROM dossier_writer.field_mappings
WHERE id IN (
    SELECT id FROM (
        SELECT id,
               ROW_NUMBER() OVER (
                   PARTITION BY chapter_code, field_name
                   ORDER BY created_at ASC, id ASC
               ) AS rn
        FROM dossier_writer.field_mappings
        WHERE is_deleted = false
    ) sub
    WHERE rn > 1
)
"""


def upgrade() -> None:
    op.execute(CLEANUP_ASSET_CATEGORIES)
    op.execute(DELETE_DUP_ASSET_CATEGORIES)
    op.execute(CLEANUP_FIELD_MAPPINGS)
    op.execute(DELETE_DUP_FIELD_MAPPINGS)

    op.execute("""
        CREATE UNIQUE INDEX uq_asset_categories_chapter_category
        ON dossier_writer.asset_categories (chapter_code, category_name)
        WHERE is_deleted = false
    """)

    op.execute("""
        CREATE UNIQUE INDEX uq_field_mappings_chapter_field
        ON dossier_writer.field_mappings (chapter_code, field_name)
        WHERE is_deleted = false
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS dossier_writer.uq_asset_categories_chapter_category")
    op.execute("DROP INDEX IF EXISTS dossier_writer.uq_field_mappings_chapter_field")
