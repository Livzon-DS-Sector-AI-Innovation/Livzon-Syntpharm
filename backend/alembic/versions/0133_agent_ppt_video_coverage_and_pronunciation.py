"""add script coverage to agent.ppt_video_slide and pronunciation_dict to agent.ppt_video_project

Revision ID: 0133_agent_ppt_video_coverage_and_pronunciation
Revises: 0132_agent_ppt_video_highlight_project_default
Create Date: 2026-11-16

两件事一起做（都只涉及 agent schema）：

1. `ppt_video_slide.coverage_*`：AI 讲稿常因段数上限被压成摘要，成片表现为「没讲完就翻页」。
   记录覆盖率与漏讲要点后，前端可以标「可能漏讲」并支持一键补全。
   可空、不回填：旧数据在下次保存/生成时自然补齐。
2. `ppt_video_project.pronunciation_dict`：项目级发音词典（原文 → 合成替代文本）。
   可空：空表示只用模块级词表。

不修改 layout / 页指纹相关字段，存量项目的换源对齐语义保持不变。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0133_agent_ppt_video_coverage_and_pronunciation"
down_revision: str = "0132_agent_ppt_video_highlight_project_default"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "agent"


def upgrade() -> None:
    op.add_column(
        "ppt_video_slide",
        sa.Column("coverage_score", sa.Float(), nullable=True, comment="讲稿要点覆盖率 0~1；空=尚未检查"),
        schema=SCHEMA,
    )
    op.add_column(
        "ppt_video_slide",
        sa.Column(
            "coverage_missing",
            sa.JSON(),
            nullable=True,
            comment="漏讲要点摘要（阅读顺序，最多 10 条）",
        ),
        schema=SCHEMA,
    )
    op.add_column(
        "ppt_video_slide",
        sa.Column(
            "coverage_checked_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="最近一次覆盖度检查时间",
        ),
        schema=SCHEMA,
    )
    op.add_column(
        "ppt_video_project",
        sa.Column(
            "pronunciation_dict",
            sa.JSON(),
            nullable=True,
            comment="项目级发音词典 {原文: 合成替代文本}；空=只用模块级词表",
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("ppt_video_project", "pronunciation_dict", schema=SCHEMA)
    op.drop_column("ppt_video_slide", "coverage_checked_at", schema=SCHEMA)
    op.drop_column("ppt_video_slide", "coverage_missing", schema=SCHEMA)
    op.drop_column("ppt_video_slide", "coverage_score", schema=SCHEMA)