"""0093_merge_0073_0092_heads

Revision ID: 0093_merge_0073_0092_heads
Revises: 0073_energy_add_workshop_excluded_energy_types, 0092_add_doc_gen_caches
Create Date: 2026-10-21 11:45:00.000000

合并 origin/main 后收敛双 head：
- 0073_energy_add_workshop_excluded_energy_types（main 线）
- 0092_add_doc_gen_caches（研发文档生成/知识库线，原 0067-0079 重编号）
"""
from collections.abc import Sequence

revision: str = "0093_merge_0073_0092_heads"
down_revision: str | Sequence[str] | None = (
    "0073_energy_add_workshop_excluded_energy_types",
    "0092_add_doc_gen_caches",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
