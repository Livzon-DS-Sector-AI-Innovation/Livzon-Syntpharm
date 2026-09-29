"""0066_align_research_column_comments

Revision ID: 0066_align_research_column_comments
Revises: 0065_align_llm_configs_column_comment
Create Date: 2026-09-28 10:15:00.000000

把 ``research`` schema 下 11 个列的注释对齐到 ORM 模型。

背景：doc_gen / 知识库重构时模型侧的列注释被写得更精确（例如
``doc_gen_input_files.parse_status`` 从 ``pending/done/failed`` 补成
``pending/done/failed/skipped/ai_fallback``，与实际业务状态一致），但当时的
commit 没有带上对应迁移，导致 ``alembic check`` 一直报漂移。方向统一为
**库对齐模型**（模型注释是超集且更准确），因此本文件只做 ``COMMENT ON COLUMN``。

关联的模型侧改动（同一提交内，无需迁移）：
- ``app/modules/research/knowledge_base/models.py``：``rd_kb_documents.parse_started_at``
  补回注释 ``提交解析时间``（库里有、模型侧丢失）；
- ``app/modules/research/doc_gen/models.py`` / ``app/modules/research/models.py``：
  补声明 3 个库里已存在但模型漏声明的索引（``doc_gen_input_files.job_id``、
  ``doc_gen_slot_values.job_id``、``rd_deliverable_templates.template_code``）。

纯注释变更，不改类型、可空性与约束，不触数据，可安全回滚。
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from alembic import op

revision: str = "0066_align_research_column_comments"
down_revision: str | Sequence[str] | None = "0065_align_llm_configs_column_comment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "research"

# (表, 列, 类型, 是否可空, 库中原注释, 模型侧注释)
_COMMENT_ALIGNMENTS: tuple[tuple[str, str, sa.types.TypeEngine[Any], bool, str, str], ...] = (
    ("doc_gen_conversations", "max_rounds", sa.Integer(), False, "轮数上限", "轮数上限（超过提示转人工确认）"),
    ("doc_gen_input_files", "page_count", sa.Integer(), False, "页数估计", "页数/行数估计"),
    (
        "doc_gen_input_files",
        "parse_status",
        sa.String(length=32),
        False,
        "pending/done/failed",
        "pending/done/failed/skipped/ai_fallback",
    ),
    ("doc_gen_messages", "content", sa.Text(), False, "消息内容", "消息内容（盘点卡为 Markdown 文本）"),
    (
        "doc_gen_sections",
        "section_key",
        sa.String(length=150),
        False,
        "章节实例 key",
        "章节实例 key，如 route_study__0",
    ),
    ("doc_gen_sections", "title", sa.String(length=300), False, "章节标题", "章节标题（不含编号）"),
    (
        "doc_gen_slot_values",
        "section_key",
        sa.String(length=150),
        True,
        "所属章节实例 key",
        "所属章节实例 key；骨架槽位为空",
    ),
    (
        "doc_gen_slot_values",
        "pre_compose_text",
        sa.Text(),
        True,
        "成文前的人工确认文本",
        "成文前的人工确认文本（未成文时为空）",
    ),
    ("rd_kb_documents", "file_ext", sa.String(length=32), False, "扩展名", "扩展名（小写，含点）"),
    ("rd_kb_documents", "sha256", sa.String(length=64), False, "内容哈希", "内容哈希（重复上传提示用）"),
    ("rd_kb_documents", "progress_msg", sa.Text(), True, "解析日志", "解析日志（RAGFlow 原文）"),
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
