"""add kind/result to agent ppt video job

Revision ID: 0143_agent_ppt_video_job_kind
Revises: 0142_agent_ppt_video_column_comments_and_audit_fk
Create Date: 2026-11-19

解析、换源预览、试听合成原先在 HTTP 请求内同步执行（LibreOffice 最长 180s、
Kokoro 推理秒级），违反「请求内不跑超过 5 秒的操作」。本迁移给任务表加 `kind`
区分任务类别（render/parse/source_preview/audio），加 `result` 承载任务产物
（换源 diff、试听音频地址），并补抢占/去重索引。

仅涉及 agent schema。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0143_agent_ppt_video_job_kind"
down_revision: str = "0142_agent_ppt_video_column_comments_and_audit_fk"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "agent"

KIND_COMMENT = "任务类别（render/parse/source_preview/audio）；决定去重与取消范围"
STAGE_COMMENT = "任务内部阶段（与 kind 不同）：render 走 queued/parse/render/tts/concat/upload/done"


def upgrade() -> None:
    op.add_column(
        "ppt_video_job",
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="render", comment=KIND_COMMENT),
        schema=SCHEMA,
    )
    op.add_column(
        "ppt_video_job",
        sa.Column("payload", sa.JSON(), nullable=True, comment="任务入参（试听的页 uid、换源预览的临时对象 key 等）"),
        schema=SCHEMA,
    )
    op.add_column(
        "ppt_video_job",
        sa.Column("result", sa.JSON(), nullable=True, comment="任务产物（换源预览 diff、试听音频地址等）"),
        schema=SCHEMA,
    )
    op.add_column(
        "ppt_video_project",
        sa.Column(
            "pending_script_text",
            sa.Text(),
            nullable=True,
            comment="待解析任务切分的上传讲稿原文；解析完成后清空",
        ),
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_job",
        "stage",
        existing_type=sa.VARCHAR(length=32),
        comment=STAGE_COMMENT,
        existing_comment="queued/parse/render/tts/concat/upload",
        existing_nullable=False,
        existing_server_default=sa.text("'queued'::character varying"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_agent_ppt_video_job_claim",
        "ppt_video_job",
        ["kind", "status", "created_at"],
        schema=SCHEMA,
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "ix_agent_ppt_video_job_dedupe",
        "ppt_video_job",
        ["project_id", "kind", "status"],
        schema=SCHEMA,
        postgresql_where=sa.text("is_deleted = false"),
    )


def downgrade() -> None:
    op.drop_index("ix_agent_ppt_video_job_dedupe", table_name="ppt_video_job", schema=SCHEMA)
    op.drop_index("ix_agent_ppt_video_job_claim", table_name="ppt_video_job", schema=SCHEMA)
    op.alter_column(
        "ppt_video_job",
        "stage",
        existing_type=sa.VARCHAR(length=32),
        comment="queued/parse/render/tts/concat/upload",
        existing_comment=STAGE_COMMENT,
        existing_nullable=False,
        existing_server_default=sa.text("'queued'::character varying"),
        schema=SCHEMA,
    )
    op.drop_column("ppt_video_project", "pending_script_text", schema=SCHEMA)
    op.drop_column("ppt_video_job", "result", schema=SCHEMA)
    op.drop_column("ppt_video_job", "payload", schema=SCHEMA)
    op.drop_column("ppt_video_job", "kind", schema=SCHEMA)
