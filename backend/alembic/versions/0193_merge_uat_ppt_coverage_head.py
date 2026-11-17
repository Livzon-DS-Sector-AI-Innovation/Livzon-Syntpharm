"""merge uat #220 ppt-video coverage head into the integration chain

Revision ID: 0193_merge_uat_ppt_coverage_head
Revises: 0190_drop_core_llm_configs_owner_index, 0168_hr_org_sync_running_unique
Create Date: 2026-11-17

uat #220（PPT 讲稿覆盖度与读音校正）在 uat 侧新增了
0167_agent_ppt_video_coverage_and_pronunciation → 0168_hr_org_sync_running_unique
这一小段链，从 0166 分叉出去；集成分支的 main 链已走到 0190。本迁移无 DDL，
仅把两条链收敛回单一 head。

注意：
- 本分支原先把 uat 旧迁移重编号占用的 0167/0168 已再次让位到 0191/0192，
  避免与 uat #220 的新编号冲突（check_migration_numbers 要求 4 位号全局唯一）。
- uat 的 0168_hr_org_sync_running_unique 与 main 的 0117_hr_org_sync_running_unique
  语义重复，已加索引存在性守卫，无论拓扑序先后都可安全执行。
"""

from collections.abc import Sequence

revision: str = "0193_merge_uat_ppt_coverage_head"
down_revision: tuple[str, str] | None = (
    "0190_drop_core_llm_configs_owner_index",
    "0168_hr_org_sync_running_unique",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
