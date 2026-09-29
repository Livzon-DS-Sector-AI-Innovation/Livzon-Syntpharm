"""0065_align_llm_configs_column_comment

Revision ID: 0065_align_llm_configs_column_comment
Revises: 0064_add_kb_chunks_and_facts
Create Date: 2026-09-28 10:10:00.000000

把 ``core.llm_configs.config_type`` 的列注释对齐到 ORM 模型（``app/core/llm/config.py``）。

背景：模型注释是 ``Config type: text / vision / embedding``，而库中仍是旧文案
``Config type: text (text model) / vision (vision model)``。``app/core/llm/client.py``
在解析向量化配置时确实会查 ``config_type="embedding"``，因此模型文案更准确——
本次把库对齐到模型，而不是反过来删掉模型里更完整的信息。

纯注释变更（``COMMENT ON COLUMN``）：不改类型、可空性与约束，不触数据，可安全回滚。

> 说明：这是本仓库少数触及 ``core`` schema 的迁移（AGENTS 规定 core/platform 级变更
> 需架构负责人审批）。本次内容为纯注释，无结构变更、无数据变更。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0065_align_llm_configs_column_comment"
down_revision: str | Sequence[str] | None = "0064_add_kb_chunks_and_facts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "core"
_TABLE = "llm_configs"
_COLUMN = "config_type"

_OLD_COMMENT = "Config type: text (text model) / vision (vision model)"
_NEW_COMMENT = "Config type: text / vision / embedding"


def upgrade() -> None:
    op.alter_column(
        _TABLE,
        _COLUMN,
        existing_type=sa.String(length=20),
        existing_nullable=False,
        comment=_NEW_COMMENT,
        schema=_SCHEMA,
    )


def downgrade() -> None:
    op.alter_column(
        _TABLE,
        _COLUMN,
        existing_type=sa.String(length=20),
        existing_nullable=False,
        comment=_OLD_COMMENT,
        schema=_SCHEMA,
    )
