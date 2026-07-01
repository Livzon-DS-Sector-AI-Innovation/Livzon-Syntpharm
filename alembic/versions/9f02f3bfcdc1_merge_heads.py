"""merge heads

Revision ID: 9f02f3bfcdc1
Revises: 949d3efb8bf8
Create Date: 2026-06-24 16:12:54.989544
"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "9f02f3bfcdc1"
down_revision: str | None = "949d3efb8bf8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
