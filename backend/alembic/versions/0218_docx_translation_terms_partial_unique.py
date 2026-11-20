"""docx translation terms: unique only among non-deleted rows

Revision ID: 0218_docx_translation_terms_partial_unique
Revises: 0217_merge_main_head_and_docx_translator_heads
Create Date: 2026-11-20

术语表原先对 `term_en_lower` 建了全表唯一约束，而查询层只按未软删行去重：
软删一条同名词条后再新建，插入会撞唯一约束抛 IntegrityError（500）。
改为「仅未软删行唯一」的部分唯一索引，软删后可重建同名词条。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0218_docx_translation_terms_partial_unique"
down_revision: str | None = "0217_merge_main_head_and_docx_translator_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "registration"
_TABLE = "docx_translation_terms"
_NAME = "uq_docx_translation_terms_term_en_lower"


def upgrade() -> None:
    op.drop_constraint(_NAME, _TABLE, schema=_SCHEMA, type_="unique")
    op.create_index(
        _NAME,
        _TABLE,
        ["term_en_lower"],
        unique=True,
        schema=_SCHEMA,
        postgresql_where=sa.text("is_deleted = false"),
    )


def downgrade() -> None:
    op.drop_index(_NAME, table_name=_TABLE, schema=_SCHEMA)
    op.create_unique_constraint(_NAME, _TABLE, ["term_en_lower"], schema=_SCHEMA)
