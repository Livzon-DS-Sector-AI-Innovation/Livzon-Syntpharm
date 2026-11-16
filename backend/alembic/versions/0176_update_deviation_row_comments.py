"""update deviation row comments（双轨合并 no-op 占位）

Revision ID: 0176_update_deviation_row_comments
Revises: 0175_align_deviation_column_comments
Create Date: 2026-11-16

本迁移与 uat 链的 0124_update_deviation_row_comments 是同一逻辑变更在两个集成分支上的编号副本，upgrade 内容逐字一致。
合并后 DDL 以 uat 链版本为准；本文件转为 no-op 占位，仅保持 main 已应用链
（… → 0114_merge_safety_officer_and_deviation_heads）的 revision 引用完整性。
"""

from collections.abc import Sequence

revision: str = "0176_update_deviation_row_comments"
down_revision: str = "0175_align_deviation_column_comments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
