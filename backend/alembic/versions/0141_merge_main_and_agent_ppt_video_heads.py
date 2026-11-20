"""merge main and agent ppt video heads

Revision ID: 0141_merge_main_and_agent_ppt_video_heads
Revises: 0122_merge_main_hr_and_registration_heads, 0133_agent_ppt_video_coverage_and_pronunciation
Create Date: 2026-11-18

main 的注册申报改造链（…→0122_merge_main_hr_and_registration_heads）
与本分支 PPT 配音视频链（…→0133_agent_ppt_video_coverage_and_pronunciation）
收敛为单一 head。

本迁移无 DDL，仅合并两条迁移链。
"""

from collections.abc import Sequence

revision: str = "0141_merge_main_and_agent_ppt_video_heads"
down_revision: tuple[str, str] | None = (
    "0122_merge_main_hr_and_registration_heads",
    "0133_agent_ppt_video_coverage_and_pronunciation",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass