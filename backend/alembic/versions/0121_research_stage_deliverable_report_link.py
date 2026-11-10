"""0121_research_stage_deliverable_report_link

Revision ID: 0121_research_stage_deliverable_report_link
Revises: 0120_backfill_report_review_grant
Create Date: 2026-11-08 16:20:00.000000

给 ``research.rd_stage_deliverables`` 补两列，把「阶段交付文档」与「AI 生成的研发报告」连起来：

- ``report_id``：这条交付文档对应哪份研发报告（生成的报告会出现在研发报告模块）。
- ``report_gen_job_id``：这条交付文档最近一次的生成任务，行内进度徽标据此取状态。

两列都可空：历史上手工维护的交付文档没有报告，生成失败/未生成时也允许为空。
外键不级联删除——报告或任务被删时只置空，交付文档本身必须留下。

只动 research schema（单模块原则）；历史数据无对应报告，保持 NULL，不回填。
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0121_research_stage_deliverable_report_link"
down_revision: str | Sequence[str] | None = "0120_backfill_report_review_grant"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "research"
_TABLE = "rd_stage_deliverables"
_REPORTS = "rd_reports"
_JOBS = "rd_report_gen_jobs"

_INDEX_REPORT = f"ix_{_SCHEMA}_{_TABLE}_report"
_INDEX_JOB = f"ix_{_SCHEMA}_{_TABLE}_job"
_FK_REPORT = f"fk_{_SCHEMA}_{_TABLE}_report"
_FK_JOB = f"fk_{_SCHEMA}_{_TABLE}_job"


def upgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column("report_id", sa.Uuid(), nullable=True, comment="AI 生成对应的研发报告"),
        schema=_SCHEMA,
    )
    op.add_column(
        _TABLE,
        sa.Column("report_gen_job_id", sa.Uuid(), nullable=True, comment="最近一次 AI 生成任务"),
        schema=_SCHEMA,
    )
    op.create_foreign_key(
        _FK_REPORT,
        _TABLE,
        _REPORTS,
        ["report_id"],
        ["id"],
        source_schema=_SCHEMA,
        referent_schema=_SCHEMA,
    )
    op.create_foreign_key(
        _FK_JOB,
        _TABLE,
        _JOBS,
        ["report_gen_job_id"],
        ["id"],
        source_schema=_SCHEMA,
        referent_schema=_SCHEMA,
    )
    op.create_index(_INDEX_REPORT, _TABLE, ["report_id"], schema=_SCHEMA)
    op.create_index(_INDEX_JOB, _TABLE, ["report_gen_job_id"], schema=_SCHEMA)


def downgrade() -> None:
    op.drop_index(_INDEX_JOB, table_name=_TABLE, schema=_SCHEMA)
    op.drop_index(_INDEX_REPORT, table_name=_TABLE, schema=_SCHEMA)
    op.drop_constraint(_FK_JOB, _TABLE, schema=_SCHEMA, type_="foreignkey")
    op.drop_constraint(_FK_REPORT, _TABLE, schema=_SCHEMA, type_="foreignkey")
    op.drop_column(_TABLE, "report_gen_job_id", schema=_SCHEMA)
    op.drop_column(_TABLE, "report_id", schema=_SCHEMA)
