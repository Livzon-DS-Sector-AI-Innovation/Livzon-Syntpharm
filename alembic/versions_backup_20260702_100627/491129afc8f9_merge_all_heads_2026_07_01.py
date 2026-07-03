"""merge_all_heads_2026_07_01

Revision ID: 491129afc8f9
Revises: add_products_001, add_doc_category, 36830a46e477, 494e3004c6fe, b9c3d8e1f4a2, c637e4490bab, d121aec51082, rd006
Create Date: 2026-07-01 14:07:30.250296
"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "491129afc8f9"
down_revision: str | None = (
    "add_products_001",
    "add_doc_category",
    "36830a46e477",
    "494e3004c6fe",
    "b9c3d8e1f4a2",
    "c637e4490bab",
    "d121aec51082",
    "rd006",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
