"""permission: 清理已下线「智能体（agent）」模块的权限、内置角色与接口绑定

Revision ID: 0206_permission_cleanup_agent_module
Revises: 0205_permission_retire_person_lookup
Create Date: 2026-11-21

背景：
- 智能体模块已随 ``0035_drop_agent_tables`` 下线，前端不再挂载；``0204`` 只把
  agent 的 4 个内置角色（owner / delegate / head / manager）置 ``disabled``，
  角色行、权限码与接口绑定仍留在库里：
  * 角色管理页不过滤 ``status``，仍显示「智能体负责人 / 智能体代表」；
  * 权限目录仍显示 ``agent:admin:read``（智能体 - 模块管理入口）等 4 条；
  * 接口绑定登记簿仍显示 ``/api/v1/agent/*`` 的历史路由。
- 管理口径：智能体模块不设权限，也不设内置角色（不需要代表 / 负责人）。

处理方式（全部软处理，不物理删除）：
- ``permission.roles``：agent 内置角色 ``is_deleted=true``、``status='disabled'``
  （角色 code 唯一约束不含软删行，agent 已下线、不会再建同名角色）；
- ``permission.user_role_grants``：其授权 ``status='disabled'``（0204 已做，幂等兜底）；
- ``permission.role_permissions``：其权限绑定 ``is_deleted=true``；
- ``permission.permissions``：``module='agent'`` 的权限码置 ``status='deprecated'``
  （注册表已无定义，``_sync_permissions`` 不回写 status，不会复活）；
- ``permission.api_bindings``：``permission_code`` 前缀为 agent 的历史绑定置
  ``status='deprecated'``（注册表已无声明，保留行用于追溯）。

展示侧同时按 ``RETIRED_MODULE_CODES`` 过滤（repository / api），保证未升级
本迁移的环境也不会在界面上看到这些残留。

downgrade 不恢复：退役 / 软删是一次性治理动作，误操作应由管理员在界面上
重新指派，而不是靠回滚把历史授权静默恢复。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0206_permission_cleanup_agent_module"
down_revision: str | None = "0205_permission_retire_person_lookup"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 与 app/platform/permission/registry.py 的 RETIRED_MODULE_CODES 保持一致。
_RETIRED_MODULES: tuple[str, ...] = ("agent",)


def _module_list() -> list[str]:
    return list(_RETIRED_MODULES)


def upgrade() -> None:
    conn = op.get_bind()

    # 1) 授权断权（0204 已处理，幂等兜底）
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
           )
        """
    ).bindparams(sa.bindparam("modules", expanding=True))
    conn.execute(grant_stmt, {"modules": _module_list()})

    # 2) 角色的权限绑定软删（先于角色软删，便于按角色 id 定位）
    role_permission_stmt = sa.text(
        """
        UPDATE permission.role_permissions
           SET is_deleted = true
         WHERE is_deleted = false
           AND role_id IN (
                SELECT id FROM permission.roles
                 WHERE module_code IN :modules
                   AND is_builtin = true
           )
        """
    ).bindparams(sa.bindparam("modules", expanding=True))
    conn.execute(role_permission_stmt, {"modules": _module_list()})

    # 3) 内置角色软删（界面不再展示，保留行用于审计追溯）
    role_stmt = sa.text(
        """
        UPDATE permission.roles
           SET is_deleted = true,
               status = 'disabled'
         WHERE module_code IN :modules
           AND is_builtin = true
           AND is_deleted = false
        """
    ).bindparams(sa.bindparam("modules", expanding=True))
    conn.execute(role_stmt, {"modules": _module_list()})

    # 4) 权限码退役（权限目录发布后不可删、只能退役）
    permission_stmt = sa.text(
        """
        UPDATE permission.permissions
           SET status = 'deprecated'
         WHERE module IN :modules
           AND status <> 'deprecated'
        """
    ).bindparams(sa.bindparam("modules", expanding=True))
    conn.execute(permission_stmt, {"modules": _module_list()})

    # 5) 接口绑定退役（按权限码前缀定位，permission_code 形如 `agent:xxx`）
    binding_stmt = sa.text(
        """
        UPDATE permission.api_bindings
           SET status = 'deprecated'
         WHERE split_part(permission_code, ':', 1) IN :modules
           AND status <> 'deprecated'
           AND is_deleted = false
        """
    ).bindparams(sa.bindparam("modules", expanding=True))
    conn.execute(binding_stmt, {"modules": _module_list()})


def downgrade() -> None:
    """不恢复：退役 / 软删的角色与权限已无判定入口，恢复应由管理员重新指派。"""
