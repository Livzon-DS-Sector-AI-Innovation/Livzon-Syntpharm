"""merge main head and docx translator heads

Revision ID: 0217_merge_main_head_and_docx_translator_heads
Revises: 0143_agent_ppt_video_job_kind, 0206_registration_docx_translation_tasks
Create Date: 2026-11-20

同步 main（#224 PPT 配音视频智能体）后，main 链走到 0143，文档翻译链走到 0206，
本迁移无 DDL，仅把两条链收敛为单一 head。

背景：文档翻译的 4 个迁移原编号 0125-0128 与 main 新增的 0125-0128
（agent_ppt_video / core_llm_config 等）冲突，故整体让位到 0203-0206。
该编号与 uat 侧同一批迁移保持一致，便于后续两轨合并。
"""

from collections.abc import Sequence

revision: str = "0217_merge_main_head_and_docx_translator_heads"
down_revision: tuple[str, str] | None = (
    "0143_agent_ppt_video_job_kind",
    "0206_registration_docx_translation_tasks",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
