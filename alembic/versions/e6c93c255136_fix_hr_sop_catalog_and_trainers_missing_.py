"""fix hr sop_catalog and trainers missing columns

Revision ID: e6c93c255136
Revises: a09acdc0169c
Create Date: 2026-06-29 20:11:40.076320
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e6c93c255136"
down_revision: str | None = "a09acdc0169c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # hr.sop_catalog
    op.add_column(
        "sop_catalog", sa.Column("created_by", sa.Uuid(), nullable=True), schema="hr"
    )
    op.add_column(
        "sop_catalog", sa.Column("updated_by", sa.Uuid(), nullable=True), schema="hr"
    )

    # hr.trainers: new columns
    op.add_column(
        "trainers",
        sa.Column("certification_date", sa.Date(), nullable=True),
        schema="hr",
    )
    op.add_column(
        "trainers",
        sa.Column("confirmation_date", sa.Date(), nullable=True),
        schema="hr",
    )
    op.add_column(
        "trainers",
        sa.Column("confirmation_reminder", sa.Date(), nullable=True),
        schema="hr",
    )
    op.add_column(
        "trainers",
        sa.Column(
            "is_primary_trainer", sa.Boolean(), server_default="false", nullable=False
        ),
        schema="hr",
    )
    op.add_column(
        "trainers", sa.Column("created_by", sa.Uuid(), nullable=True), schema="hr"
    )
    op.add_column(
        "trainers", sa.Column("updated_by", sa.Uuid(), nullable=True), schema="hr"
    )

    # hr.trainers: drop old columns
    op.drop_column("trainers", "is_level1", schema="hr")
    op.drop_column("trainers", "cert_date", schema="hr")
    op.drop_column("trainers", "remind_date", schema="hr")
    op.drop_column("trainers", "confirm_date", schema="hr")


def downgrade() -> None:
    op.add_column(
        "trainers", sa.Column("confirm_date", sa.Date(), nullable=True), schema="hr"
    )
    op.add_column(
        "trainers", sa.Column("remind_date", sa.Date(), nullable=True), schema="hr"
    )
    op.add_column(
        "trainers", sa.Column("cert_date", sa.Date(), nullable=True), schema="hr"
    )
    op.add_column(
        "trainers",
        sa.Column("is_level1", sa.Boolean(), server_default="false", nullable=True),
        schema="hr",
    )

    op.drop_column("trainers", "updated_by", schema="hr")
    op.drop_column("trainers", "created_by", schema="hr")
    op.drop_column("trainers", "is_primary_trainer", schema="hr")
    op.drop_column("trainers", "confirmation_reminder", schema="hr")
    op.drop_column("trainers", "confirmation_date", schema="hr")
    op.drop_column("trainers", "certification_date", schema="hr")

    op.drop_column("sop_catalog", "updated_by", schema="hr")
    op.drop_column("sop_catalog", "created_by", schema="hr")
