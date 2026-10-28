"""merge heads

Revision ID: 0090_merge_0073_0089_heads
Revises: 0073_energy_add_workshop_excluded_energy_types, 0089_merge_0072_0087_heads
Create Date: 2026-10-20

合并两条迁移链的 head（本迁移不做任何 schema 变更）：

- ``0073_energy_add_workshop_excluded_energy_types``：main 侧末端（#118 能耗模块车间口径）
- ``0089_merge_0072_0087_heads``：本分支末端（权限体系 + 质量提醒 + 人事系统设置）

main 每次新增迁移都会重新分叉，合入后需再补一个同类 merge 迁移，否则
``alembic upgrade head`` 会报 ``Multiple head revisions are present``。
"""

from collections.abc import Sequence

revision: str = "0090_merge_0073_0089_heads"
down_revision: tuple[str, ...] = (
    "0073_energy_add_workshop_excluded_energy_types",
    "0089_merge_0072_0087_heads",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
