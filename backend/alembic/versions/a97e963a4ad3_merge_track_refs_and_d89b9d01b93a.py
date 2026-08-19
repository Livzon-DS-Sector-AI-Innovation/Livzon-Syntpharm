"""merge track_refs and d89b9d01b93a

Revision ID: a97e963a4ad3
Revises: 2026_08_13_track_refs, d89b9d01b93a
Create Date: 2026-08-19 16:43:50.966862
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a97e963a4ad3'
down_revision: Union[str, None] = ('2026_08_13_track_refs', 'd89b9d01b93a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
