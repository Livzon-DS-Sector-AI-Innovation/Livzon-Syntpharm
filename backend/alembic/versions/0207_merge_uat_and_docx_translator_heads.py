"""merge uat mainline and docx translator heads

Revision ID: 0207_merge_uat_and_docx_translator_heads
Revises: 0202_core_workbench_todo_reads, 0206_registration_docx_translation_tasks
Create Date: 2026-11-19

集成分支收口：uat 主链已推进到 0202_core_workbench_todo_reads，
文档翻译链从 0124 分叉出去后走到 0206。本迁移无 DDL，仅把两条链合并为单一 head。

说明：文档翻译的 4 个迁移原编号为 0125-0128，与 uat 已占用的 0125-0128
（deviation 附件评论、HR 建表/组织镜像/员工档案）冲突，故整体让位到 0203-0206。
这些迁移尚未进入任何已部署库，可安全重编号；uat 已有的迁移 id 保持原样不动。
"""

from collections.abc import Sequence

revision: str = "0207_merge_uat_and_docx_translator_heads"
down_revision: tuple[str, str] | None = (
    "0202_core_workbench_todo_reads",
    "0206_registration_docx_translation_tasks",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
