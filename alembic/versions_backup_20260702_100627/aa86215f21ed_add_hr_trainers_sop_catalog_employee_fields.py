"""add hr trainers, sop_catalog, employee concurrent_departments & sort_order

Revision ID: aa86215f21ed
Revises: 697ce0ee893f
Create Date: 2026-06-29 16:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from sqlalchemy import text

revision: str = "aa86215f21ed"
down_revision: str | None = "697ce0ee893f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_exists(conn, table_name: str, schema: str) -> bool:
    """Check if a table exists in the database."""
    result = conn.execute(
        text(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = :schema AND table_name = :table
            """
        ),
        {"schema": schema, "table": table_name},
    )
    return result.scalar() is not None


def _column_exists(conn, table_name: str, column_name: str, schema: str) -> bool:
    """Check if a column exists in the database."""
    result = conn.execute(
        text(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = :schema AND table_name = :table AND column_name = :column
            """
        ),
        {"schema": schema, "table": table_name, "column": column_name},
    )
    return result.scalar() is not None


def upgrade() -> None:
    conn = op.get_bind()
    
    # ── hr.employees: add concurrent_departments ──
    if _table_exists(conn, "employees", "hr") and not _column_exists(conn, "employees", "concurrent_departments", "hr"):
        op.add_column(
            "employees",
            sa.Column(
                "concurrent_departments", sa.String(256), nullable=True, comment="兼任部门"
            ),
            schema="hr",
        )
    # ── hr.employees: add sort_order ──
    if _table_exists(conn, "employees", "hr") and not _column_exists(conn, "employees", "sort_order", "hr"):
        op.add_column(
            "employees",
            sa.Column("sort_order", sa.Integer(), nullable=True, comment="Excel行序号"),
            schema="hr",
        )

    # ── hr.sop_catalog: add created_by / updated_by ──
    if _table_exists(conn, "sop_catalog", "hr"):
        if not _column_exists(conn, "sop_catalog", "created_by", "hr"):
            op.add_column(
                "sop_catalog", sa.Column("created_by", sa.Uuid(), nullable=True), schema="hr"
            )
        if not _column_exists(conn, "sop_catalog", "updated_by", "hr"):
            op.add_column(
                "sop_catalog", sa.Column("updated_by", sa.Uuid(), nullable=True), schema="hr"
            )

    # ── hr.trainers: add new columns ──
    if _table_exists(conn, "trainers", "hr"):
        if not _column_exists(conn, "trainers", "certification_date", "hr"):
            op.add_column(
                "trainers",
                sa.Column("certification_date", sa.Date(), nullable=True),
                schema="hr",
            )
        if not _column_exists(conn, "trainers", "confirmation_date", "hr"):
            op.add_column(
                "trainers",
                sa.Column("confirmation_date", sa.Date(), nullable=True),
                schema="hr",
            )
        if not _column_exists(conn, "trainers", "confirmation_reminder", "hr"):
            op.add_column(
                "trainers",
                sa.Column("confirmation_reminder", sa.Date(), nullable=True),
                schema="hr",
            )
        if not _column_exists(conn, "trainers", "is_primary_trainer", "hr"):
            op.add_column(
                "trainers",
                sa.Column(
                    "is_primary_trainer", sa.Boolean(), server_default="false", nullable=False
                ),
                schema="hr",
            )
        if not _column_exists(conn, "trainers", "created_by", "hr"):
            op.add_column(
                "trainers", sa.Column("created_by", sa.Uuid(), nullable=True), schema="hr"
            )
        if not _column_exists(conn, "trainers", "updated_by", "hr"):
            op.add_column(
                "trainers", sa.Column("updated_by", sa.Uuid(), nullable=True), schema="hr"
            )

        # ── hr.trainers: drop old columns ──
        if _column_exists(conn, "trainers", "is_level1", "hr"):
            op.drop_column("trainers", "is_level1", schema="hr")
        if _column_exists(conn, "trainers", "cert_date", "hr"):
            op.drop_column("trainers", "cert_date", schema="hr")
        if _column_exists(conn, "trainers", "remind_date", "hr"):
            op.drop_column("trainers", "remind_date", schema="hr")
        if _column_exists(conn, "trainers", "confirm_date", "hr"):
            op.drop_column("trainers", "confirm_date", schema="hr")


def downgrade() -> None:
    # trainers: restore old columns
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

    # trainers: drop new columns
    op.drop_column("trainers", "updated_by", schema="hr")
    op.drop_column("trainers", "created_by", schema="hr")
    op.drop_column("trainers", "is_primary_trainer", schema="hr")
    op.drop_column("trainers", "confirmation_reminder", schema="hr")
    op.drop_column("trainers", "confirmation_date", schema="hr")
    op.drop_column("trainers", "certification_date", schema="hr")

    # sop_catalog: drop new columns
    op.drop_column("sop_catalog", "updated_by", schema="hr")
    op.drop_column("sop_catalog", "created_by", schema="hr")

    # employees: drop new columns
    op.drop_column("employees", "sort_order", schema="hr")
    op.drop_column("employees", "concurrent_departments", schema="hr")
