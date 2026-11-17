"""0155_research_report_gen_comment_alignment

Revision ID: 0155_research_report_gen_comment_alignment
Revises: 0154_merge_report_gen_and_deviation_heads
Create Date: 2026-11-15 21:00:00.000000

把 ``research`` schema 下 AI 报告生成相关表的列注释对齐到 ORM 模型。

背景：报告生成二期（在线编辑 / 版本回滚 / 意见库）先写模型、后补迁移，模型侧的
列注释在过程中写得更精确（例如 ``rd_report_gen_document_versions.kind`` 补上
``manual_edit``，``rd_report_gen_examples.source`` 补上
``feedback_promoted``），但这些改动没带迁移，``alembic check`` 一直报漂移。
方向与 0132 一致：**库对齐模型**（模型注释是超集且更准确），因此这里只做
``COMMENT ON COLUMN``，不改类型、可空性与约束，不触数据。

另有两类反向清理（模型侧没有、库里残留）：
- ``rd_report_gen_examples`` / ``rd_report_gen_feedback`` /
  ``rd_report_gen_structure_runs`` 的 ``id``、``is_deleted``：注释来自建表脚本，
  而模型继承 ``BaseModel`` 时不再声明，清掉使库与模型一致；
- 表注释与 ``ix_research_rd_report_gen_jobs_digest`` 索引属于「模型侧漏声明」，
  已在本次模型改动里补回，不需要迁移。

纯注释变更，可安全回滚。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0155_research_report_gen_comment_alignment"
down_revision: str | Sequence[str] | None = "0154_merge_report_gen_and_deviation_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "research"

# (表, 列, 类型, 是否可空, 库中原注释, 模型侧注释)
_COMMENT_ALIGNMENTS: tuple[tuple[str, str, sa.types.TypeEngine[Any], bool, str | None, str | None], ...] = (
    (
        "rd_report_gen_document_versions",
        "kind",
        sa.String(length=20),
        False,
        "ai_draft=AI 初稿 / manual_render=按槽位重渲 / manual_upload=人工上传",
        "ai_draft=AI 初稿 / manual_render=按槽位重渲 / manual_upload=人工上传 / manual_edit=站内在线编辑",
    ),
    (
        "rd_report_gen_document_versions",
        "note",
        sa.String(length=300),
        True,
        "版本说明",
        "版本说明，如「按当前槽位重渲染」",
    ),
    (
        "rd_report_gen_examples",
        "source",
        sa.String(length=20),
        False,
        "manual_edit=人工修正 / agent_filled=模型填充",
        "manual_edit=人工修正 / agent_filled=模型填充 / feedback_promoted=评审意见沉淀",
    ),
    (
        "rd_report_gen_examples",
        "query_text",
        sa.Text(),
        True,
        "当时用的检索词",
        "当时用的检索词（给模型参考）",
    ),
    (
        "rd_report_gen_examples",
        "usage_count",
        sa.Integer(),
        False,
        "被注入次数",
        "被注入到生成任务的次数",
    ),
    ("rd_report_gen_examples", "id", sa.Uuid(), False, "主键", None),
    ("rd_report_gen_examples", "is_deleted", sa.Boolean(), False, "软删除标记", None),
    ("rd_report_gen_feedback", "id", sa.Uuid(), False, "主键", None),
    ("rd_report_gen_feedback", "is_deleted", sa.Boolean(), False, "软删除标记", None),
    (
        "rd_report_gen_opinion_digests",
        "source_hash",
        sa.String(length=64),
        False,
        "意见集合指纹，便于判断汇总是否过期",
        "意见集合指纹，用于判断汇总是否过期",
    ),
    (
        "rd_report_gen_opinions",
        "last_feedback_id",
        sa.Uuid(),
        True,
        "最近一次贡献该意见的原始记录（rd_report_gen_feedback）",
        "最近一次贡献该意见的原始记录",
    ),
    (
        "rd_report_gen_slots",
        "slot_label",
        sa.String(length=200),
        False,
        "槽位名称",
        "槽位名称（如「品种名称」）",
    ),
    (
        "rd_report_gen_structure_runs",
        "source_key",
        sa.String(length=500),
        True,
        "母本存储键",
        "母本存储键（换版即变）",
    ),
    (
        "rd_report_gen_structure_runs",
        "candidate_count",
        sa.Integer(),
        False,
        "候选位置数",
        "送模型的候选位置数",
    ),
    (
        "rd_report_gen_structure_runs",
        "slot_count",
        sa.Integer(),
        False,
        "判定出的槽位数",
        "模型判定出的槽位数",
    ),
    (
        "rd_report_gen_structure_runs",
        "slot_keys",
        postgresql.JSON(astext_type=sa.Text()),
        True,
        "判定出的槽位标识（有序）",
        "模型判定出的槽位标识（有序）",
    ),
    (
        "rd_report_gen_structure_runs",
        "error",
        sa.Text(),
        True,
        "失败原因",
        "失败原因（截断）",
    ),
    ("rd_report_gen_structure_runs", "id", sa.Uuid(), False, "主键", None),
    ("rd_report_gen_structure_runs", "is_deleted", sa.Boolean(), False, "软删除标记", None),
)


def upgrade() -> None:
    for table, column, type_, nullable, _old, new_comment in _COMMENT_ALIGNMENTS:
        op.alter_column(
            table,
            column,
            existing_type=type_,
            existing_nullable=nullable,
            comment=new_comment,
            schema=_SCHEMA,
        )


def downgrade() -> None:
    for table, column, type_, nullable, old_comment, _new in _COMMENT_ALIGNMENTS:
        op.alter_column(
            table,
            column,
            existing_type=type_,
            existing_nullable=nullable,
            comment=old_comment,
            schema=_SCHEMA,
        )