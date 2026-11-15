"""0153_research_report_gen_edit_restore_operation

Revision ID: 0153_research_report_gen_edit_restore_operation
Revises: 0152_research_report_gen_opinion_library
Create Date: 2026-11-15 16:50:00.000000

在线编辑新增了「还原为母本原样」（``restore_position``）：编辑流水会把这条操作写进
``research.rd_report_gen_edits.operation``，但 0151 建表时的 CHECK 只列了 6 个操作，
少了它。约束一旦存在，还原操作就会在写流水时触发 CheckViolation（接口报「数据完整性错误」）。

这里把 CHECK 扩到编辑器实际会产出的 7 个操作；``DROP CONSTRAINT IF EXISTS`` 让本迁移
在约束缺失（历史环境漂移）时也能安全执行。

只动 research schema（单模块原则）。
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0153_research_report_gen_edit_restore_operation"
down_revision: str | Sequence[str] | None = "0152_research_report_gen_opinion_library"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "research"
_TABLE = "rd_report_gen_edits"
_CONSTRAINT = "ck_research_rd_report_gen_edits_operation"

_OPERATIONS = (
    "update_text",
    "update_cell",
    "restore_position",
    "insert_paragraph",
    "delete_paragraph",
    "append_table_row",
    "delete_table_row",
)


def _condition() -> str:
    values = ", ".join(f"'{item}'" for item in _OPERATIONS)
    return f"operation IN ({values})"


def upgrade() -> None:
    op.execute(f"ALTER TABLE {_SCHEMA}.{_TABLE} DROP CONSTRAINT IF EXISTS {_CONSTRAINT}")
    op.create_check_constraint(_CONSTRAINT, _TABLE, _condition(), schema=_SCHEMA)


def downgrade() -> None:
    op.drop_constraint(_CONSTRAINT, _TABLE, type_="check", schema=_SCHEMA)
    legacy = ", ".join(f"'{item}'" for item in _OPERATIONS if item != "restore_position")
    op.create_check_constraint(_CONSTRAINT, _TABLE, f"operation IN ({legacy})", schema=_SCHEMA)
