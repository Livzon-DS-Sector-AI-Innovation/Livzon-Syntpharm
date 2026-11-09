"""add script segments to ppt video slide

Revision ID: 0108_agent_ppt_video_script_segments
Revises: 0107_agent_ppt_video_page_images_state
Create Date: 2026-11-03

讲稿从「整页一段」变成「段序列」，每段带它讲到的页面元素 id，这样渲染时：

- 每段单独合成音频 ⇒ 高亮起止 = 音频实测时长，不再按字数估算；
- 段上直接带 targets ⇒ 坐标来自解析结果，模型编不出坐标，也就亮不错。

`script_segments` 可空，且必须满足「各段文本拼起来等于 `script_text`」；渲染前会做这个
一致性校验，不一致（用户手改过讲稿、回滚、换源）就退回字面匹配，不删列也不重算。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0108_agent_ppt_video_script_segments"
down_revision: str = "0107_agent_ppt_video_page_images_state"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "agent"
TABLE = "ppt_video_slide"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column(
            "script_segments",
            sa.JSON(),
            nullable=True,
            comment="段级讲稿 [{text,targets[]}]：拼起来必须等于 script_text",
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column(TABLE, "script_segments", schema=SCHEMA)
