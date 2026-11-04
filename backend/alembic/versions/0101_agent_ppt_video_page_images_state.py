"""add page images generation state to ppt video project

Revision ID: 0101_agent_ppt_video_page_images_state
Revises: 0100_agent_ppt_video_page_images
Create Date: 2026-11-03

页图生成是一本一本串行跑的：53 页 PPT 命中 PDF 缓存也要拆图约 170 秒。
只靠 `core.background_jobs` 的 running/done/failed 回答不了「到第几页了」，
所以把进度写在项目行上（与 `script_ai_status/progress` 同一套做法）：

- `page_images_status/progress/done/total/error/job_id`：前端每 2 秒查一次单行就能画出进度条；
- `page_images_renderer`：产出这批页图的渲染管线指纹。字体或转换参数一变，
  旧页图虽然还在对象存储里，但画面是错的，必须重出；
  该列为空串表示「老项目、指纹未知」，一律视为过期。

注意 `page_images_renderer` 的 server_default 故意是空串而不是当前指纹：
存量项目下一次打开（或手动重试）会自动重出一次图，这正是修完字体后期望的行为。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0101_agent_ppt_video_page_images_state"
down_revision: str = "0100_agent_ppt_video_page_images"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "agent"
TABLE = "ppt_video_project"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column(
            "page_images_status",
            sa.String(length=16),
            nullable=False,
            server_default="idle",
            comment="页图生成状态: idle/queued/running/done/failed",
        ),
        schema=SCHEMA,
    )
    op.add_column(
        TABLE,
        sa.Column(
            "page_images_progress",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="页图生成进度 0~100",
        ),
        schema=SCHEMA,
    )
    op.add_column(
        TABLE,
        sa.Column(
            "page_images_done",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="已完成页数（含跳过）",
        ),
        schema=SCHEMA,
    )
    op.add_column(
        TABLE,
        sa.Column(
            "page_images_total",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="本次出图总页数",
        ),
        schema=SCHEMA,
    )
    op.add_column(
        TABLE,
        sa.Column("page_images_error", sa.Text(), nullable=True, comment="页图最近一次失败原因"),
        schema=SCHEMA,
    )
    op.add_column(
        TABLE,
        sa.Column(
            "page_images_job_id",
            sa.UUID(as_uuid=True),
            nullable=True,
            comment="最近一次页图任务的 core.background_jobs.id",
        ),
        schema=SCHEMA,
    )
    op.add_column(
        TABLE,
        sa.Column(
            "page_images_renderer",
            sa.String(length=64),
            nullable=False,
            server_default="",
            comment="产出当前页图的渲染管线指纹；与 render.RENDERER_KEY 不一致即视为过期",
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column(TABLE, "page_images_renderer", schema=SCHEMA)
    op.drop_column(TABLE, "page_images_job_id", schema=SCHEMA)
    op.drop_column(TABLE, "page_images_error", schema=SCHEMA)
    op.drop_column(TABLE, "page_images_total", schema=SCHEMA)
    op.drop_column(TABLE, "page_images_done", schema=SCHEMA)
    op.drop_column(TABLE, "page_images_progress", schema=SCHEMA)
    op.drop_column(TABLE, "page_images_status", schema=SCHEMA)