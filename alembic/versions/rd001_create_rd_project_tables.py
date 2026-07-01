"""create rd project tables

Revision ID: rd001
Revises:
Create Date: 2026-06-24 12:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "rd001"
down_revision = "ccd803220bd9"  # 依赖 warehouse
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建 research schema（如果不存在）
    op.execute("CREATE SCHEMA IF NOT EXISTS research")

    # 1. rd_projects - 研发项目主表
    op.create_table(
        "rd_projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, comment="品种名称"),
        sa.Column("api_name", sa.String(200), nullable=False, comment="API全称"),
        sa.Column("cas_number", sa.String(50), nullable=True, comment="CAS号"),
        sa.Column("molecular_formula", sa.String(200), nullable=True, comment="分子式"),
        sa.Column("molecular_weight", sa.Float(), nullable=True, comment="分子量"),
        sa.Column("indication", sa.String(500), nullable=True, comment="适应症"),
        sa.Column(
            "project_type", sa.String(50), nullable=True, comment="generic/improved"
        ),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="initiation",
            comment="当前阶段状态",
        ),
        sa.Column(
            "priority",
            sa.String(20),
            nullable=False,
            server_default="normal",
            comment="low/normal/high/urgent",
        ),
        sa.Column(
            "project_manager_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="项目经理",
        ),
        sa.Column("start_date", sa.Date(), nullable=True, comment="开始日期"),
        sa.Column(
            "target_filing_date", sa.Date(), nullable=True, comment="目标申报日期"
        ),
        sa.Column(
            "actual_filing_date", sa.Date(), nullable=True, comment="实际申报日期"
        ),
        sa.Column("current_stage", sa.String(50), nullable=True, comment="当前阶段"),
        sa.Column("overall_progress", sa.Float(), nullable=True, comment="总体进度%"),
        sa.Column("notes", sa.Text(), nullable=True, comment="备注"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        schema="research",
    )

    # 2. rd_milestones - 里程碑/决策记录
    op.create_table(
        "rd_milestones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="项目ID",
        ),
        sa.Column("title", sa.String(200), nullable=False, comment="标题"),
        sa.Column(
            "milestone_type",
            sa.String(50),
            nullable=True,
            comment="gate_review/decision/achievement",
        ),
        sa.Column("stage", sa.String(50), nullable=True, comment="关联阶段"),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="planned",
            comment="planned/achieved/delayed/cancelled",
        ),
        sa.Column("planned_date", sa.Date(), nullable=True, comment="计划日期"),
        sa.Column("actual_date", sa.Date(), nullable=True, comment="实际日期"),
        sa.Column(
            "decision",
            sa.String(50),
            nullable=True,
            comment="go/no_go/hold/conditional",
        ),
        sa.Column("decision_rationale", sa.Text(), nullable=True, comment="决策理由"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["project_id"], ["research.rd_projects.id"]),
        schema="research",
    )

    # 3. rd_stage_records - 阶段记录
    op.create_table(
        "rd_stage_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="项目ID",
        ),
        sa.Column(
            "stage",
            sa.String(50),
            nullable=False,
            comment="initiation/route_dev/optimization/pilot/validation/filing",
        ),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="not_started",
            comment="not_started/in_progress/review/completed/transferred",
        ),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default="1",
            comment="版本号",
        ),
        sa.Column(
            "input_summary", postgresql.JSON(), nullable=True, comment="上游输入摘要"
        ),
        sa.Column(
            "input_references",
            postgresql.JSON(),
            nullable=True,
            comment="关联的上游记录ID",
        ),
        sa.Column(
            "output_summary", postgresql.JSON(), nullable=True, comment="产出摘要"
        ),
        sa.Column(
            "deliverables", postgresql.JSON(), nullable=True, comment="产出物列表"
        ),
        sa.Column(
            "gate_review_status",
            sa.String(50),
            nullable=True,
            comment="pending/approved/rejected/conditional",
        ),
        sa.Column(
            "gate_hard_conditions",
            postgresql.JSON(),
            nullable=True,
            comment="硬条件检查结果",
        ),
        sa.Column(
            "gate_soft_conditions",
            postgresql.JSON(),
            nullable=True,
            comment="软条件检查结果",
        ),
        sa.Column("gate_review_notes", sa.Text(), nullable=True, comment="评审备注"),
        sa.Column("gate_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("gate_reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["project_id"], ["research.rd_projects.id"]),
        schema="research",
    )

    # 4. rd_research_tracks - 研究项
    op.create_table(
        "rd_research_tracks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="项目ID",
        ),
        sa.Column(
            "type",
            sa.String(50),
            nullable=False,
            comment="impurity/crystal_form/stability/quality_standard/custom",
        ),
        sa.Column("name", sa.String(200), nullable=False, comment="研究项名称"),
        sa.Column("description", sa.Text(), nullable=True, comment="描述"),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="active",
            comment="active/paused/completed/archived",
        ),
        sa.Column(
            "priority",
            sa.String(20),
            nullable=False,
            server_default="normal",
            comment="low/normal/high/urgent",
        ),
        sa.Column("current_conclusion", sa.Text(), nullable=True, comment="当前结论"),
        sa.Column(
            "conclusion_version",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="结论版本号",
        ),
        sa.Column(
            "conclusion_confidence",
            sa.String(50),
            nullable=True,
            comment="preliminary/confirmed/final",
        ),
        sa.Column(
            "active_stages",
            postgresql.ARRAY(sa.String(50)),
            nullable=True,
            comment="活跃阶段列表",
        ),
        sa.Column(
            "owner_id", postgresql.UUID(as_uuid=True), nullable=True, comment="负责人"
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["project_id"], ["research.rd_projects.id"]),
        schema="research",
    )

    # 5. rd_research_findings - 研究发现
    op.create_table(
        "rd_research_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "track_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="研究项ID",
        ),
        sa.Column(
            "stage_record_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="关联阶段记录",
        ),
        sa.Column(
            "finding_type",
            sa.String(50),
            nullable=True,
            comment="identification/classification/control_strategy/characterization",
        ),
        sa.Column("data", postgresql.JSON(), nullable=False, comment="结构化数据"),
        sa.Column("conclusion", sa.Text(), nullable=True, comment="结论"),
        sa.Column(
            "confidence",
            sa.String(50),
            nullable=False,
            server_default="preliminary",
            comment="preliminary/confirmed/final",
        ),
        sa.Column("attachments", postgresql.JSON(), nullable=True, comment="附件列表"),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default="1",
            comment="版本号",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["track_id"], ["research.rd_research_tracks.id"]),
        sa.ForeignKeyConstraint(["stage_record_id"], ["research.rd_stage_records.id"]),
        schema="research",
    )


def downgrade() -> None:
    op.drop_table("rd_research_findings", schema="research")
    op.drop_table("rd_research_tracks", schema="research")
    op.drop_table("rd_stage_records", schema="research")
    op.drop_table("rd_milestones", schema="research")
    op.drop_table("rd_projects", schema="research")
