"""merge uat permission head and registration review/letter heads

Revision ID: 0227_merge_uat_permission_and_review_heads
Revises: 0222_merge_main_and_permission_heads, 0226_fix_dossier_products_read_permission
Create Date: 2026-11-25

uat 侧权限线走到 0222（role_owner_delegate / retire_person_lookup 收口），
本分支注册模块线走到 0226（模块下线、产品注册号、dossier 权限修复），
本迁移无 DDL，仅把两条链收敛为单一 head。
"""

from collections.abc import Sequence

revision: str = "0227_merge_uat_permission_and_review_heads"
down_revision: tuple[str, str] | None = (
    "0222_merge_main_and_permission_heads",
    "0226_fix_dossier_products_read_permission",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
