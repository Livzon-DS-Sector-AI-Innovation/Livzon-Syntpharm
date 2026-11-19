"""registration docx translation glossary terms

Revision ID: 0125_registration_docx_translation_terms
Revises: 0124_registration_project_drug_link
Create Date: 2026-11-17

文档翻译技能的术语表：英文术语（小写去重键）+ 中文术语 + 启停 + 来源。
内置术语由 `docx_translator/seed.py` 在启动时幂等导入。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0125_registration_docx_translation_terms"
down_revision: str = "0124_registration_project_drug_link"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "registration"
_TABLE = "docx_translation_terms"


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("term_en", sa.String(length=300), nullable=False, comment="英文术语"),
        sa.Column("term_en_lower", sa.String(length=300), nullable=False, comment="英文术语小写（去重键）"),
        sa.Column("term_zh", sa.String(length=300), nullable=False, comment="中文术语"),
        sa.Column(
            "is_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            comment="是否启用",
        ),
        sa.Column(
            "source",
            sa.String(length=20),
            nullable=False,
            server_default="manual",
            comment="来源: builtin/manual/import",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["identity.users.id"],
            name="fk_docx_translation_terms_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["identity.users.id"],
            name="fk_docx_translation_terms_updated_by",
        ),
        sa.UniqueConstraint("term_en_lower", name="uq_docx_translation_terms_term_en_lower"),
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_docx_translation_terms_enabled",
        _TABLE,
        ["is_enabled"],
        schema=_SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_docx_translation_terms_enabled", table_name=_TABLE, schema=_SCHEMA)
    op.drop_table(_TABLE, schema=_SCHEMA)
