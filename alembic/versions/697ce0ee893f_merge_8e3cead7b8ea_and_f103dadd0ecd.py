"""merge 8e3cead7b8ea and f103dadd0ecd

Revision ID: 697ce0ee893f
Revises: 8e3cead7b8ea, f103dadd0ecd
Create Date: 2026-06-29 11:00:00.000000
"""

from collections.abc import Sequence

revision: str = "697ce0ee893f"
down_revision: str | None = ("8e3cead7b8ea", "f103dadd0ecd")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
