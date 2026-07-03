"""merge heads

Revision ID: 9a01e2d58ecb
Revises:
Create Date: 2026-06-25 22:13:51.864201
"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "9a01e2d58ecb"
down_revision: str | None = "7ef205f0db8c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
