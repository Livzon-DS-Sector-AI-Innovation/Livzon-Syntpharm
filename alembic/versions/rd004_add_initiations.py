"""add rd_initiations table

Revision ID: rd004
Revises: rd003
Create Date: 2026-06-29
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "rd004"
down_revision = "rd003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rd_initiations",
        sa.Column("project_id", sa.UUID(), nullable=False, comment="项目ID"),
        sa.Column("project_background", sa.Text(), nullable=True, comment="项目背景"),
        sa.Column("market_analysis", sa.Text(), nullable=True, comment="市场分析"),
        sa.Column(
            "technical_feasibility", sa.Text(), nullable=True, comment="技术可行性分析"
        ),
        sa.Column(
            "resource_requirements",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="资源需求",
        ),
        sa.Column(
            "timeline_plan",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="时间计划",
        ),
        sa.Column(
            "risk_assessment",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="风险评估",
        ),
        sa.Column("expected_outcomes", sa.Text(), nullable=True, comment="预期成果"),
        sa.Column("applicant_id", sa.UUID(), nullable=True, comment="申请人"),
        sa.Column("application_date", sa.Date(), nullable=True, comment="申请日期"),
        sa.Column(
            "review_status", sa.String(50), server_default="pending", comment="评审状态"
        ),
        sa.Column("reviewer_id", sa.UUID(), nullable=True, comment="评审人"),
        sa.Column("review_date", sa.Date(), nullable=True, comment="评审日期"),
        sa.Column("review_comments", sa.Text(), nullable=True, comment="评审意见"),
        sa.Column("review_score", sa.Integer(), nullable=True, comment="评审评分"),
        sa.Column(
            "approval_status",
            sa.String(50),
            server_default="pending",
            comment="批准状态",
        ),
        sa.Column("approver_id", sa.UUID(), nullable=True, comment="批准人"),
        sa.Column("approval_date", sa.Date(), nullable=True, comment="批准日期"),
        sa.Column("approval_comments", sa.Text(), nullable=True, comment="批准意见"),
        sa.Column(
            "attachments",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="附件列表",
        ),
        sa.Column("notes", sa.Text(), nullable=True, comment="备注"),
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
        sa.ForeignKeyConstraint(["project_id"], ["research.rd_projects.id"]),
        sa.ForeignKeyConstraint(["applicant_id"], ["identity.users.id"]),
        sa.ForeignKeyConstraint(["reviewer_id"], ["identity.users.id"]),
        sa.ForeignKeyConstraint(["approver_id"], ["identity.users.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="research",
    )


def downgrade() -> None:
    op.drop_table("rd_initiations", schema="research")
