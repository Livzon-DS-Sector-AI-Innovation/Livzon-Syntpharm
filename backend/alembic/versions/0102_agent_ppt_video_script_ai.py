"""add ai script draft fields to agent ppt video

Revision ID: 0102_agent_ppt_video_script_ai
Revises: 0101_create_agent_schema_and_ppt_video_tables
Create Date: 2026-11-03

上传 PPT 后由 AI 逐页生成讲稿初稿，需要记录项目级生成状态与单页讲稿来源：

- ppt_video_project：script_ai_status / script_ai_error / script_ai_progress
- ppt_video_slide  ：script_source（upload / ai / manual）

只改 agent schema 内两张表，符合单模块迁移原则；历史数据取默认值（idle / 空来源），
前端在 idle 时不展示任何 AI 稿提示，渲染链路不受影响。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0102_agent_ppt_video_script_ai"
down_revision: str = "0101_create_agent_schema_and_ppt_video_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "agent"


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = :schema AND table_name = :table AND column_name = :column
            """
        ),
        {"schema": SCHEMA, "table": table_name, "column": column_name},
    )
    return result.scalar() is not None


def upgrade() -> None:
    project_columns = (
        sa.Column(
            "script_ai_status",
            sa.String(length=16),
            nullable=False,
            server_default="idle",
            comment="AI 讲稿初稿状态: idle/queued/running/done/partial/failed/disabled",
        ),
        sa.Column("script_ai_error", sa.Text(), nullable=True, comment="AI 讲稿初稿最近一次失败原因"),
        sa.Column(
            "script_ai_progress",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="AI 讲稿初稿进度 0~100",
        ),
    )
    for column in project_columns:
        if not _column_exists("ppt_video_project", column.name):
            op.add_column("ppt_video_project", column, schema=SCHEMA)

    if not _column_exists("ppt_video_slide", "script_source"):
        op.add_column(
            "ppt_video_slide",
            sa.Column(
                "script_source",
                sa.String(length=16),
                nullable=False,
                server_default="",
                comment="讲稿来源: upload/ai/manual；空=无讲稿",
            ),
            schema=SCHEMA,
        )


def downgrade() -> None:
    if _column_exists("ppt_video_slide", "script_source"):
        op.drop_column("ppt_video_slide", "script_source", schema=SCHEMA)

    for column_name in ("script_ai_progress", "script_ai_error", "script_ai_status"):
        if _column_exists("ppt_video_project", column_name):
            op.drop_column("ppt_video_project", column_name, schema=SCHEMA)
