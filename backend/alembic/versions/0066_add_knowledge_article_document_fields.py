"""add_knowledge_article_document_fields

Revision ID: 0066_add_knowledge_article_document_fields
Revises: 0065_add_capa_table
Create Date: 2026-09-27 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0066_add_knowledge_article_document_fields"
down_revision: str | None = "0065_add_capa_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "knowledge_articles"
SCHEMA = "safety"
FK_NAME = "fk_knowledge_articles_superseded_by_id"

COLUMNS = [
    ("article_no", sa.String(64), {"nullable": True, "comment": "文档编号"}),
    ("version", sa.Integer(), {"nullable": False, "server_default": "1", "comment": "版本号"}),
    ("source", sa.String(255), {"nullable": True, "comment": "来源"}),
    ("author", sa.String(255), {"nullable": True, "comment": "作者"}),
    ("publish_date", sa.DateTime(timezone=True), {"nullable": True, "comment": "发布日期"}),
    ("superseded_by_id", UUID(as_uuid=True), {"nullable": True, "comment": "被哪个新版本替代"}),
    ("notes", sa.Text(), {"nullable": True, "comment": "备注"}),
]


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa_inspect(conn)
    existing_columns = {c["name"] for c in inspector.get_columns(TABLE, schema=SCHEMA)}
    for name, type_, kwargs in COLUMNS:
        if name not in existing_columns:
            op.add_column(TABLE, sa.Column(name, type_, **kwargs), schema=SCHEMA)

    existing_fks = {fk["name"] for fk in inspector.get_foreign_keys(TABLE, schema=SCHEMA)}
    if FK_NAME not in existing_fks:
        op.create_foreign_key(
            FK_NAME,
            TABLE,
            TABLE,
            ["superseded_by_id"],
            ["id"],
            source_schema=SCHEMA,
            referent_schema=SCHEMA,
            ondelete="SET NULL",
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa_inspect(conn)
    existing_columns = {c["name"] for c in inspector.get_columns(TABLE, schema=SCHEMA)}
    existing_fks = {fk["name"] for fk in inspector.get_foreign_keys(TABLE, schema=SCHEMA)}
    if FK_NAME in existing_fks:
        op.drop_constraint(FK_NAME, TABLE, schema=SCHEMA, type_="foreignkey")
    for name, _, _ in reversed(COLUMNS):
        if name in existing_columns:
            op.drop_column(TABLE, name, schema=SCHEMA)
