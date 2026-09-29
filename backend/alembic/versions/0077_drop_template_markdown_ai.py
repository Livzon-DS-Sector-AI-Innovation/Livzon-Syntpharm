"""0068_drop_template_markdown_ai

Revision ID: 0068_drop_template_markdown_ai
Revises: 0067_add_template_markdown_ai
Create Date: 2026-09-28 23:30:00.000000

「AI 重组模板 Markdown」功能下线，删除交付物模板的视图缓存两列：

- ``markdown_ai``：AI 重组版 Markdown 缓存文本；
- ``markdown_ai_hash``：生成该文本时的母本 sha256。

两列仅服务弹窗视图缓存（不参与成文），功能移除后无任何读写方。
幂等删除（不存在即跳过），downgrade 可完整还原列结构。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0068_drop_template_markdown_ai"
down_revision: str | Sequence[str] | None = "0067_add_template_markdown_ai"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "rd_deliverable_templates"
_SCHEMA = "research"


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns(_TABLE, schema=_SCHEMA)]

    if "markdown_ai_hash" in columns:
        op.drop_column(_TABLE, "markdown_ai_hash", schema=_SCHEMA)
    if "markdown_ai" in columns:
        op.drop_column(_TABLE, "markdown_ai", schema=_SCHEMA)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns(_TABLE, schema=_SCHEMA)]

    if "markdown_ai" not in columns:
        op.add_column(
            _TABLE,
            sa.Column("markdown_ai", sa.Text(), nullable=True, comment="AI 重组全内容 Markdown（弹窗视图缓存）"),
            schema=_SCHEMA,
        )
    if "markdown_ai_hash" not in columns:
        op.add_column(
            _TABLE,
            sa.Column("markdown_ai_hash", sa.String(length=64), nullable=True, comment="markdown_ai 生成时的母本 sha256"),
            schema=_SCHEMA,
        )
