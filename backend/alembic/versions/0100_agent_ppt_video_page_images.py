"""add page images version to ppt video project

Revision ID: 0100_agent_ppt_video_page_images
Revises: 0099_agent_ppt_video_script_revision
Create Date: 2026-11-03

页图从「渲染时顺手生成」改为「上传后异步生成」，需要一个字段回答
「现有页图是不是当前这份源的结果」——否则换源后无法判断要不要重转：

- `page_images_version == source_version` 且每页都有图 → 渲染直接复用页面图，
  跳过 soffice 整本转 PDF（这是渲染链路上最贵的一步）；
- 不相等 → 照旧转换，转换结果会按源文件指纹缓存，下次仍能命中。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0100_agent_ppt_video_page_images"
down_revision: str = "0099_agent_ppt_video_script_revision"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "agent"
TABLE = "ppt_video_project"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column(
            "page_images_version",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="已生成页图对应的源版本；等于 source_version 才能跳过重新转换",
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column(TABLE, "page_images_version", schema=SCHEMA)
