"""merge main（agent / 研发）与权限委派两条 head

Revision ID: 0219_merge_main_and_permission_heads
Revises: 0143_agent_ppt_video_job_kind, 0218_permission_retire_person_lookup
Create Date: 2026-11-21

PR #225 从 0122 处分出权限 / HR 主数据链（0207–0218），main 同期在 0123 之后
新增 agent（PPT 配音视频）链至 0143。两条链互不冲突，本迁移只做合并，不改任何 schema。
"""

from collections.abc import Sequence

revision: str = "0219_merge_main_and_permission_heads"
down_revision: tuple[str, str] | None = (
    "0143_agent_ppt_video_job_kind",
    "0218_permission_retire_person_lookup",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass