"""add llm_model_name to agent.ppt_video_project

Revision ID: 0106_agent_ppt_video_llm_model_name
Revises: 0105_core_llm_config_available_models
Create Date: 2026-11-05

一个 Key 可勾选多个模型后，项目级覆盖不能只记配置 id，还要记「选的是哪一个模型」。

可空、不回填：空表示沿用该配置的默认模型（`core.llm_configs.model_name`），
旧项目行为与之前完全一致。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0106_agent_ppt_video_llm_model_name"
down_revision: str = "0105_core_llm_config_available_models"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "agent"
TABLE = "ppt_video_project"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column(
            "llm_model_name",
            sa.String(length=128),
            nullable=True,
            comment="项目级模型名（该配置清单内）；空=用配置默认模型",
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column(TABLE, "llm_model_name", schema=SCHEMA)