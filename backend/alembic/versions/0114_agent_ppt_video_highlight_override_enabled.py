"""add highlight_override_enabled to ppt_video_project / ppt_video_slide

Revision ID: 0114_agent_ppt_video_highlight_override_enabled
Revises: 0113_agent_ppt_video_project_highlight_override
Create Date: 2026-11-05

高亮升为「单页 > 项目 > 模块」三层后，覆盖值只能靠「空值」表达跟随，用户想
临时关掉本级自定义就必须把已选好的样式/颜色清空。这里补一个独立开关列：
关闭时保留值但不生效，回落到上一级。

存量数据必须回填：只要历史上写过样式或颜色，升级后一律视为已启用，否则升级
瞬间等于把用户既有配置静默关掉，界面上还会显示「未启用」。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0114_agent_ppt_video_highlight_override_enabled"
down_revision: str = "0113_agent_ppt_video_project_highlight_override"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "agent"
PROJECT_TABLE = "ppt_video_project"
SLIDE_TABLE = "ppt_video_slide"
COLUMN = "highlight_override_enabled"
PROJECT_COMMENT = "项目级高亮是否启用；关闭=样式/颜色保留但不生效，回落到模块设置"
SLIDE_COMMENT = "本页高亮是否启用；关闭=样式/颜色保留但不生效，回落到项目设置"


def upgrade() -> None:
    for table, comment in ((PROJECT_TABLE, PROJECT_COMMENT), (SLIDE_TABLE, SLIDE_COMMENT)):
        op.add_column(
            table,
            sa.Column(
                COLUMN,
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
                comment=comment,
            ),
            schema=SCHEMA,
        )
        # 存量回填：配过样式或颜色即视为「已勾选」，行为与升级前一致
        op.execute(
            sa.text(
                f"UPDATE {SCHEMA}.{table} SET {COLUMN} = true "
                "WHERE highlight_style IS NOT NULL OR highlight_color IS NOT NULL"
            )
        )


def downgrade() -> None:
    for table in (SLIDE_TABLE, PROJECT_TABLE):
        op.drop_column(table, COLUMN, schema=SCHEMA)
