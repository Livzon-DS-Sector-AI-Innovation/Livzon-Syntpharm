"""0072_add_doc_gen_corpus_documents

Revision ID: 0072_add_doc_gen_corpus_documents
Revises: 0071_add_research_knowledge_base
Create Date: 2026-09-24 16:50:00.000000

补写「项目资料块入库（doc_gen corpus）」这一版迁移。

**为什么会有这个文件**：UAT 库的 `alembic_version` 停在
`0072_add_doc_gen_corpus_documents`，表 `research.doc_gen_corpus_documents`
也确实存在（含 4 行数据），但对应的迁移文件与 ORM 代码已不在任何分支里——
属于「影子迁移」。它会让 `alembic upgrade head` 直接报
`Can't locate revision identified by '0072_add_doc_gen_corpus_documents'`，
既挡住新环境初始化，也挡住 UAT 部署（compose 里 backend 依赖 migrate 成功）。

本文件按库中实测结构补写该 revision，使迁移图能走到单一 head：

- **表已存在时不做任何 DDL**（幂等判断），因此对 UAT 及其它现存库是 no-op，
  只把版本链补齐（UAT 的版本行仍是 0063，`alembic current` 即 head）；
- **全新库**会得到一张与 UAT 结构等价的 `research.doc_gen_corpus_documents`，
  避免各环境结构漂移。列名与类型来自 `information_schema` 实测，
  `varchar` 长度按仓库同类表（`doc_gen_input_files`）约定推定；
  唯一约束 `uq_research_doc_gen_corpus_documents_project_sha256` 亦一并创建
  （UAT 实测存在，原补写遗漏，否则全新库与 UAT 结构不一致）。

对应的 ORM 与业务代码不在本仓库，本文件只负责让迁移图可推进；
如该功能确认废弃，后续可单独提 DROP 迁移（需先备份那 4 行数据）。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0072_add_doc_gen_corpus_documents"
down_revision: str | Sequence[str] | None = "0071_add_research_knowledge_base"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "doc_gen_corpus_documents"
_SCHEMA = "research"


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
    # 幂等：UAT 及其它已应用过该 revision 的库直接跳过（表已存在）
    if _TABLE in sa.inspect(op.get_bind()).get_table_names(schema=_SCHEMA):
        return

    op.create_table(
        _TABLE,
        sa.Column("project_id", sa.Uuid(), nullable=False, comment="关联研发项目"),
        sa.Column("file_id", sa.String(length=64), nullable=False, comment="解析与引用用的稳定标识"),
        sa.Column("sha256", sa.String(length=64), nullable=False, comment="内容哈希"),
        sa.Column("original_filename", sa.String(length=500), nullable=False, comment="原始文件名"),
        sa.Column("role", sa.String(length=32), nullable=False, comment="material/literature"),
        sa.Column("page_count", sa.Integer(), nullable=False, comment="页数/行数估计"),
        sa.Column("char_count", sa.Integer(), nullable=False, comment="解析字符数"),
        sa.Column("blocks", sa.JSON(), nullable=True, comment="解析出的文本块"),
        *_base_columns(),
        sa.ForeignKeyConstraint(["project_id"], ["research.rd_projects.id"]),
        *_audit_fks(_TABLE),
        sa.PrimaryKeyConstraint("id"),
        schema=_SCHEMA,
    )
    op.create_index(f"ix_{_SCHEMA}_{_TABLE}_project", _TABLE, ["project_id"], schema=_SCHEMA)
    # UAT 实测存在该唯一约束（contype='u'），原补写遗漏 —— 不补会让全新库与 UAT 结构不一致
    op.create_unique_constraint(
        f"uq_{_SCHEMA}_{_TABLE}_project_sha256", _TABLE, ["project_id", "sha256"], schema=_SCHEMA
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if _TABLE not in inspector.get_table_names(schema=_SCHEMA):
        return
    index_names = {idx["name"] for idx in inspector.get_indexes(_TABLE, schema=_SCHEMA)}
    if f"ix_{_SCHEMA}_{_TABLE}_project" in index_names:
        op.drop_index(f"ix_{_SCHEMA}_{_TABLE}_project", table_name=_TABLE, schema=_SCHEMA)
    # 注意：该表在 UAT 有真实数据，回滚会一并删除，执行前务必备份
    op.drop_table(_TABLE, schema=_SCHEMA)
