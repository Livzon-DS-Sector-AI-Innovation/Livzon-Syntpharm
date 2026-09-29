"""0061_merge_0060_heads

Revision ID: 0061_merge_0060_heads
Revises: 0060_add_deliverable_template_versions
Create Date: 2026-09-24 11:00:00.000000

合并两个 0060 分支（交付物模板版本 / 外键与可空性修复），使后续迁移回到单 head。
注：'0060_add_foreign_keys_and_fix_nullable' 在 uat 链中已重编号为
'0064_add_foreign_keys_and_fix_nullable'，且经 0058_add_doc_gen_core_tables
的上游（0066 head）覆盖，故此处不再重复引用。
"""
from collections.abc import Sequence

revision: str = '0061_merge_0060_heads'
down_revision: str | Sequence[str] | None = '0060_add_deliverable_template_versions'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
