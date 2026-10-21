"""0094_sync_doc_gen_cache_comments

Revision ID: 0094_sync_doc_gen_cache_comments
Revises: 0093_merge_0073_0092_heads
Create Date: 2026-10-21 15:10:00.000000

把 ``research.doc_gen_parse_cache`` / ``research.doc_gen_extract_cache`` 的列注释
对齐到 ORM 模型（``app/modules/research/doc_gen/models.py``）。

背景：0092 建表时用的是简短文案（「解析器版本」「命中次数」等），随后模型注释被
补全为带用途说明的版本（「解析器版本（行为变更时递增，旧缓存作废）」「命中次数（可观测）」
等），但没同步回迁移，导致 ``alembic check`` 在 CI 报 6 条 ``modify_comment`` 漂移。
本次把库对齐到模型，而不是把模型信息删回简版。

纯注释变更（``COMMENT ON COLUMN``）：不改类型、可空性与约束，不触数据，可安全回滚。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0094_sync_doc_gen_cache_comments"
down_revision: str | Sequence[str] | None = "0093_merge_0073_0092_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "research"
_PARSE_TABLE = "doc_gen_parse_cache"
_EXTRACT_TABLE = "doc_gen_extract_cache"

# (table, column, existing_type, existing_nullable, old_comment, new_comment)
_CHANGES: tuple[tuple[str, str, sa.types.TypeEngine, bool, str, str], ...] = (
    (
        _PARSE_TABLE,
        "parser_version",
        sa.String(length=16),
        False,
        "解析器版本",
        "解析器版本（行为变更时递增，旧缓存作废）",
    ),
    (
        _PARSE_TABLE,
        "file_name",
        sa.String(length=500),
        False,
        "原始文件名",
        "原始文件名（诊断用）",
    ),
    (
        _PARSE_TABLE,
        "blocks",
        sa.JSON(),
        False,
        "解析出的文本块",
        "解析出的文本块（file_id 由调用方回填）",
    ),
    (
        _PARSE_TABLE,
        "hits",
        sa.Integer(),
        False,
        "命中次数",
        "命中次数（可观测）",
    ),
    (
        _EXTRACT_TABLE,
        "payload",
        sa.JSON(),
        False,
        "SlotResult 可序列化形态",
        "SlotResult 的可序列化形态",
    ),
    (
        _EXTRACT_TABLE,
        "hits",
        sa.Integer(),
        False,
        "命中次数",
        "命中次数（可观测）",
    ),
)


def upgrade() -> None:
    for table, column, existing_type, existing_nullable, _old, new in _CHANGES:
        op.alter_column(
            table,
            column,
            existing_type=existing_type,
            existing_nullable=existing_nullable,
            comment=new,
            schema=_SCHEMA,
        )


def downgrade() -> None:
    for table, column, existing_type, existing_nullable, old, _new in _CHANGES:
        op.alter_column(
            table,
            column,
            existing_type=existing_type,
            existing_nullable=existing_nullable,
            comment=old,
            schema=_SCHEMA,
        )
