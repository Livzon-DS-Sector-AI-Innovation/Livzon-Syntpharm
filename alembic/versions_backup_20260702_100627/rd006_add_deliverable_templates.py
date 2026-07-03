"""add deliverable templates table

Revision ID: rd006
Revises: rd005
Create Date: 2026-06-30
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "rd006"
down_revision = "rd005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rd_deliverable_templates",
        sa.Column("name", sa.String(200), nullable=False, comment="模板名称"),
        sa.Column(
            "deliverable_type", sa.String(50), nullable=False, comment="交付物类型"
        ),
        sa.Column("stage", sa.String(50), nullable=False, comment="所属阶段"),
        sa.Column("description", sa.Text(), nullable=True, comment="模板描述"),
        sa.Column("template_content", sa.Text(), nullable=True, comment="模板内容"),
        sa.Column(
            "template_structure",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="模板结构定义",
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.true(), comment="是否启用"
        ),
        sa.Column("creator_id", sa.UUID(), nullable=True, comment="创建者"),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column(
            "is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.ForeignKeyConstraint(["creator_id"], ["identity.users.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="research",
    )


def downgrade() -> None:
    op.drop_table("rd_deliverable_templates", schema="research")
