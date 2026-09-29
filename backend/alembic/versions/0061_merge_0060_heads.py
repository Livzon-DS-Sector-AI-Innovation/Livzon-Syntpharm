"""0061_merge_0060_heads

Revision ID: 0061_merge_0060_heads
Revises: 0060_add_deliverable_template_versions, 0060_add_foreign_keys_and_fix_nullable
Create Date: 2026-09-24 11:00:00.000000

合并两个 0060 分支（交付物模板版本 / 外键与可空性修复），使后续迁移回到单 head。
"""
from collections.abc import Sequence

revision: str = '0061_merge_0060_heads'
down_revision: str | Sequence[str] | None = (
    '0060_add_deliverable_template_versions',
    '0060_add_foreign_keys_and_fix_nullable',
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
