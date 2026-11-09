"""add highlight_style / highlight_color to agent.ppt_video_project

Revision ID: 0113_agent_ppt_video_project_highlight_override
Revises: 0112_agent_ppt_video_llm_model_name
Create Date: 2026-11-05

高亮原来只有「模块设置 + 单页覆盖」两层，项目级无处可配。升为三层后取值顺序是
「单页 > 项目 > 模块」，两列可空即代表「跟随模块设置」，存量项目不回填，
行为与升级前完全一致。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0113_agent_ppt_video_project_highlight_override"
down_revision: str = "0112_agent_ppt_video_llm_model_name"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "agent"
TABLE = "ppt_video_project"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column(
            "highlight_style",
            sa.String(length=16),
            nullable=True,
            comment="项目级高亮样式覆盖；空=用模块设置",
        ),
        schema=SCHEMA,
    )
    op.add_column(
        TABLE,
        sa.Column(
            "highlight_color",
            sa.String(length=16),
            nullable=True,
            comment="项目级高亮主色 #RRGGBB；空=用模块设置",
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column(TABLE, "highlight_color", schema=SCHEMA)
    op.drop_column(TABLE, "highlight_style", schema=SCHEMA)
