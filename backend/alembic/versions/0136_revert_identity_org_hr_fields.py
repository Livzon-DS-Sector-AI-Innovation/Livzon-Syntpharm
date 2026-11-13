"""revert HR additions to the platform department mirror

Revision ID: 0136_revert_identity_org_hr_fields
Revises: 0135_hr_departments_mirror_and_sync_runs
Create Date: 2026-11-13

Contract phase: HR now reads/writes `hr.departments`. Remove the columns and
sync-run table that the HR org work added to the platform `identity` schema,
and delete the company row HR inserted.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0136_revert_identity_org_hr_fields"
down_revision: str = "0135_hr_departments_mirror_and_sync_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "identity"
_TABLE = "departments"
_ROOT = "od-9c7089e0d3edc7822c0650a9b2ff4318"

_ADDED_COLUMNS = (
    "custom_fields",
    "directory_synced_at",
    "data_source",
    "direct_departments_count",
    "recursive_departments_count",
    "direct_members_count",
    "recursive_members_count",
    "leader_ids",
    "department_path",
    "order_weight",
    "enabled_status",
)


def upgrade() -> None:
    op.execute(sa.text("DELETE FROM identity.departments WHERE feishu_department_id = :root").bindparams(root=_ROOT))
    for column in _ADDED_COLUMNS:
        op.drop_column(_TABLE, column, schema=_SCHEMA)
    op.drop_index("idx_identity_org_sync_runs_started_at", table_name="org_sync_runs", schema=_SCHEMA)
    op.drop_table("org_sync_runs", schema=_SCHEMA)


def downgrade() -> None:
    op.create_table(
        "org_sync_runs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("department_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("people_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Uuid(as_uuid=True), sa.ForeignKey("identity.users.id"), nullable=True),
        sa.Column("updated_by", sa.Uuid(as_uuid=True), sa.ForeignKey("identity.users.id"), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        schema=_SCHEMA,
    )
    op.create_index("idx_identity_org_sync_runs_started_at", "org_sync_runs", ["started_at"], schema=_SCHEMA)
    op.add_column(_TABLE, sa.Column("enabled_status", sa.Boolean(), nullable=True), schema=_SCHEMA)
    op.add_column(_TABLE, sa.Column("order_weight", sa.String(64), nullable=True), schema=_SCHEMA)
    op.add_column(
        _TABLE,
        sa.Column("department_path", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema=_SCHEMA,
    )
    op.add_column(
        _TABLE,
        sa.Column("leader_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema=_SCHEMA,
    )
    op.add_column(_TABLE, sa.Column("recursive_members_count", sa.Integer(), nullable=True), schema=_SCHEMA)
    op.add_column(_TABLE, sa.Column("direct_members_count", sa.Integer(), nullable=True), schema=_SCHEMA)
    op.add_column(_TABLE, sa.Column("recursive_departments_count", sa.Integer(), nullable=True), schema=_SCHEMA)
    op.add_column(_TABLE, sa.Column("direct_departments_count", sa.Integer(), nullable=True), schema=_SCHEMA)
    op.add_column(_TABLE, sa.Column("data_source", sa.Integer(), nullable=True), schema=_SCHEMA)
    op.add_column(_TABLE, sa.Column("directory_synced_at", sa.DateTime(timezone=True), nullable=True), schema=_SCHEMA)
    op.add_column(
        _TABLE,
        sa.Column("custom_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema=_SCHEMA,
    )
