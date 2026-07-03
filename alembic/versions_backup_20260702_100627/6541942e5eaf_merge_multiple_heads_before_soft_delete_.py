"""merge multiple heads before soft-delete-unique-index migration

Revision ID: 6541942e5eaf
Revises:
Create Date: 2026-06-23 20:50:52.925466
"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "6541942e5eaf"
down_revision: str | None = "7ef205f0db8c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
