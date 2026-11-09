"""switch project highlight switch to project-level semantics

Revision ID: 0109_agent_ppt_video_highlight_project_default
Revises: 0108_agent_ppt_video_highlight_override_enabled
Create Date: 2026-11-09

高亮语义从「不勾选=回落到模块默认」改成「不勾选=整项目成片无高亮，单页可单独开启」。

本迁移只更新两张表的列注释，不回填数据：语义切换后「不勾选」就意味着无高亮，
若把存量项目一律回填 true，会让已经关闭开关的项目被静默打开，与新默认相反。
存量项目若要继续高亮，由使用方在项目设置里自行勾选。

只有注释变化，不改列类型、约束与数据。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0109_agent_ppt_video_highlight_project_default"
down_revision: str = "0108_agent_ppt_video_highlight_override_enabled"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "agent"
PROJECT_TABLE = "ppt_video_project"
SLIDE_TABLE = "ppt_video_slide"
COLUMN = "highlight_override_enabled"

PROJECT_COMMENT = "项目级高亮是否启用；关闭=整项目成片无高亮（样式/颜色保留），单页仍可单独开启"
SLIDE_COMMENT = "本页高亮是否启用；关闭=跟随项目设置（项目也未开启则本页无高亮），样式/颜色保留"
OLD_PROJECT_COMMENT = "项目级高亮是否启用；关闭=样式/颜色保留但不生效，回落到模块设置"
OLD_SLIDE_COMMENT = "本页高亮是否启用；关闭=样式/颜色保留但不生效，回落到项目设置"


def upgrade() -> None:
    for table, comment in ((PROJECT_TABLE, PROJECT_COMMENT), (SLIDE_TABLE, SLIDE_COMMENT)):
        op.alter_column(
            table,
            COLUMN,
            existing_type=sa.Boolean(),
            existing_nullable=False,
            existing_server_default=sa.text("false"),
            comment=comment,
            schema=SCHEMA,
        )


def downgrade() -> None:
    for table, comment in ((PROJECT_TABLE, OLD_PROJECT_COMMENT), (SLIDE_TABLE, OLD_SLIDE_COMMENT)):
        op.alter_column(
            table,
            COLUMN,
            existing_type=sa.Boolean(),
            existing_nullable=False,
            existing_server_default=sa.text("false"),
            comment=comment,
            schema=SCHEMA,
        )
