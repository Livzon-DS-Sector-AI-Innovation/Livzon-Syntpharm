"""align deviation column comments

Revision ID: 0111_align_deviation_column_comments
Revises: 0110_add_department_contact_qa_reviewer_fields
Create Date: 2026-11-11

偏差台账与部门联系人表的若干 JSONB / 数组列，模型里的 ``comment`` 在迁移
（0106 / 0107 / 0110）落库之后又被补充成更完整的形态，但没跟迁移同步，
导致 ``alembic check`` 一直报 ``modify_comment`` 漂移——相同漂移还会让
``env.py`` 的 ``process_revision_directives`` 误判「有新表需要建 schema」，
额外产出 ``CREATE SCHEMA IF NOT EXISTS quality``。

本迁移只做注释对齐，不动任何列的类型、默认值与可空性。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0111_align_deviation_column_comments"
down_revision: str = "0110_add_department_contact_qa_reviewer_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "quality"

# (表名, 列名, 目标注释, 回滚注释)
_COMMENT_CHANGES: list[tuple[str, str, str, str]] = [
    (
        "deviation_ledger",
        "attachments",
        "附件元数据 [{file_id, file_name, object_key, size, content_type, uploaded_by, uploaded_at}]",
        "附件元数据",
    ),
    (
        "deviation_ledger",
        "ai_analysis",
        "AI 结构化分析 {description, reason, risk_assessment, capa_suggestion}",
        "AI 结构化分析",
    ),
    (
        "deviation_ledger",
        "investigation_records",
        "调查记录 [{content, author_id, author_name, create_time}]",
        "调查记录",
    ),
    (
        "deviation_ledger",
        "review_opinions",
        "审核意见 [{step, result, author_id, author_name, content, create_time}]",
        "审核意见",
    ),
    (
        "deviation_ledger",
        "report_versions",
        "报告版本 [{content, editor_id, editor_name, edit_time, change_summary}]",
        "报告版本",
    ),
    (
        "department_contacts",
        "qa_staff_ids",
        "兼容字段：历史 QA 人员数组（[0]=所属 QA，[1]=QA 负责人），流程以 qa_reviewer_id / qa_head_id 为准",
        "QA 人员（[0]=所属 QA，[1]=QA 负责人；兼容 UUID 与 open_id）",
    ),
]


def _escape(comment: str) -> str:
    """转义单引号，COMMENT ON 不支持绑定参数（pg8000 下会报 syntax error）。"""
    return comment.replace("'", "''")


def _set_comment(table_name: str, column_name: str, comment: str) -> None:
    op.execute(sa.text(f'COMMENT ON COLUMN {_SCHEMA}."{table_name}"."{column_name}" IS \'{_escape(comment)}\''))


def upgrade() -> None:
    """Sync column comments with the ORM model definitions."""
    for table_name, column_name, new_comment, _old_comment in _COMMENT_CHANGES:
        _set_comment(table_name, column_name, new_comment)


def downgrade() -> None:
    """Restore the comments that 0106 / 0107 / 0110 originally wrote."""
    for table_name, column_name, _new_comment, old_comment in _COMMENT_CHANGES:
        _set_comment(table_name, column_name, old_comment)
