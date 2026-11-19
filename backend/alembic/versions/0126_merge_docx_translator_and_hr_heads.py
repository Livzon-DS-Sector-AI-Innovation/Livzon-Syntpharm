"""merge docx translator chain and hr/registration merge head

Revision ID: 0126_merge_docx_translator_and_hr_heads
Revises: 0122_merge_main_hr_and_registration_heads, 0125_registration_docx_translation_terms
Create Date: 2026-11-17

文档翻译术语表迁移（0123 → 0124 → 0125）与 main 的 HR/注册合并头（0122）分属两条链，
`alembic heads` 会出现两个 head，CI 的 multi-head 门禁会直接失败。
本迁移无 DDL，仅把两条链收敛为单一 head。
"""

from collections.abc import Sequence

revision: str = "0126_merge_docx_translator_and_hr_heads"
down_revision: tuple[str, str] | None = (
    "0122_merge_main_hr_and_registration_heads",
    "0125_registration_docx_translation_terms",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
