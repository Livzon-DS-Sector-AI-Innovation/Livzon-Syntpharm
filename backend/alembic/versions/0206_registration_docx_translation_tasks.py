"""registration docx translation tasks

Revision ID: 0206_registration_docx_translation_tasks
Revises: 0205_registration_docx_translation_files
Create Date: 2026-11-18

历史从「文件级」升级为「任务级」：新增 docx_translation_tasks（一次提交一行），
文件表补 task_id/success/error 并允许失败行 object_key 为空。
同时按 job_ref 回填既有文件行为任务行，保证老数据在任务级列表可见。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0206_registration_docx_translation_tasks"
down_revision: str = "0205_registration_docx_translation_files"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "registration"
_TASKS = "docx_translation_tasks"
_FILES = "docx_translation_files"


def upgrade() -> None:
    op.create_table(
        _TASKS,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("job_ref", sa.String(length=64), nullable=False, comment="任务ID（进程内任务同号）"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="running", comment="状态: running/done/failed"),
        sa.Column("source_count", sa.Integer(), nullable=False, server_default="0", comment="文件总数"),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0", comment="成功文件数"),
        sa.Column("fail_count", sa.Integer(), nullable=False, server_default="0", comment="失败文件数"),
        sa.Column(
            "first_source_filename",
            sa.String(length=500),
            nullable=False,
            server_default="",
            comment="首个原文件名（列表展示）",
        ),
        sa.Column("source_lang", sa.String(length=8), nullable=False, comment="源语言"),
        sa.Column("target_lang", sa.String(length=8), nullable=False, comment="目标语言"),
        sa.Column("mode", sa.String(length=20), nullable=False, comment="输出模式"),
        sa.Column("batch_size", sa.Integer(), nullable=False, server_default="30", comment="每批段落数"),
        sa.Column("elapsed_seconds", sa.Integer(), nullable=False, server_default="0", comment="耗时(秒)"),
        sa.Column(
            "source_keys",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
            comment="原件位置 [{filename,object_key,size}]",
        ),
        sa.Column("error", sa.Text(), nullable=True, comment="任务级错误"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["created_by"], ["identity.users.id"], name="fk_docx_translation_tasks_created_by"),
        sa.ForeignKeyConstraint(["updated_by"], ["identity.users.id"], name="fk_docx_translation_tasks_updated_by"),
        sa.UniqueConstraint("job_ref", name="uq_docx_translation_tasks_job_ref"),
        schema=_SCHEMA,
    )
    op.create_index("ix_docx_translation_tasks_created_at", _TASKS, ["created_at"], schema=_SCHEMA)
    op.create_index("ix_docx_translation_tasks_created_by", _TASKS, ["created_by"], schema=_SCHEMA)

    op.add_column(_FILES, sa.Column("task_id", sa.Uuid(), nullable=True, comment="所属任务ID"), schema=_SCHEMA)
    op.add_column(
        _FILES,
        sa.Column("success", sa.Boolean(), nullable=False, server_default="true", comment="该文件是否翻译成功"),
        schema=_SCHEMA,
    )
    op.add_column(_FILES, sa.Column("error", sa.Text(), nullable=True, comment="失败原因"), schema=_SCHEMA)
    op.alter_column(_FILES, "object_key", existing_type=sa.String(length=500), nullable=True, schema=_SCHEMA)
    op.create_index("ix_docx_translation_files_task_id", _FILES, ["task_id"], schema=_SCHEMA)

    # 回填：按 job_ref 生成任务行，并把旧文件行关联到任务
    op.execute(
        f"""
        INSERT INTO {_SCHEMA}.{_TASKS} (
            id, job_ref, status, source_count, success_count, fail_count,
            first_source_filename, source_lang, target_lang, mode, batch_size,
            elapsed_seconds, source_keys, error,
            created_at, updated_at, created_by, updated_by, is_deleted
        )
        SELECT
            gen_random_uuid(),
            f.job_ref,
            'done',
            count(DISTINCT f.source_filename),
            count(DISTINCT f.source_filename),
            0,
            min(f.source_filename),
            min(f.source_lang),
            min(f.target_lang),
            min(f.mode),
            30,
            0,
            '[]'::jsonb,
            NULL,
            min(f.created_at),
            now(),
            (array_agg(f.created_by ORDER BY f.created_at))[1],
            NULL,
            false
        FROM {_SCHEMA}.{_FILES} f
        WHERE f.is_deleted = false
        GROUP BY f.job_ref
        """
    )
    op.execute(
        f"""
        UPDATE {_SCHEMA}.{_FILES} f
        SET task_id = t.id
        FROM {_SCHEMA}.{_TASKS} t
        WHERE t.job_ref = f.job_ref AND f.task_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_docx_translation_files_task_id", table_name=_FILES, schema=_SCHEMA)
    op.alter_column(_FILES, "object_key", existing_type=sa.String(length=500), nullable=False, schema=_SCHEMA)
    op.drop_column(_FILES, "error", schema=_SCHEMA)
    op.drop_column(_FILES, "success", schema=_SCHEMA)
    op.drop_column(_FILES, "task_id", schema=_SCHEMA)
    op.drop_index("ix_docx_translation_tasks_created_by", table_name=_TASKS, schema=_SCHEMA)
    op.drop_index("ix_docx_translation_tasks_created_at", table_name=_TASKS, schema=_SCHEMA)
    op.drop_table(_TASKS, schema=_SCHEMA)
