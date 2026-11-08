"""0119_add_example_source_feedback_promoted

Revision ID: 0119_add_example_source_feedback_promoted
Revises: 0118_add_report_gen_feedback
Create Date: 2026-11-08 16:55:00.000000

``research.rd_report_gen_examples.source`` 的取值增加 ``feedback_promoted``：

P4c 之后示例库多了一条沉淀路径——某条评审意见被后续生成落实、人工认可该槽位写法后，
可以把这次的值收进示例库当 few-shot。原约束只允许 ``manual_edit`` / ``agent_filled``，
不放开就会在写入时被库拒绝。

只改 research schema 的约束（单模块原则）；旧数据不受影响，downgrade 时若已存在
``feedback_promoted`` 行，先把它们回落成 ``manual_edit`` 再收紧约束，避免删约束失败。
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0119_add_example_source_feedback_promoted"
down_revision: str | Sequence[str] | None = "0118_add_report_gen_feedback"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "research"
_TABLE = "rd_report_gen_examples"
_CONSTRAINT = f"ck_{_SCHEMA}_{_TABLE}_source"

_OLD = "source IN ('manual_edit', 'agent_filled')"
_NEW = "source IN ('manual_edit', 'agent_filled', 'feedback_promoted')"


def upgrade() -> None:
    op.drop_constraint(_CONSTRAINT, _TABLE, schema=_SCHEMA, type_="check")
    op.create_check_constraint(_CONSTRAINT, _TABLE, _NEW, schema=_SCHEMA)


def downgrade() -> None:
    op.execute(
        f"UPDATE {_SCHEMA}.{_TABLE} SET source = 'manual_edit' WHERE source = 'feedback_promoted'"
    )
    op.drop_constraint(_CONSTRAINT, _TABLE, schema=_SCHEMA, type_="check")
    op.create_check_constraint(_CONSTRAINT, _TABLE, _OLD, schema=_SCHEMA)
