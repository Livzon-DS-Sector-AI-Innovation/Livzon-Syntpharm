"""add department contact qa reviewer fields（双轨合并 no-op 占位）

Revision ID: 0174_add_department_contact_qa_reviewer_fields
Revises: 0173_deprecate_deviation_settings_permissions
Create Date: 2026-11-16

本迁移与 uat 链的 0122_add_department_contact_qa_reviewer_fields 是同一逻辑变更在两个集成分支上的编号副本，upgrade 内容逐字一致。
合并后 DDL 以 uat 链版本为准；本文件转为 no-op 占位，仅保持 main 已应用链
（… → 0114_merge_safety_officer_and_deviation_heads）的 revision 引用完整性。
"""

from collections.abc import Sequence

revision: str = "0174_add_department_contact_qa_reviewer_fields"
down_revision: str = "0173_deprecate_deviation_settings_permissions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
