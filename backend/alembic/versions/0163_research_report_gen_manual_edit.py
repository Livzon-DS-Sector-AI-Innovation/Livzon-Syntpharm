"""0163_research_report_gen_manual_edit

站内在线编辑的留痕与来源标记：

1. ``research.rd_report_gen_edits``：逐条记录「改了哪一处、改前是什么、改后是什么」。
   版本表只能回答「哪一版」，回答不了段落级的改动轨迹，而研发报告要能追溯。
2. ``research.rd_report_gen_slots`` 加 ``edit_source`` / ``edited_at``：区分 AI 写入与
   人工修改。不改 ``state`` 的 CHECK——历史数据的 state 语义保持不变，来源用独立列表达，
   存量记录靠 ``server_default='ai'`` 回填，不需要 UPDATE。
3. ``research.rd_report_gen_document_versions.kind`` 放宽到含 ``manual_edit``：
   站内编辑保存后落一个新版本，与人工上传（manual_upload）区分开。

downgrade 说明：回退前必须先把 ``manual_edit`` 版本改成 ``manual_upload`` 或删除，
否则重建旧 CHECK 会失败（迁移不做静默改数据）。
只动 research schema（单模块原则）。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from alembic import op

revision: str = "0163_research_report_gen_manual_edit"
down_revision: str | Sequence[str] | None = "0162_research_template_version_kind"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "research"
_SLOTS = "rd_report_gen_slots"
_VERSIONS = "rd_report_gen_document_versions"
_EDITS = "rd_report_gen_edits"
_JOBS = "rd_report_gen_jobs"

_CK_VERSION_KIND = "ck_research_rd_report_gen_doc_versions_kind"
_CK_EDIT_OPERATION = "ck_research_rd_report_gen_edits_operation"
_INDEX_EDIT_JOB_TIME = "ix_research_rd_report_gen_edits_job_time"


def _base_columns() -> tuple[Any, ...]:
    """BaseModel 公共列：Column 不能挂到多张表上，每次建表都新建实例。"""
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
    op.add_column(
        _SLOTS,
        sa.Column(
            "edit_source",
            sa.String(length=16),
            nullable=False,
            server_default="ai",
            comment="ai=生成写入 / manual=人工修改",
        ),
        schema=_SCHEMA,
    )
    op.add_column(
        _SLOTS,
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True, comment="最近一次人工修改时间"),
        schema=_SCHEMA,
    )

    op.drop_constraint(_CK_VERSION_KIND, _VERSIONS, type_="check", schema=_SCHEMA)
    op.create_check_constraint(
        _CK_VERSION_KIND,
        _VERSIONS,
        "kind IN ('ai_draft', 'manual_render', 'manual_upload', 'manual_edit')",
        schema=_SCHEMA,
    )

    op.create_table(
        _EDITS,
        *_base_columns(),
        sa.Column("job_id", sa.Uuid(), nullable=False, comment="所属生成任务"),
        sa.Column(
            "slot_key",
            sa.String(length=100),
            nullable=False,
            comment="位置标识：p12 / t2r3c1 / ap1 / at1 / ref",
        ),
        sa.Column(
            "operation",
            sa.String(length=32),
            nullable=False,
            comment=(
                "update_text/update_cell/insert_paragraph/delete_paragraph/"
                "append_table_row/delete_table_row"
            ),
        ),
        sa.Column("anchor", sa.JSON(), nullable=True, comment="定位锚点与操作上下文"),
        sa.Column("before_value", sa.Text(), nullable=True, comment="改前内容"),
        sa.Column("after_value", sa.Text(), nullable=True, comment="改后内容"),
        sa.Column("version_id", sa.Uuid(), nullable=True, comment="这次编辑落成的新版本"),
        sa.ForeignKeyConstraint(["job_id"], [f"{_SCHEMA}.{_JOBS}.id"]),
        sa.ForeignKeyConstraint(["version_id"], [f"{_SCHEMA}.{_VERSIONS}.id"]),
        sa.CheckConstraint(
            "operation IN ('update_text', 'update_cell', 'insert_paragraph', 'delete_paragraph',"
            " 'append_table_row', 'delete_table_row')",
            name=_CK_EDIT_OPERATION,
        ),
        schema=_SCHEMA,
        comment="AI 报告人工在线编辑流水（逐条改前改后）",
    )
    op.create_index(_INDEX_EDIT_JOB_TIME, _EDITS, ["job_id", "created_at"], schema=_SCHEMA)


def downgrade() -> None:
    op.drop_index(_INDEX_EDIT_JOB_TIME, table_name=_EDITS, schema=_SCHEMA)
    op.drop_table(_EDITS, schema=_SCHEMA)

    op.drop_constraint(_CK_VERSION_KIND, _VERSIONS, type_="check", schema=_SCHEMA)
    op.create_check_constraint(
        _CK_VERSION_KIND,
        _VERSIONS,
        "kind IN ('ai_draft', 'manual_render', 'manual_upload')",
        schema=_SCHEMA,
    )

    op.drop_column(_SLOTS, "edited_at", schema=_SCHEMA)
    op.drop_column(_SLOTS, "edit_source", schema=_SCHEMA)
