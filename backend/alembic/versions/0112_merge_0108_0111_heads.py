"""0112_merge_0108_0111_heads

Revision ID: 0112_merge_0108_0111_heads
Revises: 0108_merge_0092_0107_heads, 0111_safety_hazard_identification_ledger_fields
Create Date: 2026-11-05 20:50:00.000000

合并 origin/main 与研发文档生成线的双 head：
- 0108_merge_0092_0107_heads（研发文档生成 / 知识库线）
- 0111_safety_hazard_identification_ledger_fields（main 线：质量偏差流程 / safety 台账字段，
  原 0093-0095 与本线的 0093-0095 编号撞车，合流时重编号为 0109-0111）
"""
from collections.abc import Sequence

revision: str = "0112_merge_0108_0111_heads"
down_revision: str | Sequence[str] | None = (
    "0108_merge_0092_0107_heads",
    "0111_safety_hazard_identification_ledger_fields",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass