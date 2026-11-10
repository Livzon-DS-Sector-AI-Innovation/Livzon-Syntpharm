"""0115_add_rd_report_gen_tables

Revision ID: 0115_add_rd_report_gen_tables
Revises: 0114_drop_doc_gen_tables
Create Date: 2026-11-07 14:00:00.000000

「AI 生成报告」以 Agent 方式重新落地，新增三张表（schema=research）：

- ``rd_report_gen_jobs``：一次生成的输入快照与终态（进度、当前步骤、产物存储键）；
- ``rd_report_gen_steps``：只追加的执行轨迹，详情页按 (job_id, seq) 增量拉取；
- ``rd_report_gen_slots``：逐槽位的填充值、状态、来源与原文证据。

刻意不动 ``rd_reports``：生成输入挂在任务行上，同一报告多次生成各留一份快照，
既有报告 CRUD 与读方完全不受影响。
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from alembic import op

revision: str = "0115_add_rd_report_gen_tables"
down_revision: str | Sequence[str] | None = "0114_drop_doc_gen_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "research"

def _base_columns() -> tuple[Any, ...]:
    """BaseModel 公共列。每次建表都要新建 Column 实例：Column 不能挂到多张表上。"""
    return (
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["identity.users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["identity.users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def upgrade() -> None:
    op.create_table(
        "rd_report_gen_jobs",
        *_base_columns(),
        sa.Column("report_id", sa.Uuid(), nullable=False, comment="关联研发报告"),
        sa.Column("project_id", sa.Uuid(), nullable=False, comment="关联研发项目"),
        sa.Column("deliverable_template_id", sa.Uuid(), nullable=True, comment="使用的交付物模板（Word 母本）"),
        sa.Column("template_file_key", sa.String(length=500), nullable=True, comment="母本存储键快照"),
        sa.Column("template_file_name", sa.String(length=500), nullable=True, comment="母本文件名快照"),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="queued",
            comment="queued/running/completed/failed/cancelled",
        ),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0", comment="进度百分比 0~100"),
        sa.Column("current_step", sa.String(length=300), nullable=True, comment="当前步骤描述"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="失败原因"),
        sa.Column("doc_code", sa.String(length=100), nullable=True, comment="受控编码（输入快照）"),
        sa.Column("drug_name", sa.String(length=200), nullable=True, comment="品种名称（输入快照）"),
        sa.Column("supplement_text", sa.Text(), nullable=True, comment="补充说明（输入快照）"),
        sa.Column("document_object_key", sa.String(length=500), nullable=True, comment="成品 docx 存储键"),
        sa.Column("document_file_name", sa.String(length=500), nullable=True, comment="成品 docx 文件名"),
        sa.Column("comparison_object_key", sa.String(length=500), nullable=True, comment="槽位对照表存储键"),
        sa.Column("slot_total", sa.Integer(), nullable=False, server_default="0", comment="槽位总数"),
        sa.Column("slot_filled", sa.Integer(), nullable=False, server_default="0", comment="已填槽位数"),
        sa.Column("slot_gap", sa.Integer(), nullable=False, server_default="0", comment="缺口槽位数"),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default="false", comment="人工请求终止"),
        sa.Column("rounds", sa.Integer(), nullable=False, server_default="0", comment="已执行的 Agent 轮次"),
        sa.Column("tool_mode", sa.String(length=16), nullable=True, comment="实际使用的协议：tools/json"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True, comment="开始执行时间"),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True, comment="结束时间（含失败/终止）"),
        sa.ForeignKeyConstraint(["report_id"], ["research.rd_reports.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["research.rd_projects.id"]),
        sa.ForeignKeyConstraint(["deliverable_template_id"], ["research.rd_deliverable_templates.id"]),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed', 'cancelled')",
            name="ck_research_rd_report_gen_jobs_status",
        ),
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_research_rd_report_gen_jobs_report", "rd_report_gen_jobs", ["report_id"], schema=_SCHEMA
    )
    op.create_index(
        "ix_research_rd_report_gen_jobs_project", "rd_report_gen_jobs", ["project_id"], schema=_SCHEMA
    )
    op.create_index("ix_research_rd_report_gen_jobs_status", "rd_report_gen_jobs", ["status"], schema=_SCHEMA)

    op.create_table(
        "rd_report_gen_steps",
        *_base_columns(),
        sa.Column("job_id", sa.Uuid(), nullable=False, comment="所属任务"),
        sa.Column("seq", sa.Integer(), nullable=False, comment="任务内自增序号，从 1 起"),
        sa.Column("kind", sa.String(length=20), nullable=False, comment="think/tool_call/tool_result/error/status"),
        sa.Column("title", sa.String(length=300), nullable=False, comment="一句话标题（列表直接展示）"),
        sa.Column("tool_name", sa.String(length=60), nullable=True, comment="工具名"),
        sa.Column("args_summary", sa.JSON(), nullable=True, comment="入参摘要（已截断）"),
        sa.Column("result_summary", sa.Text(), nullable=True, comment="结果摘要（已截断）"),
        sa.Column("status", sa.String(length=12), nullable=False, server_default="ok", comment="ok/failed"),
        sa.Column("duration_ms", sa.Integer(), nullable=True, comment="耗时毫秒"),
        sa.ForeignKeyConstraint(["job_id"], ["research.rd_report_gen_jobs.id"]),
        sa.UniqueConstraint("job_id", "seq", name="uq_research_rd_report_gen_steps_seq"),
        sa.CheckConstraint(
            "kind IN ('think', 'tool_call', 'tool_result', 'error', 'status')",
            name="ck_research_rd_report_gen_steps_kind",
        ),
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_research_rd_report_gen_steps_job_seq", "rd_report_gen_steps", ["job_id", "seq"], schema=_SCHEMA
    )

    op.create_table(
        "rd_report_gen_slots",
        *_base_columns(),
        sa.Column("job_id", sa.Uuid(), nullable=False, comment="所属任务"),
        sa.Column("slot_key", sa.String(length=100), nullable=False, comment="槽位稳定标识"),
        sa.Column("slot_label", sa.String(length=200), nullable=False, server_default="", comment="槽位名称"),
        sa.Column("anchor", sa.JSON(), nullable=True, comment="母本锚点定义"),
        sa.Column("value", sa.Text(), nullable=True, comment="填充值"),
        sa.Column(
            "state",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
            comment="filled/conflict/pending/gap/anchor_unresolved",
        ),
        sa.Column("source_name", sa.String(length=500), nullable=True, comment="来源文件或数据表"),
        sa.Column("evidence", sa.Text(), nullable=True, comment="原文证据（引文）"),
        sa.Column("confidence", sa.Float(), nullable=True, comment="置信度 0~1"),
        sa.Column("owner_hint", sa.String(length=100), nullable=True, comment="缺口责任方提示"),
        sa.ForeignKeyConstraint(["job_id"], ["research.rd_report_gen_jobs.id"]),
        sa.UniqueConstraint("job_id", "slot_key", name="uq_research_rd_report_gen_slots_key"),
        sa.CheckConstraint(
            "state IN ('filled', 'conflict', 'pending', 'gap', 'anchor_unresolved')",
            name="ck_research_rd_report_gen_slots_state",
        ),
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_research_rd_report_gen_slots_job_state", "rd_report_gen_slots", ["job_id", "state"], schema=_SCHEMA
    )


def downgrade() -> None:
    op.drop_table("rd_report_gen_slots", schema=_SCHEMA)
    op.drop_table("rd_report_gen_steps", schema=_SCHEMA)
    op.drop_table("rd_report_gen_jobs", schema=_SCHEMA)
