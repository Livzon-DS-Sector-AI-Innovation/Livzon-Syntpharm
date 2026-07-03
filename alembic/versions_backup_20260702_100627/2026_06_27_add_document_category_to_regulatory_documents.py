"""add document_category to regulatory_documents

Revision ID: add_doc_category
Revises: 7ef205f0db8c
Create Date: 2026-06-27

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_doc_category"
down_revision = "a1b2c3d4e5f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add document_category column
    op.add_column(
        "regulatory_documents",
        sa.Column(
            "document_category",
            sa.String(20),
            nullable=True,
            comment="系统分类: attention/general/archive/failed",
            server_default="general",
        ),
        schema="regulatory_tracker",
    )

    # Create index for faster filtering
    op.create_index(
        "ix_regulatory_documents_document_category",
        "regulatory_documents",
        ["document_category"],
        schema="regulatory_tracker",
    )


def downgrade() -> None:
    # Drop index
    op.drop_index(
        "ix_regulatory_documents_document_category",
        table_name="regulatory_documents",
        schema="regulatory_tracker",
    )

    # Drop column
    op.drop_column(
        "regulatory_documents", "document_category", schema="regulatory_tracker"
    )
