"""0076_add_template_markdown_ai

Revision ID: 0076_add_template_markdown_ai
Revises: 0075_align_research_column_comments
Create Date: 2026-09-28 22:30:00.000000

交付物模板新增「AI 重组 Markdown」视图缓存两列：

- ``markdown_ai``：模型读取规则抽取的全内容 Markdown、重组结构后落库的文本；
  仅供「模板 Markdown」弹窗优先展示（``source=ai``），**不参与成文**——
  成文仍以母本 docx + 槽位锚点为唯一事实源。
- ``markdown_ai_hash``：生成该文本时的母本 sha256。读取时与当前母本比对，
  换母本即指纹不符、自动失效回退规则版现转换，无需触发钩子。

两列均可空、幂等添加（存在即跳过），对存量库无破坏。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0076_add_template_markdown_ai"
down_revision: str | Sequence[str] | None = "0075_align_research_column_comments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "rd_deliverable_templates"
_SCHEMA = "research"


def upgrade() -> None:
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


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns(_TABLE, schema=_SCHEMA)]

    if "markdown_ai_hash" in columns:
        op.drop_column(_TABLE, "markdown_ai_hash", schema=_SCHEMA)
    if "markdown_ai" in columns:
        op.drop_column(_TABLE, "markdown_ai", schema=_SCHEMA)
