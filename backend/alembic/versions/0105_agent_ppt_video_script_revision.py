"""create agent ppt video script revision table

Revision ID: 0105_agent_ppt_video_script_revision
Revises: 0104_agent_ppt_video_slide_identity
Create Date: 2026-11-03

讲稿改写与换源都需要「改完能反悔」。不做版本文件，改为一条修订记录同时承担：

- 任务记录：status / progress / error_message / requested_by_name
- 回滚依据：before / after 两份 {slide_uid: script_text} 快照

回滚只回写 `before` 并置 `applied=false`，不删记录，保留审计线索。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0105_agent_ppt_video_script_revision"
down_revision: str = "0104_agent_ppt_video_slide_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "agent"


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(sa.text("SELECT to_regclass(:fq_name)"), {"fq_name": f"{SCHEMA}.{table_name}"})
    return result.scalar() is not None


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    ]


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
    if _table_exists("ppt_video_script_revision"):
        return

    op.create_table(
        "ppt_video_script_revision",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), nullable=False, comment="所属项目"),
        sa.Column(
            "mode",
            sa.String(24),
            nullable=False,
            comment="fill_blank/rewrite_all/rewrite_selected/rewrite_one/source_replace",
        ),
        sa.Column("instruction", sa.Text(), nullable=True, comment="单次临时指令"),
        sa.Column("model_name", sa.String(128), nullable=True, comment="本次实际使用的模型"),
        sa.Column("provider", sa.String(64), nullable=True, comment="模型来源: project/global/active/env"),
        sa.Column("scope", sa.JSON(), nullable=True, comment="影响的 slide_uid 列表"),
        sa.Column("before", sa.JSON(), nullable=True, comment="改写前讲稿快照 {slide_uid: text}"),
        sa.Column("after", sa.JSON(), nullable=True, comment="改写后讲稿快照 {slide_uid: text}"),
        sa.Column("status", sa.String(16), nullable=False, server_default="running", comment="状态"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0", comment="进度 0~100"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="失败原因"),
        sa.Column("source_version", sa.Integer(), nullable=True, comment="换源前的源文件版本号"),
        sa.Column("applied", sa.Boolean(), nullable=False, server_default=sa.text("true"), comment="是否仍生效"),
        sa.Column("requested_by_name", sa.String(100), nullable=True, comment="发起人姓名（展示用）"),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["project_id"],
            [f"{SCHEMA}.ppt_video_project.id"],
            name="ppt_video_script_revision_project_id_fkey",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_agent_ppt_video_script_revision_project",
        "ppt_video_script_revision",
        ["project_id", "created_at"],
        schema=SCHEMA,
        postgresql_where=sa.text("is_deleted = false"),
    )


def downgrade() -> None:
    if _table_exists("ppt_video_script_revision"):
        op.drop_table("ppt_video_script_revision", schema=SCHEMA)