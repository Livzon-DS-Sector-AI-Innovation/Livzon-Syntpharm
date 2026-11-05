"""add available_models to core.llm_configs

Revision ID: 0105_core_llm_config_available_models
Revises: 0104_agent_ppt_video_slide_highlight_regions
Create Date: 2026-11-05

一个 API Key 往往能调用同一网关下的多个模型（如 qwen-plus / qwen-max），
原先 `model_name` 只存单个值，用户每次换模型都要新增一条重复的 Key。

改为：`available_models` 存该 Key 勾选过的模型清单，`model_name` 保留为默认模型
（清单首项），既有读路径与其它模块不受影响。可空、不回填：空表示只有 `model_name`。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0105_core_llm_config_available_models"
down_revision: str = "0104_agent_ppt_video_slide_highlight_regions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "core"
TABLE = "llm_configs"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column(
            "available_models",
            sa.JSON(),
            nullable=True,
            comment="该配置可选的模型清单；空=只有 model_name（兼容一配置一模型）",
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column(TABLE, "available_models", schema=SCHEMA)