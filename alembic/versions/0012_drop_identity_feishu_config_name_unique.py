"""drop identity feishu config name unique

Revision ID: 0012_drop_identity_feishu_config_name_unique
Revises: 0012_add_identity_feishu_configs
Create Date: 2026-07-03 00:00:01.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0012_drop_identity_feishu_config_name_unique"
down_revision: str | None = "0011_add_identity_feishu_configs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_identity_feishu_configs_name",
        "feishu_configs",
        schema="identity",
        type_="unique",
    )


def downgrade() -> None:
    op.create_unique_constraint(
        "uq_identity_feishu_configs_name",
        "feishu_configs",
        ["config_name"],
        schema="identity",
    )
