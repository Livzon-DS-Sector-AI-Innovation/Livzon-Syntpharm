"""merge main hr chain and registration chain

Revision ID: 0183_merge_main_hr_and_registration_heads
Revises: 0117_hr_org_sync_running_unique, 0182_registration_comment_alignment
Create Date: 2026-11-16

main 的 HR 模块改造链（0115_deviation_investigation_drafts → 0117_hr_org_sync_running_unique）
与本分支注册申报链（…→0182_registration_comment_alignment）收敛为单一 head。

本迁移无 DDL，仅合并两条迁移链。
"""

from collections.abc import Sequence

revision: str = "0183_merge_main_hr_and_registration_heads"
down_revision: tuple[str, str] | None = (
    "0117_hr_org_sync_running_unique",
    "0182_registration_comment_alignment",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
