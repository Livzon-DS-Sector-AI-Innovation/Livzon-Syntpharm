"""merge main（agent / 研发 / 文档翻译）与权限委派三条 head

Revision ID: 0222_merge_main_and_permission_heads
Revises: 0218_docx_translation_terms_partial_unique, 0221_permission_retire_person_lookup
Create Date: 2026-11-21

PR #225 从 0122 处分出权限 / HR 主数据链（0207–0221），main 同期新增
agent（PPT 配音视频）链至 0143、registration 文档翻译链至 0218。三条链互不冲突，
本迁移只做合并，不改任何 schema。

编号说明：本链原用 0217 / 0218 / 0219，与 main 的文档翻译迁移（0217 / 0218）撞号，
合入 main 后统一后移为 0220 / 0221 / 0222；已执行过旧 revision ID 的库需先 stamp 到新 ID。
"""

from collections.abc import Sequence

revision: str = "0222_merge_main_and_permission_heads"
down_revision: tuple[str, str] | None = (
    "0218_docx_translation_terms_partial_unique",
    "0221_permission_retire_person_lookup",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass