"""add per-slide highlight style override to ppt video slide

Revision ID: 0109_agent_ppt_video_slide_highlight_override
Revises: 0108_agent_ppt_video_script_segments
Create Date: 2026-11-03

高亮样式原本只有模块级一套（`AGENT_PPT_VIDEO_HIGHLIGHT_*`），整条视频只能同一种风格。
但一页里既有「必须把字染红」的重点页，也有「压暗描边更清爽」的封面/图表页，
所以把样式与主色的**覆盖**下沉到页级：空 = 跟随模块设置，非空 = 本页单独生效。

两列都可空、都不回填：旧数据行为不变（继续走模块设置），不会因为加列改变已出片的画面。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0109_agent_ppt_video_slide_highlight_override"
down_revision: str = "0108_agent_ppt_video_script_segments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "agent"
TABLE = "ppt_video_slide"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column(
            "highlight_style",
            sa.String(length=16),
            nullable=True,
            comment="覆盖本页视觉引导样式；空=用模块设置",
        ),
        schema=SCHEMA,
    )
    op.add_column(
        TABLE,
        sa.Column(
            "highlight_color",
            sa.String(length=16),
            nullable=True,
            comment="覆盖本页高亮主色 #RRGGBB；空=用模块设置",
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column(TABLE, "highlight_color", schema=SCHEMA)
    op.drop_column(TABLE, "highlight_style", schema=SCHEMA)