"""0117_add_report_gen_prompt_learning

Revision ID: 0117_add_report_gen_prompt_learning
Revises: 0116_add_report_gen_model_snapshot
Create Date: 2026-11-08 14:20:00.000000

给研发报告生成补两张「提示词学习」表：

- ``research.rd_report_gen_examples``：槽位示例库。人工在任务详情里改过的槽位值沉淀成
  few-shot 参照，下次同模板生成时随 ``read_template_outline`` 下发。以
  ``(template_id, slot_key)`` 唯一，重复修正覆盖而不是追加。
- ``research.rd_report_gen_structure_runs``：母本结构解析留痕。每次真实解析落一条，
  存解析当时选中的槽位标识列表，用于事后统计「漏选（人工后补）/多选（人工否掉）」。

只动 research schema（单模块原则）；两张新表无历史数据，不需要回填。
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0117_add_report_gen_prompt_learning"
down_revision: str | Sequence[str] | None = "0116_add_report_gen_model_snapshot"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "research"
_TEMPLATES = "rd_deliverable_templates"


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
        "rd_report_gen_examples",
        *_base_columns(),
        sa.Column(
            "template_id",
            sa.Uuid(),
            nullable=True,
            comment="所属交付物模板；空=跨模板通用",
        ),
        sa.Column("slot_key", sa.String(length=100), nullable=False, comment="槽位稳定标识"),
        sa.Column("slot_label", sa.String(length=200), nullable=False, server_default="", comment="槽位名称"),
        sa.Column(
            "source",
            sa.String(length=20),
            nullable=False,
            server_default="manual_edit",
            comment="manual_edit=人工修正 / agent_filled=模型填充",
        ),
        sa.Column("value", sa.Text(), nullable=False, comment="该槽位的正确写法"),
        sa.Column("evidence_text", sa.Text(), nullable=True, comment="当时引用的原文证据"),
        sa.Column("query_text", sa.Text(), nullable=True, comment="当时用的检索词"),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0", comment="被注入次数"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true", comment="是否参与注入"),
        sa.ForeignKeyConstraint(
            ["template_id"],
            [f"{_SCHEMA}.{_TEMPLATES}.id"],
            name="fk_research_rd_report_gen_examples_template",
        ),
        sa.UniqueConstraint("template_id", "slot_key", name="uq_research_rd_report_gen_examples_slot"),
        sa.CheckConstraint(
            "source IN ('manual_edit', 'agent_filled')",
            name="ck_research_rd_report_gen_examples_source",
        ),
        *_base_constraints("rd_report_gen_examples"),
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_research_rd_report_gen_examples_template",
        "rd_report_gen_examples",
        ["template_id", "is_active"],
        schema=_SCHEMA,
    )

    op.create_table(
        "rd_report_gen_structure_runs",
        *_base_columns(),
        sa.Column("template_id", sa.Uuid(), nullable=False, comment="所属交付物模板"),
        sa.Column("source_key", sa.String(length=500), nullable=True, comment="母本存储键"),
        sa.Column("prompt_version", sa.String(length=20), nullable=False, comment="解析所用提示词指纹"),
        sa.Column("model_name", sa.String(length=200), nullable=True, comment="解析所用模型档位"),
        sa.Column("candidate_count", sa.Integer(), nullable=False, server_default="0", comment="候选位置数"),
        sa.Column("slot_count", sa.Integer(), nullable=False, server_default="0", comment="判定出的槽位数"),
        sa.Column(
            "slot_keys",
            sa.JSON(),
            nullable=True,
            comment="判定出的槽位标识（有序）",
        ),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0", comment="解析耗时毫秒"),
        sa.Column("status", sa.String(length=12), nullable=False, server_default="ok", comment="ok/failed"),
        sa.Column("error", sa.Text(), nullable=True, comment="失败原因"),
        sa.ForeignKeyConstraint(
            ["template_id"],
            [f"{_SCHEMA}.{_TEMPLATES}.id"],
            name="fk_research_rd_report_gen_structure_runs_template",
        ),
        *_base_constraints("rd_report_gen_structure_runs"),
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_research_rd_report_gen_structure_runs_template",
        "rd_report_gen_structure_runs",
        ["template_id", "created_at"],
        schema=_SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_research_rd_report_gen_structure_runs_template",
        table_name="rd_report_gen_structure_runs",
        schema=_SCHEMA,
    )
    op.drop_table("rd_report_gen_structure_runs", schema=_SCHEMA)
    op.drop_index(
        "ix_research_rd_report_gen_examples_template",
        table_name="rd_report_gen_examples",
        schema=_SCHEMA,
    )
    op.drop_table("rd_report_gen_examples", schema=_SCHEMA)
