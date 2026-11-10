"""0118_add_report_gen_feedback

Revision ID: 0118_add_report_gen_feedback
Revises: 0117_add_report_gen_prompt_learning
Create Date: 2026-11-08 15:40:00.000000

给研发报告生成补「评审修改意见」表 ``research.rd_report_gen_feedback``：

- 一条记录 = 一次评审里提出的一条意见，可针对整篇（``slot_key`` 为空）或某个槽位。
- ``status`` 只三态：``open`` 待落实 / ``applied`` 已被某次重生成带走 / ``ignored`` 人工判定不采纳。
- ``applied_job_id`` 记录「被哪次重生成落实」，用于事后回答「这条意见到底改没改」。

只动 research schema（单模块原则）；新表无历史数据，不需要回填。
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0118_add_report_gen_feedback"
down_revision: str | Sequence[str] | None = "0117_add_report_gen_prompt_learning"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "research"
_JOBS = "rd_report_gen_jobs"
_REPORTS = "rd_reports"
_TABLE = "rd_report_gen_feedback"


def _base_columns() -> list[sa.Column]:
    """与 ``BaseModel`` 对齐的公共列（含双 FK 到 identity.users）。"""
    return [
        sa.Column("id", sa.Uuid(), nullable=False, comment="主键"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, comment="软删除标记"),
    ]


def _base_constraints(table: str) -> list[sa.schema.BaseConstraint]:
    return [
        sa.PrimaryKeyConstraint("id", name=f"pk_{_SCHEMA}_{table}"),
        sa.ForeignKeyConstraint(["created_by"], ["identity.users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["identity.users.id"]),
    ]


def upgrade() -> None:
    op.create_table(
        _TABLE,
        *_base_columns(),
        sa.Column("job_id", sa.Uuid(), nullable=False, comment="提出意见时对应的生成任务"),
        sa.Column("report_id", sa.Uuid(), nullable=False, comment="所属研发报告（跨任务汇总用）"),
        sa.Column("slot_key", sa.String(length=100), nullable=True, comment="针对的槽位；空=整篇意见"),
        sa.Column("content", sa.Text(), nullable=False, comment="意见内容"),
        sa.Column(
            "status",
            sa.String(length=12),
            nullable=False,
            server_default="open",
            comment="open=待落实 / applied=已被重生成带走 / ignored=不采纳",
        ),
        sa.Column("applied_job_id", sa.Uuid(), nullable=True, comment="落实该意见的重生成任务"),
        sa.ForeignKeyConstraint(["job_id"], [f"{_SCHEMA}.{_JOBS}.id"], name=f"fk_{_SCHEMA}_{_TABLE}_job"),
        sa.ForeignKeyConstraint(
            ["applied_job_id"], [f"{_SCHEMA}.{_JOBS}.id"], name=f"fk_{_SCHEMA}_{_TABLE}_applied_job"
        ),
        sa.ForeignKeyConstraint(["report_id"], [f"{_SCHEMA}.{_REPORTS}.id"], name=f"fk_{_SCHEMA}_{_TABLE}_report"),
        sa.CheckConstraint("status IN ('open', 'applied', 'ignored')", name=f"ck_{_SCHEMA}_{_TABLE}_status"),
        *_base_constraints(_TABLE),
        schema=_SCHEMA,
    )
    op.create_index(
        f"ix_{_SCHEMA}_{_TABLE}_job",
        _TABLE,
        ["job_id", "status"],
        schema=_SCHEMA,
    )
    op.create_index(
        f"ix_{_SCHEMA}_{_TABLE}_report",
        _TABLE,
        ["report_id", "status"],
        schema=_SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(f"ix_{_SCHEMA}_{_TABLE}_report", table_name=_TABLE, schema=_SCHEMA)
    op.drop_index(f"ix_{_SCHEMA}_{_TABLE}_job", table_name=_TABLE, schema=_SCHEMA)
    op.drop_table(_TABLE, schema=_SCHEMA)
