"""core_add_module_settings_table

Revision ID: d2dfea3363e9
Revises: 7ef205f0db8c
Create Date: 2026-06-27 11:08:58.557566
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used in this file.
revision: str = "d2dfea3363e9"
down_revision: None | str = "7ef205f0db8c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Ensure core schema exists
    op.execute("CREATE SCHEMA IF NOT EXISTS core")

    # Create module_settings table
    op.create_table(
        "module_settings",
        sa.Column(
            "module",
            sa.String(50),
            nullable=False,
            comment="Module name (safety, equipment, energy, hr, regulatory_tracker)",
        ),
        sa.Column(
            "key",
            sa.String(100),
            nullable=False,
            comment="Setting key (e.g., SAFETY_AI_TEXT_MODEL)",
        ),
        sa.Column(
            "value",
            sa.Text(),
            nullable=False,
            comment="Setting value (stored as string, parsed based on value_type)",
        ),
        sa.Column(
            "value_type",
            sa.String(20),
            server_default="string",
            nullable=False,
            comment="Type hint: string, int, bool, json",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Human-readable description for UI display",
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["identity.users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["identity.users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("module", "key", name="uq_module_setting"),
        schema="core",
        comment="Module runtime configuration settings",
    )
    op.create_index(
        op.f("ix_module_settings_module"), "module_settings", ["module"], schema="core"
    )
    op.create_index(
        op.f("ix_module_settings_key"), "module_settings", ["key"], schema="core"
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_module_settings_key"), table_name="module_settings", schema="core"
    )
    op.drop_index(
        op.f("ix_module_settings_module"), table_name="module_settings", schema="core"
    )
    op.drop_table("module_settings", schema="core")
