"""permission_sync_20260702

Revision ID: 001_permission
Revises: 491129afc8f9
Create Date: 2026-07-02 08:41:56.112106
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_permission'
down_revision: Union[str, None] = '491129afc8f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tables already exist in database, no operations needed
    pass


def downgrade() -> None:
    # Tables already exist in database, no operations needed
    pass
