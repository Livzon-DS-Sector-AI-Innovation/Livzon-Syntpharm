"""drop core llm_configs owner index

Revision ID: 0190_drop_core_llm_configs_owner_index
Revises: 0189_align_agent_ppt_video_drift
Create Date: 2026-11-16

对齐 uat 链遗留漂移：模型已不再声明 ix_core_llm_configs_owner（owner_user_id, visibility）
部分索引，但 uat 链迁移 0103_llm_config_owner_scope 仍会创建它。按模型现状删除；
IF EXISTS 保证各环境幂等，只动 core schema。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0190_drop_core_llm_configs_owner_index"
down_revision: str = "0189_align_agent_ppt_video_drift"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS core.ix_core_llm_configs_owner"))


def downgrade() -> None:
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_core_llm_configs_owner "
            "ON core.llm_configs (owner_user_id, visibility) WHERE is_deleted = false"
        )
    )
