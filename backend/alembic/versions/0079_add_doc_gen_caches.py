"""0079_add_doc_gen_caches

Revision ID: 0079_add_doc_gen_caches
Revises: 0078_add_doc_gen_job_env
Create Date: 2026-09-30 20:00:00.000000

文档生成新增两张旁路缓存表（都可随时清空，代码在表缺失时静默降级为无缓存）：

- ``doc_gen_parse_cache``：文件内容 SHA-256 + 解析器版本 → 解析产物（blocks）。
  同一份资料（尤其扫描件）被多个任务复用时不再重复解析 / OCR；
- ``doc_gen_extract_cache``：模板槽位 + 候选内容哈希 + 提示版本 → 抽取结果。
  重跑时未变的槽位不再重复调模型。

幂等建表（已存在即跳过），不触碰存量数据。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0079_add_doc_gen_caches"
down_revision: str | Sequence[str] | None = "0078_add_doc_gen_job_env"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "research"
_PARSE_TABLE = "doc_gen_parse_cache"
_EXTRACT_TABLE = "doc_gen_extract_cache"


def _base_columns() -> list[sa.Column]:
    """公共审计列（与 app/shared/base_model.py 对齐）。"""
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
    ]


def _audit_fks(table: str) -> list[sa.ForeignKeyConstraint]:
    """审计列外键（命名与其它迁移保持一致）。"""
    return [
        sa.ForeignKeyConstraint(["created_by"], ["identity.users.id"], name=f"fk_{_SCHEMA}_{table}_created_by"),
        sa.ForeignKeyConstraint(["updated_by"], ["identity.users.id"], name=f"fk_{_SCHEMA}_{table}_updated_by"),
    ]


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names(schema=_SCHEMA))

    if _PARSE_TABLE not in tables:
        op.create_table(
            _PARSE_TABLE,
            *_base_columns(),
            sa.Column("content_hash", sa.String(length=64), nullable=False, comment="文件内容 SHA-256"),
            sa.Column("parser_version", sa.String(length=16), nullable=False, comment="解析器版本"),
            sa.Column("file_name", sa.String(length=500), nullable=False, server_default="", comment="原始文件名"),
            sa.Column("page_count", sa.Integer(), nullable=False, server_default="0", comment="页数/行数估计"),
            sa.Column("char_count", sa.Integer(), nullable=False, server_default="0", comment="解析字符数"),
            sa.Column("blocks", sa.JSON(), nullable=False, comment="解析出的文本块"),
            sa.Column("warnings", sa.JSON(), nullable=True, comment="解析时的告警"),
            sa.Column("hits", sa.Integer(), nullable=False, server_default="0", comment="命中次数"),
            sa.UniqueConstraint("content_hash", "parser_version", name="uq_research_doc_gen_parse_cache_hash_version"),
            *_audit_fks(_PARSE_TABLE),
            sa.PrimaryKeyConstraint("id", name=f"pk_{_SCHEMA}_{_PARSE_TABLE}"),
            schema=_SCHEMA,
        )

    if _EXTRACT_TABLE not in tables:
        op.create_table(
            _EXTRACT_TABLE,
            *_base_columns(),
            sa.Column("cache_key", sa.String(length=64), nullable=False, comment="缓存键 SHA-256"),
            sa.Column("slot_key", sa.String(length=150), nullable=False, comment="槽位 key（诊断用）"),
            sa.Column("template_code", sa.String(length=100), nullable=False, comment="模板 code（诊断用）"),
            sa.Column("state", sa.String(length=24), nullable=False, comment="结果状态（诊断用）"),
            sa.Column("payload", sa.JSON(), nullable=False, comment="SlotResult 可序列化形态"),
            sa.Column("hits", sa.Integer(), nullable=False, server_default="0", comment="命中次数"),
            sa.UniqueConstraint("cache_key", name="uq_research_doc_gen_extract_cache_key"),
            *_audit_fks(_EXTRACT_TABLE),
            sa.PrimaryKeyConstraint("id", name=f"pk_{_SCHEMA}_{_EXTRACT_TABLE}"),
            schema=_SCHEMA,
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names(schema=_SCHEMA))
    if _EXTRACT_TABLE in tables:
        op.drop_table(_EXTRACT_TABLE, schema=_SCHEMA)
    if _PARSE_TABLE in tables:
        op.drop_table(_PARSE_TABLE, schema=_SCHEMA)
