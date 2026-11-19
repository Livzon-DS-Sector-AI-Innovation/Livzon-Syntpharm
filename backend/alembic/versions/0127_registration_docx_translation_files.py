"""registration docx translation output files

Revision ID: 0127_registration_docx_translation_files
Revises: 0126_merge_docx_translator_and_hr_heads
Create Date: 2026-11-18

文档翻译产出文件的历史记录（一行 = 一份可下载译文），
支持刷新/重启后仍可下载、逐条软删 + 删对象，以及按保留天数自动清理。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0127_registration_docx_translation_files"
down_revision: str = "0126_merge_docx_translator_and_hr_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "registration"
_TABLE = "docx_translation_files"


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("job_ref", sa.String(length=64), nullable=False, comment="进程内任务ID（排查用）"),
        sa.Column("source_filename", sa.String(length=500), nullable=False, comment="上传的原文件名"),
        sa.Column("output_filename", sa.String(length=500), nullable=False, comment="产出文件名"),
        sa.Column("output_kind", sa.String(length=20), nullable=False, comment="产出类型: bilingual/translated"),
        sa.Column("object_key", sa.String(length=500), nullable=False, comment="MinIO 对象 key（失败行可空）"),
        sa.Column("file_size", sa.BigInteger(), nullable=False, server_default="0", comment="文件大小(字节)"),
        sa.Column("source_lang", sa.String(length=8), nullable=False, comment="源语言"),
        sa.Column("target_lang", sa.String(length=8), nullable=False, comment="目标语言"),
        sa.Column("mode", sa.String(length=20), nullable=False, comment="输出模式: bilingual/replace/both"),
        sa.Column("success_rate", sa.Float(), nullable=False, server_default="0", comment="段落成功率(%)"),
        sa.Column("translated_units", sa.Integer(), nullable=False, server_default="0", comment="已翻译段落数"),
        sa.Column("total_units", sa.Integer(), nullable=False, server_default="0", comment="总段落数"),
        sa.Column(
            "warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
            comment="告警信息",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["identity.users.id"],
            name="fk_docx_translation_files_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["identity.users.id"],
            name="fk_docx_translation_files_updated_by",
        ),
        sa.UniqueConstraint("job_ref", "object_key", name="uq_docx_translation_files_job_object"),
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_docx_translation_files_created_at",
        _TABLE,
        ["created_at"],
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_docx_translation_files_created_by",
        _TABLE,
        ["created_by"],
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_docx_translation_files_source_filename",
        _TABLE,
        ["source_filename"],
        schema=_SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_docx_translation_files_source_filename", table_name=_TABLE, schema=_SCHEMA)
    op.drop_index("ix_docx_translation_files_created_by", table_name=_TABLE, schema=_SCHEMA)
    op.drop_index("ix_docx_translation_files_created_at", table_name=_TABLE, schema=_SCHEMA)
    op.drop_table(_TABLE, schema=_SCHEMA)
