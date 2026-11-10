"""add per-region highlight config to ppt video slide

Revision ID: 0110_agent_ppt_video_slide_highlight_regions
Revises: 0109_agent_ppt_video_slide_highlight_override
Create Date: 2026-11-04

高亮此前只有「整页一套」的粒度（模块设置 + 页级样式覆盖），哪几个区域亮完全由讲稿自动决定，
人工既没法要求「这块只铺底色」，也没法把一个总是亮错的区域排除掉。

所以把粒度下沉到**区域**：`highlight_regions` 存一页的区域三态（不参与 / 文字变色 / 区域铺底色）
与句级微调（这句讲哪些区域、哪些区域这句不亮），布局解析不出的地方用相对整页比例的手绘矩形兜底。

可空、不回填：空 = 走原有的自动判定，旧数据与已出片的画面逐像素不变。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0110_agent_ppt_video_slide_highlight_regions"
down_revision: str = "0109_agent_ppt_video_slide_highlight_override"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "agent"
TABLE = "ppt_video_slide"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column(
            "highlight_regions",
            sa.JSON(),
            nullable=True,
            comment="区域级高亮配置 {regions[],sentences[]}；空=按讲稿自动判定",
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column(TABLE, "highlight_regions", schema=SCHEMA)
