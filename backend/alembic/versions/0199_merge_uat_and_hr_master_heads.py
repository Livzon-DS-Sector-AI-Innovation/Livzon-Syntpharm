"""merge uat head and hr master-data head

Revision ID: 0199_merge_uat_and_hr_master_heads
Revises: 0198_safety_cert_personnel_profile_ref, 0122_merge_main_hr_and_registration_heads
Create Date: 2026-11-18

uat 分支的迁移链（末端 0193 → 本分支 0194-0198）与 main 分支 registration 改造
引入的 `0122_merge_main_hr_and_registration_heads` 是两条平行链。本迁移只做
head 合并，不产生任何 schema 变更，避免 `alembic upgrade head` 出现多个 head。
"""

from collections.abc import Sequence

revision: str = "0199_merge_uat_and_hr_master_heads"
down_revision: tuple[str, str] | None = (
    "0198_safety_cert_personnel_profile_ref",
    "0122_merge_main_hr_and_registration_heads",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass