"""add stage deliverables table

Revision ID: rd002
Revises: rd001
Create Date: 2026-06-28
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "rd002"
down_revision = "rd001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rd_stage_deliverables",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("research.rd_projects.id"),
            nullable=False,
            comment="项目ID",
        ),
        sa.Column("stage", sa.String(50), nullable=False, comment="阶段"),
        sa.Column(
            "deliverable_type", sa.String(100), nullable=False, comment="交付物类型"
        ),
        sa.Column("title", sa.String(500), nullable=False, comment="标题"),
        sa.Column("status", sa.String(50), server_default="draft", comment="状态"),
        sa.Column("version", sa.String(50), server_default="v1.0", comment="版本号"),
        sa.Column("file_url", sa.String(1000), nullable=True, comment="附件URL"),
        sa.Column("file_name", sa.String(500), nullable=True, comment="文件名"),
        sa.Column("file_size", sa.BigInteger, nullable=True, comment="文件大小"),
        sa.Column("content", sa.Text, nullable=True, comment="内容"),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity.users.id"),
            nullable=True,
            comment="负责人",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            comment="创建时间",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            comment="更新时间",
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity.users.id"),
            nullable=True,
            comment="创建人",
        ),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity.users.id"),
            nullable=True,
            comment="更新人",
        ),
        schema="research",
    )

    op.create_index(
        "ix_rd_stage_deliverables_project_id",
        "rd_stage_deliverables",
        ["project_id"],
        schema="research",
    )
    op.create_index(
        "ix_rd_stage_deliverables_stage",
        "rd_stage_deliverables",
        ["stage"],
        schema="research",
    )
    op.create_index(
        "ix_rd_stage_deliverables_deliverable_type",
        "rd_stage_deliverables",
        ["deliverable_type"],
        schema="research",
    )
    op.create_index(
        "ix_rd_stage_deliverables_status",
        "rd_stage_deliverables",
        ["status"],
        schema="research",
    )


def downgrade() -> None:
    op.drop_table("rd_stage_deliverables", schema="research")
