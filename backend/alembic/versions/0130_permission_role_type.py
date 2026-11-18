"""permission: role_type + 活跃授权唯一约束

Revision ID: 0130_permission_role_type
Revises: 0129_safety_cert_personnel_profile_ref
Create Date: 2026-11-18

委派式权限管理（Issue #221）第 1 步：

1. ``permission.roles`` 增加 ``role_type``（system / head / manager / job）。
   - system  = 系统管理员（super_admin，判定直接放行）
   - head    = 模块负责人（内置，本模块全部业务权限 + 模块管理入口）
   - manager = 模块管理人（内置，只持有模块管理入口）
   - job     = 岗位角色 / 全局自定义角色（默认值，存量角色自动落入此类）

2. ``permission.user_role_grants`` 增加「同一人同一角色只有一条活跃授权」的
   部分唯一索引。建索引前先把历史重复行停用（保留最新一条活跃行），
   否则索引创建会失败。停用而不是软删，保留可追溯与可恢复能力。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0130_permission_role_type"
down_revision: str | None = "0129_safety_cert_personnel_profile_ref"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "permission"
_ROLES = "roles"
_GRANTS = "user_role_grants"
_ROLE_TYPE_INDEX = "ix_permission_roles_role_type"
_GRANT_UNIQUE_INDEX = "uq_permission_user_role_grants_active"

# 历史重复授权清洗：同一 (user_id, role_id) 存在多条活跃行时，只保留
# (created_at, id) 最大的那条，其余置为 disabled。幂等，可重复执行。
_DEDUPE_SQL = f"""
UPDATE {_SCHEMA}.{_GRANTS} AS g
SET status = 'disabled'
WHERE g.is_deleted = false
  AND g.status = 'active'
  AND EXISTS (
      SELECT 1
      FROM {_SCHEMA}.{_GRANTS} AS g2
      WHERE g2.user_id = g.user_id
        AND g2.role_id = g.role_id
        AND g2.is_deleted = false
        AND g2.status = 'active'
        AND (g2.created_at, g2.id) > (g.created_at, g.id)
  )
"""


def upgrade() -> None:
    op.add_column(
        _ROLES,
        sa.Column(
            "role_type",
            sa.String(length=32),
            nullable=False,
            server_default="job",
            comment="system / head / manager / job",
        ),
        schema=_SCHEMA,
    )
    op.create_index(_ROLE_TYPE_INDEX, _ROLES, ["role_type"], schema=_SCHEMA)

    op.execute(sa.text(_DEDUPE_SQL))
    op.create_index(
        _GRANT_UNIQUE_INDEX,
        _GRANTS,
        ["user_id", "role_id"],
        unique=True,
        schema=_SCHEMA,
        postgresql_where=sa.text("is_deleted = false AND status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index(_GRANT_UNIQUE_INDEX, table_name=_GRANTS, schema=_SCHEMA)
    op.drop_index(_ROLE_TYPE_INDEX, table_name=_ROLES, schema=_SCHEMA)
    op.drop_column(_ROLES, "role_type", schema=_SCHEMA)
