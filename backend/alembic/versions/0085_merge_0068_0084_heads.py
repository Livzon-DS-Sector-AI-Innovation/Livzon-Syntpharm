"""merge heads

Revision ID: 0085_merge_0068_0084_heads
Revises: 0068_add_background_jobs, 0084_identity_login_lockout
Create Date: 2026-10-16

合并两条迁移链的 head（本迁移不做任何 schema 变更）：
- `0068_add_background_jobs`：main 侧末端（#88 带入的 quality 迁移）
- `0084_identity_login_lockout`：feature 侧末端（权限体系迁移）

两条链都从 `0066_add_knowledge_article_document_fields` 分叉，本迁移只把 head
收敛为一条，避免 `alembic upgrade head` 报 `Multiple head revisions are present`。
"""

from collections.abc import Sequence

revision: str = "0085_merge_0068_0084_heads"
down_revision: tuple[str, ...] = (
    "0068_add_background_jobs",
    "0084_identity_login_lockout",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
