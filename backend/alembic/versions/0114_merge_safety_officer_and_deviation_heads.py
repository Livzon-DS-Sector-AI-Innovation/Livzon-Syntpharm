"""merge safety officer and deviation heads

合流两个平行 head：合并 `origin/main` 时，本分支的偏差台账链（0106…0113）与
主干新增的「隐患分管安全员」0102 都从 `0101_safety_equipment_facility_evaluation_grade`
分叉，导致 `alembic heads` 出现 2 个 head、`upgrade head` 直接报错。

两侧迁移均已推送/执行过，按 AGENTS.md 不改历史迁移，改为新增本合并迁移把两条链
接到同一个 head。本迁移不产生任何 DDL。

Revision ID: 0114_merge_safety_officer_and_deviation_heads
Revises: 0102_safety_hazard_safety_officer, 0113_add_deviation_attachment_comments
Create Date: 2026-11-12
"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "0114_merge_safety_officer_and_deviation_heads"
down_revision: tuple[str, str] | None = (
    "0102_safety_hazard_safety_officer",
    "0113_add_deviation_attachment_comments",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """两条链各自已建表，这里只需合并版本图。"""


def downgrade() -> None:
    """回退只是重新拆成两个 head，不涉及数据。"""
