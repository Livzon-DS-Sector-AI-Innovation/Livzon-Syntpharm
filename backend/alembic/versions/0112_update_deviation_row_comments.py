"""deviation_ledger 跨部门行与调查记录列注释同步

JSONB 列本身无 schema 变更：``cross_dept_reviewers`` 行元素扩展逐行审核状态字段
（review_state/approved_by/approved_name/approved_at/opinion），
``investigation_records`` 元素改为结构化四区 + CAPA + 紧急措施 + 记录级附件引用。
本迁移仅同步列注释，防止 autogenerate 误报列注释漂移。

Revision ID: 0112
Revises: 0111
Create Date: 2026-11-12
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0112_update_deviation_row_comments"
down_revision: str | None = "0111_align_deviation_column_comments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_COLUMN_COMMENTS: dict[str, str] = {
    "cross_dept_reviewers": (
        "跨部门审核行 [{department, investigator_ids[], review_state, approved_by, approved_name,"
        " approved_at, opinion}（review_state: pending/approved）]"
    ),
    "investigation_records": (
        "调查记录 [{nonconformity_description, root_cause_analysis, risk_assessment, capa_proposals[],"
        " urgent_measures, attachments[], author_id, author_name, create_time}]，旧记录为 {content}"
    ),
}


def upgrade() -> None:
    for column_name, comment in _COLUMN_COMMENTS.items():
        op.execute(
            sa.text(
                "COMMENT ON COLUMN quality.deviation_ledger."
                f'"{column_name}" IS :comment'
            ).bindparams(comment=comment)
        )


def downgrade() -> None:
    op.execute(
        sa.text(
            "COMMENT ON COLUMN quality.deviation_ledger.\"cross_dept_reviewers\" "
            "IS '跨部门调查人 [{department, investigators[]}]'"
        )
    )
    op.execute(
        sa.text(
            "COMMENT ON COLUMN quality.deviation_ledger.\"investigation_records\" "
            "IS '调查记录 [{content, author_id, author_name, create_time}]'"
        )
    )
