"""merge safety feishu_record_id unique index

Revision ID: 80dbc811b69b
Revises: 2af364a150a5
Create Date: 2026-06-30 14:33:42.709635
"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "80dbc811b69b"
down_revision: str | None = "2af364a150a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
