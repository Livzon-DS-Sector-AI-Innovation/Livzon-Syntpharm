"""merge migration heads

Revision ID: d89b9d01b93a
Revises: e49b4ff53298
Create Date: 2026-08-13 08:52:26.153107
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd89b9d01b93a'
down_revision: Union[str, Sequence[str], None] = ('0055_add_sync_operation_log', '29a5a96069e8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
