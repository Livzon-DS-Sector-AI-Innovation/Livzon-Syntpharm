"""permission: roles.sync_locked（内置角色手工接管）

Revision ID: 0131_permission_role_sync_lock
Revises: 0130_permission_role_type
Create Date: 2026-11-18

系统管理员可以手工编辑内置角色（模块负责人 / 模块管理员）的权限。一旦手工编辑，
该角色就退出启动时的「自动扩量」，否则管理员删掉的权限码会在下次重启时被同步补回来。

- ``sync_locked = false``：仍由注册表同步维护（默认）
- ``sync_locked = true`` ：已人工接管，同步跳过；界面可「恢复默认」清除标记

列用 IF NOT EXISTS 语义写入，重复执行不会失败（本仓库存在历史分叉库，容错优先）。
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0131_permission_role_sync_lock"
down_revision: str | None = "0130_permission_role_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "permission"
_ROLES = "roles"


def upgrade() -> None:
    op.execute(
        f"ALTER TABLE {_SCHEMA}.{_ROLES} "
        "ADD COLUMN IF NOT EXISTS sync_locked BOOLEAN NOT NULL DEFAULT false"
    )
    op.execute(
        f"COMMENT ON COLUMN {_SCHEMA}.{_ROLES}.sync_locked IS "
        "'内置角色是否已被人工接管（true 时启动同步不再改动其权限）'"
    )


def downgrade() -> None:
    op.execute(f"ALTER TABLE {_SCHEMA}.{_ROLES} DROP COLUMN IF EXISTS sync_locked")
