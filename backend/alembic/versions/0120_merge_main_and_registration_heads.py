"""merge main and registration heads

Revision ID: 0120_merge_main_and_registration_heads
Revises: 0114_merge_safety_officer_and_deviation_heads, 0119_registration_letter_trails
Create Date: 2026-11-13

合并 main 与注册管理功能分支的迁移链。本迁移只收敛版本图，不执行 DDL。
"""

from collections.abc import Sequence

revision: str = "0120_merge_main_and_registration_heads"
down_revision: tuple[str, str] = (
    "0114_merge_safety_officer_and_deviation_heads",
    "0119_registration_letter_trails",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
