"""merge heads

Revision ID: 0088_merge_0081_0087_heads
Revises: 0081_add_doc_gen_caches, 0087_hr_system_settings
Create Date: 2026-10-20

合并两条迁移链的 head（本迁移不做任何 schema 变更）：

- ``0081_add_doc_gen_caches``：uat 侧末端（#112 把 research/doc_gen 迁移重编号为 0069-0081）
- ``0087_hr_system_settings``：feature 侧末端（权限体系 + 质量提醒 + 人事系统设置）

两条链在 0085 之后各自延伸（0085 只合了 0068 与 0084，没有覆盖 uat 的 0069-0081），
导致 ``alembic upgrade head`` 报 ``Multiple head revisions are present``、
UAT 部署在 migrate 步骤以 exit 255 失败。本迁移只把 head 收敛为一条。

注意：UAT 库的 ``alembic_version`` 曾被旧合并分支写成 ``0086_merge_0081_0085_heads``
（该 revision 在当前代码库里已不存在）。部署前需把 UAT 库的版本行修正为
``0081_add_doc_gen_caches`` + ``0085_merge_0068_0084_heads`` 两行，再执行 upgrade。
"""

from collections.abc import Sequence

revision: str = "0088_merge_0081_0087_heads"
down_revision: tuple[str, ...] = (
    "0081_add_doc_gen_caches",
    "0087_hr_system_settings",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
