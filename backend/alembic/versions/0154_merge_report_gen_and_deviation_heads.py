"""0154_merge_report_gen_and_deviation_heads

Revision ID: 0154_merge_report_gen_and_deviation_heads
Revises: 0153_research_report_gen_edit_restore_operation, 0115_add_deviation_investigation_drafts
Create Date: 2026-11-15 20:55:00.000000

合并两条并行的迁移链，让 ``alembic upgrade head`` 回到单 head：

- 本分支的研发报告生成链：``0114`` → … → ``0153``
- main 的偏差调查草稿链：``0114`` → ``0115_add_deviation_investigation_drafts``

两条链都从 ``0114_merge_safety_officer_and_deviation_heads`` 分叉，合并分支后
heads 变成 2 个，alembic 的 upgrade 与 drift 检查都会直接失败。本迁移只做
拓扑收敛，不含任何 DDL/DML。
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0154_merge_report_gen_and_deviation_heads"
down_revision: str | Sequence[str] | None = (
    "0153_research_report_gen_edit_restore_operation",
    "0115_add_deviation_investigation_drafts",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass