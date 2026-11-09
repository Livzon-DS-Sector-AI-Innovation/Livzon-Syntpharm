"""0122_research_report_gen_document_versions

Revision ID: 0122_research_report_gen_document_versions
Revises: 0121_research_stage_deliverable_report_link
Create Date: 2026-11-08 18:00:00.000000

新增 ``research.rd_report_gen_document_versions``：一条记录对应「一版成品 docx」。

背景：AI 出的报告只是初稿，用户改完要能拿回新旧对照。只靠任务上的
``document_object_key`` 无法回溯——重新渲染或上传一覆盖，AI 初稿就没了。

版本类型（kind）：
- ``ai_draft``：Agent 首次生成；
- ``manual_render``：用户改完槽位后按当前内容重渲染；
- ``manual_upload``：用户下载改完再传回来的 Word。

回填策略：历史上已有成品的任务补一条 ``ai_draft`` 并置为当前版本。
文件大小与操作人无从得知，留空；UUID 在 Python 侧生成，不依赖
gen_random_uuid()/uuid-ossp 扩展（与 0095 的处理一致）。
只动 research schema（单模块原则）。
"""

from __future__ import annotations

import uuid as uuid_module
from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from alembic import op

revision: str = "0122_research_report_gen_document_versions"
down_revision: str | Sequence[str] | None = "0121_research_stage_deliverable_report_link"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "research"
_TABLE = "rd_report_gen_document_versions"
_JOBS = "rd_report_gen_jobs"

_UQ_NO = f"uq_{_SCHEMA}_rd_report_gen_doc_versions_no"
_CK_KIND = f"ck_{_SCHEMA}_rd_report_gen_doc_versions_kind"
_INDEX_JOB = f"ix_{_SCHEMA}_rd_report_gen_doc_versions_job"
_INDEX_CURRENT = f"ix_{_SCHEMA}_rd_report_gen_doc_versions_current"


def _base_columns() -> tuple[Any, ...]:
    """BaseModel 公共列。每次建表都要新建 Column 实例：Column 不能挂到多张表上。"""
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
    op.create_table(
        _TABLE,
        *_base_columns(),
        sa.Column("job_id", sa.Uuid(), nullable=False, comment="所属生成任务"),
        sa.Column("version_no", sa.Integer(), nullable=False, comment="任务内递增版本号，从 1 起"),
        sa.Column(
            "kind",
            sa.String(length=20),
            nullable=False,
            comment="ai_draft=AI 初稿 / manual_render=按槽位重渲 / manual_upload=人工上传",
        ),
        sa.Column("object_key", sa.String(length=500), nullable=False, comment="docx 存储键"),
        sa.Column(
            "comparison_object_key",
            sa.String(length=500),
            nullable=True,
            comment="同版本对照表存储键（人工上传为空）",
        ),
        sa.Column("file_name", sa.String(length=500), nullable=True, comment="文件名"),
        sa.Column("file_size", sa.Integer(), nullable=True, comment="文件字节数"),
        sa.Column("note", sa.String(length=300), nullable=True, comment="版本说明"),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default="false", comment="是否为当前生效版本"),
        sa.ForeignKeyConstraint(["job_id"], [f"{_SCHEMA}.{_JOBS}.id"]),
        sa.UniqueConstraint("job_id", "version_no", name=_UQ_NO),
        sa.CheckConstraint(
            "kind IN ('ai_draft', 'manual_render', 'manual_upload')",
            name=_CK_KIND,
        ),
        schema=_SCHEMA,
        comment="AI 报告成品文档版本（初稿/人工重渲/人工上传）",
    )
    op.create_index(_INDEX_JOB, _TABLE, ["job_id", "version_no"], schema=_SCHEMA)
    op.create_index(_INDEX_CURRENT, _TABLE, ["job_id", "is_current"], schema=_SCHEMA)

    # 回填：已有成品的任务补一条 ai_draft 并置为当前版本
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            f"""
            SELECT id, document_object_key, comparison_object_key, document_file_name
            FROM {_SCHEMA}.{_JOBS}
            WHERE document_object_key IS NOT NULL
              AND is_deleted = false
            """
        )
    ).fetchall()
    insert_sql = sa.text(
        f"""
        INSERT INTO {_SCHEMA}.{_TABLE}
            (id, job_id, version_no, kind, object_key, comparison_object_key,
             file_name, file_size, note, is_current, is_deleted, created_at, updated_at)
        VALUES
            (:id, :job_id, 1, 'ai_draft', :object_key, :comparison_key,
             :file_name, NULL, 'AI 生成初稿（迁移回填）', true, false, now(), now())
        """
    )
    for row in rows:
        bind.execute(
            insert_sql,
            {
                "id": uuid_module.uuid4(),
                "job_id": row.id,
                "object_key": row.document_object_key,
                "comparison_key": row.comparison_object_key,
                "file_name": row.document_file_name,
            },
        )


def downgrade() -> None:
    op.drop_index(_INDEX_CURRENT, table_name=_TABLE, schema=_SCHEMA)
    op.drop_index(_INDEX_JOB, table_name=_TABLE, schema=_SCHEMA)
    op.drop_table(_TABLE, schema=_SCHEMA)
