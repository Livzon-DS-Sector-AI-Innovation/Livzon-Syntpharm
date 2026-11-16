"""merge feature chain into uat mainline

Revision ID: 0188_merge_feature_and_uat_mainline
Revises: 0183_merge_main_hr_and_registration_heads, 0166_research_report_gen_comment_alignment
Create Date: 2026-11-16

功能链（main HR/偏差/注册申报，…→0183）与 uat 主链（…→0166）收敛为单一 head。

背景：main 与 uat 曾双轨演进，同一批偏差/安全迁移在两条链上各有一份编号副本
（upgrade 内容逐字一致）。合并策略：
- uat 链的 0168/0169、0118-0125 保留为真实迁移（加存在性守卫，prod 已建对象则跳过）；
- main 链的同构副本转为 0186/0187、0170-0177 的 no-op 占位 revision，保持已应用链引用完整；
- main 的 0115_add_deviation_investigation_drafts、0116_hr_org_records、
  0117_hr_org_sync_running_unique 保留原始 id（prod 可能先行部署 main）。

本迁移无 DDL，仅合并两条迁移链。
"""

from collections.abc import Sequence

revision: str = "0188_merge_feature_and_uat_mainline"
down_revision: tuple[str, str] | None = (
    "0183_merge_main_hr_and_registration_heads",
    "0166_research_report_gen_comment_alignment",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
