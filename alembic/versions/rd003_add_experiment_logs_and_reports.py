"""add experiment logs and reports tables

Revision ID: rd003
Revises: rd002
Create Date: 2026-06-29
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "rd003"
down_revision = "rd002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # RdExperimentLog
    op.create_table(
        "rd_experiment_logs",
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
        sa.Column(
            "stage_record_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("research.rd_stage_records.id"),
            nullable=True,
            comment="关联阶段记录",
        ),
        sa.Column("title", sa.String(300), nullable=False, comment="实验标题"),
        sa.Column("experiment_type", sa.String(50), nullable=False, comment="实验类型"),
        sa.Column("experiment_date", sa.Date, nullable=True, comment="实验日期"),
        sa.Column("operator", sa.String(100), nullable=True, comment="操作人"),
        sa.Column("status", sa.String(50), server_default="planned", comment="状态"),
        sa.Column("objective", sa.Text, nullable=True, comment="实验目的"),
        sa.Column("materials", postgresql.JSON, nullable=True, comment="原辅料信息"),
        sa.Column("equipment", postgresql.JSON, nullable=True, comment="设备信息"),
        sa.Column("procedure", sa.Text, nullable=True, comment="实验步骤"),
        sa.Column("process_params", postgresql.JSON, nullable=True, comment="工艺参数"),
        sa.Column("observations", sa.Text, nullable=True, comment="实验现象"),
        sa.Column("results", postgresql.JSON, nullable=True, comment="实验结果"),
        sa.Column("conclusion", sa.Text, nullable=True, comment="实验结论"),
        sa.Column("issues", sa.Text, nullable=True, comment="问题与讨论"),
        sa.Column("next_steps", sa.Text, nullable=True, comment="后续计划"),
        sa.Column("notes", sa.Text, nullable=True, comment="备注"),
        sa.Column(
            "is_deleted",
            sa.Boolean,
            server_default=sa.text("false"),
            comment="是否删除",
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
        "ix_rd_experiment_logs_project_id",
        "rd_experiment_logs",
        ["project_id"],
        schema="research",
    )
    op.create_index(
        "ix_rd_experiment_logs_type",
        "rd_experiment_logs",
        ["experiment_type"],
        schema="research",
    )
    op.create_index(
        "ix_rd_experiment_logs_status",
        "rd_experiment_logs",
        ["status"],
        schema="research",
    )

    # RdReport
    op.create_table(
        "rd_reports",
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
        sa.Column("title", sa.String(500), nullable=False, comment="报告标题"),
        sa.Column("report_type", sa.String(50), nullable=False, comment="报告类型"),
        sa.Column("stage", sa.String(50), nullable=True, comment="关联阶段"),
        sa.Column("status", sa.String(50), server_default="draft", comment="状态"),
        sa.Column("version", sa.String(50), server_default="v1.0", comment="版本号"),
        sa.Column("content", sa.Text, nullable=True, comment="报告内容"),
        sa.Column("summary", sa.Text, nullable=True, comment="摘要"),
        sa.Column("key_findings", postgresql.JSON, nullable=True, comment="关键发现"),
        sa.Column("recommendations", sa.Text, nullable=True, comment="建议与结论"),
        sa.Column(
            "author_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity.users.id"),
            nullable=True,
            comment="作者",
        ),
        sa.Column(
            "reviewer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity.users.id"),
            nullable=True,
            comment="审核人",
        ),
        sa.Column(
            "reviewed_at", sa.DateTime(timezone=True), nullable=True, comment="审核时间"
        ),
        sa.Column("notes", sa.Text, nullable=True, comment="备注"),
        sa.Column(
            "is_deleted",
            sa.Boolean,
            server_default=sa.text("false"),
            comment="是否删除",
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
        "ix_rd_reports_project_id", "rd_reports", ["project_id"], schema="research"
    )
    op.create_index(
        "ix_rd_reports_type", "rd_reports", ["report_type"], schema="research"
    )
    op.create_index("ix_rd_reports_status", "rd_reports", ["status"], schema="research")


def downgrade() -> None:
    op.drop_table("rd_reports", schema="research")
    op.drop_table("rd_experiment_logs", schema="research")
