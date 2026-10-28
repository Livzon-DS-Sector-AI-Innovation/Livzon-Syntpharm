"""0108_merge_0092_0107_heads

Revision ID: 0108_merge_0092_0107_heads
Revises: 0092_identity_revoked_sessions_comments_fks, 0107_sync_doc_gen_cache_comments
Create Date: 2026-10-28 09:30:00.000000

合并 origin/main 与研发文档生成线的双 head：
- 0092_identity_revoked_sessions_comments_fks（main 线：权限体系 / 身份会话）
- 0107_sync_doc_gen_cache_comments（研发文档生成 / 知识库线，原 0080-0094 重编号）
"""
from collections.abc import Sequence

revision: str = "0108_merge_0092_0107_heads"
down_revision: str | Sequence[str] | None = (
    "0092_identity_revoked_sessions_comments_fks",
    "0107_sync_doc_gen_cache_comments",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
