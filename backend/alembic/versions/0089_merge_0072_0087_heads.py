"""merge heads

Revision ID: 0089_merge_0072_0087_heads
Revises: 0072_add_equipment_quantity, 0087_hr_system_settings
Create Date: 2026-10-20

合并两条迁移链的 head（本迁移不做任何 schema 变更）：

- ``0072_add_equipment_quantity``：main 侧末端（设备导入 v4 / 同步日志 / 设备数量等）
- ``0087_hr_system_settings``：feature 侧末端（权限体系 + 质量提醒 + 人事系统设置）

两条链都从 ``0068_add_background_jobs`` 分叉：main 继续 0069-0072，
本分支用 0085 汇合了 feature 侧的 0084 后再往后加 0086/0087。
不做这次合并的话，``alembic upgrade head`` 会报
``Multiple head revisions are present``。

编号说明：这里刻意跳过 0088 —— 0088 已被 uat 线的
``0088_merge_0081_0087_heads`` 占用（uat 把 research 迁移重编号成 0069-0081，
那是 uat 独有的链）。两边都合入 main 时若同号会导致迁移编号唯一性检查失败。
"""

from collections.abc import Sequence

revision: str = "0089_merge_0072_0087_heads"
down_revision: tuple[str, ...] = (
    "0072_add_equipment_quantity",
    "0087_hr_system_settings",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
