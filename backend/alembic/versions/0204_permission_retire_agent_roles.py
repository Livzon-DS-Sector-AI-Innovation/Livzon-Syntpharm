"""permission: 停用已下线模块（agent）的内置角色与授权

Revision ID: 0204_permission_retire_agent_roles
Revises: 0203_permission_role_owner_delegate
Create Date: 2026-11-19

背景（TC-010）：
- 智能体模块已随 ``0035_drop_agent_tables`` 下线，前端也不再挂载该模块，
  但启动同步只做「增/改」，历史上写库的 ``agent:head`` / ``agent:manager``
  一直留在 ``permission.roles`` 里，在权限管理页被当成「智能体的内置角色」；
- 管理口径：智能体模块不设权限，也不该有内置角色。

处理方式：
- 角色置 ``status='disabled'``（不物理删除，保留审计可追溯）；
- 对应授权同步置 disabled —— 生效权限计算本身已过滤 ``Role.status``，
  置 disabled 即断权，保留授权行便于追溯；
- 应用启动时 ``_sync_roles`` 会再次执行同样的退役逻辑（幂等兜底）。

downgrade 不复活数据：角色/授权退役是一次性治理动作，误停用应由管理员
在界面上重新指派，而不是靠回滚把历史授权静默恢复。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0204_permission_retire_agent_roles"
down_revision: str | None = "0203_permission_role_owner_delegate"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 与 app/platform/permission/registry.py 的 RETIRED_MODULE_CODES 保持一致。
_RETIRED_MODULES: tuple[str, ...] = ("agent",)


def upgrade() -> None:
    conn = op.get_bind()

    grant_stmt = sa.text(
        """
        UPDATE permission.user_role_grants
           SET status = 'disabled'
         WHERE status = 'active'
           AND is_deleted = false
           AND role_id IN (
                SELECT id FROM permission.roles
                 WHERE module_code IN :modules
                   AND is_builtin = true
                   AND is_deleted = false
           )
        """
    ).bindparams(sa.bindparam("modules", expanding=True))
    conn.execute(grant_stmt, {"modules": list(_RETIRED_MODULES)})

    role_stmt = sa.text(
        """
        UPDATE permission.roles
           SET status = 'disabled'
         WHERE module_code IN :modules
           AND is_builtin = true
           AND is_deleted = false
           AND status = 'active'
        """
    ).bindparams(sa.bindparam("modules", expanding=True))
    conn.execute(role_stmt, {"modules": list(_RETIRED_MODULES)})


def downgrade() -> None:
    """不恢复：退役角色的授权已失效，恢复应由管理员重新指派。"""
