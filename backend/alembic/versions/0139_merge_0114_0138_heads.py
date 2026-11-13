"""0139_merge_0114_0138_heads

Revision ID: 0139_merge_0114_0138_heads
Revises: 0114_merge_safety_officer_and_deviation_heads, 0138_sync_doc_gen_cache_comments
Create Date: 2026-10-28 09:30:00.000000

合并 origin/main 与研发文档生成线的双 head：
- 0114_merge_safety_officer_and_deviation_heads（main 线：安全风险分级 / 质量偏差重构）
- 0138_sync_doc_gen_cache_comments（研发文档生成 / 知识库线）
"""
from collections.abc import Sequence

revision: str = "0139_merge_0114_0138_heads"
down_revision: str | Sequence[str] | None = (
    "0114_merge_safety_officer_and_deviation_heads",
    "0138_sync_doc_gen_cache_comments",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
