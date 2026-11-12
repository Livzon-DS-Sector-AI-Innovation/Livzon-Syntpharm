"""add owner and visibility scope to core llm configs

Revision ID: 0103_llm_config_owner_scope
Revises: 0102_agent_ppt_video_script_ai
Create Date: 2026-11-03

业务用户需要「用自己的 API Key」，但平台级 LLM 配置对所有有读权限的人可见。
在不破坏现有平台管理语义的前提下，给配置行加两个维度：

- `owner_user_id`：个人配置的归属用户，系统配置为空
- `visibility`   ：system（平台预置，所有人可选）/ personal（仅 owner 可见可用）

历史行一律回填 `visibility='system'`，平台管理端点只读写 system 行，行为完全不变。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0103_llm_config_owner_scope"
down_revision: str = "0102_agent_ppt_video_script_ai"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "core"
TABLE = "llm_configs"


def _column_exists(column_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = :schema AND table_name = :table AND column_name = :column
            """
        ),
        {"schema": SCHEMA, "table": TABLE, "column": column_name},
    )
    return result.scalar() is not None


def upgrade() -> None:
    if not _column_exists("owner_user_id"):
        op.add_column(
            TABLE,
            sa.Column("owner_user_id", sa.UUID(as_uuid=True), nullable=True, comment="个人配置归属用户；系统配置为空"),
            schema=SCHEMA,
        )
    if not _column_exists("visibility"):
        op.add_column(
            TABLE,
            sa.Column(
                "visibility",
                sa.String(length=16),
                nullable=False,
                server_default="system",
                comment="system=平台预置所有人可选；personal=仅 owner 可见可用",
            ),
            schema=SCHEMA,
        )
        # 历史行没有 owner，统一按系统配置处理
        op.execute(sa.text(f"UPDATE {SCHEMA}.{TABLE} SET visibility = 'system' WHERE visibility IS NULL"))

    op.execute(
        sa.text(
            f"CREATE INDEX IF NOT EXISTS ix_core_llm_configs_owner "
            f"ON {SCHEMA}.{TABLE} (owner_user_id, visibility) WHERE is_deleted = false"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS core.ix_core_llm_configs_owner"))
    if _column_exists("visibility"):
        op.drop_column(TABLE, "visibility", schema=SCHEMA)
    if _column_exists("owner_user_id"):
        op.drop_column(TABLE, "owner_user_id", schema=SCHEMA)