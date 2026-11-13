"""registration project stages & progress logs

Revision ID: 0118_registration_project_stage_logs
Revises: 0117_registration_project_drug_link
Create Date: 2026-11-12

注册项目页改版：
1. registration_projects 新增项目编号/项目名称/申报前阶段/阶段完成时间/预计递交日期/受理号，
   market 调整为可空；按现有 status 回填 pre_stage，按 product_name 回填 name。
2. 新建 project_progress_logs 进展记录表（审计追踪，只增不删）。
3. drugs 新增受理号 acceptance_number，供申报进度查询侧登记后回写项目状态。

只动 registration schema，单模块迁移。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "0118_registration_project_stage_logs"
down_revision: str = "0117_registration_project_drug_link"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "registration"
_TABLE = "registration_projects"


def upgrade() -> None:
    # ── registration_projects 新字段 ──
    op.add_column(
        _TABLE,
        sa.Column("project_no", sa.String(64), nullable=True, comment="项目编号（留空自动生成）"),
        schema=_SCHEMA,
    )
    op.add_column(_TABLE, sa.Column("name", sa.String(255), nullable=True, comment="项目名称"), schema=_SCHEMA)
    op.add_column(
        _TABLE,
        sa.Column(
            "pre_stage",
            sa.String(32),
            nullable=False,
            server_default="initiation",
            comment="申报前阶段：initiation/data_preparation/internal_review/submission/accepted",
        ),
        schema=_SCHEMA,
    )
    op.add_column(
        _TABLE,
        sa.Column(
            "stage_completed_at",
            JSONB,
            nullable=False,
            server_default="{}",
            comment="各申报前阶段完成时间 {stage: ISO8601 时间}",
        ),
        schema=_SCHEMA,
    )
    op.add_column(
        _TABLE, sa.Column("planned_submission_date", sa.Date(), nullable=True, comment="预计递交日期"), schema=_SCHEMA
    )
    op.add_column(
        _TABLE,
        sa.Column("acceptance_number", sa.String(128), nullable=True, comment="受理号（受理后同步）"),
        schema=_SCHEMA,
    )
    op.alter_column(_TABLE, "market", existing_type=sa.String(128), nullable=True, schema=_SCHEMA)

    # 回填：名称缺省取品种名；阶段按现有状态推导
    op.execute(f"UPDATE {_SCHEMA}.{_TABLE} SET name = product_name WHERE name IS NULL")
    op.execute(
        f"""
        UPDATE {_SCHEMA}.{_TABLE} SET pre_stage = CASE
            WHEN status = 'draft' THEN 'initiation'
            WHEN status = 'preparing' THEN 'data_preparation'
            WHEN status = 'submitted' THEN 'submission'
            ELSE 'accepted'
        END
        """
    )

    op.create_unique_constraint("uq_registration_projects_project_no", _TABLE, ["project_no"], schema=_SCHEMA)
    op.create_check_constraint(
        "ck_registration_projects_pre_stage",
        _TABLE,
        "pre_stage IN ('initiation', 'data_preparation', 'internal_review', 'submission', 'accepted')",
        schema=_SCHEMA,
    )

    # ── 进展记录表（只增不删） ──
    op.create_table(
        "project_progress_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("registration.registration_projects.id"),
            nullable=False,
            comment="所属注册项目ID",
        ),
        sa.Column("log_type", sa.String(16), nullable=False, comment="记录类型：manual=手动 / system=系统自动"),
        sa.Column("content", sa.Text(), nullable=False, comment="记录内容"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("identity.users.id"), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), sa.ForeignKey("identity.users.id"), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        schema=_SCHEMA,
    )
    op.create_check_constraint(
        "ck_project_progress_logs_type", "project_progress_logs", "log_type IN ('manual', 'system')", schema=_SCHEMA
    )
    op.create_index("ix_project_progress_logs_project", "project_progress_logs", ["project_id"], schema=_SCHEMA)

    # ── drugs 受理号 ──
    op.add_column(
        "drugs", sa.Column("acceptance_number", sa.String(128), nullable=True, comment="受理号"), schema=_SCHEMA
    )


def downgrade() -> None:
    op.drop_column("drugs", "acceptance_number", schema=_SCHEMA)
    op.drop_index("ix_project_progress_logs_project", table_name="project_progress_logs", schema=_SCHEMA)
    op.drop_table("project_progress_logs", schema=_SCHEMA)
    op.drop_constraint("ck_registration_projects_pre_stage", _TABLE, type_="check", schema=_SCHEMA)
    op.drop_constraint("uq_registration_projects_project_no", _TABLE, type_="unique", schema=_SCHEMA)
    op.alter_column(_TABLE, "market", existing_type=sa.String(128), nullable=False, schema=_SCHEMA)
    for col in (
        "acceptance_number",
        "planned_submission_date",
        "stage_completed_at",
        "pre_stage",
        "name",
        "project_no",
    ):
        op.drop_column(_TABLE, col, schema=_SCHEMA)
