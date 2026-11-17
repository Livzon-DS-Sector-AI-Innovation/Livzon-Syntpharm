"""0156_merge_hr_and_report_gen_heads

Revision ID: 0156_merge_hr_and_report_gen_heads
Revises: 0117_hr_org_sync_running_unique, 0155_research_report_gen_comment_alignment
Create Date: 2026-11-15 22:30:00.000000

合并两条并行的迁移链，让 ``alembic upgrade head`` 回到单 head：

- main 的 HR 组织架构/台账链：``0115`` → ``0116_hr_org_records`` → ``0117_hr_org_sync_running_unique``
- 本分支的研发报告生成链：``0115`` → ``0154_merge_report_gen_and_deviation_heads`` → ``0155_research_report_gen_comment_alignment``

两条链都从 ``0115_add_deviation_investigation_drafts`` 分叉，合并 main 后
heads 变成 2 个，alembic 的 upgrade 与 drift 检查都会直接失败。本迁移只做
拓扑收敛，不含任何 DDL/DML。
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0156_merge_hr_and_report_gen_heads"
down_revision: str | Sequence[str] | None = (
    "0117_hr_org_sync_running_unique",
    "0155_research_report_gen_comment_alignment",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass