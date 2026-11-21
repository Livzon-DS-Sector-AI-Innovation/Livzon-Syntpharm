"""permission: 退役「人员查询」权限码（platform:person:lookup）

Revision ID: 0205_permission_retire_person_lookup
Revises: 0204_permission_retire_agent_roles
Create Date: 2026-11-20

背景：
- 该码只为选人下拉（``GET /api/v1/identity/users/lookup``）存在，选人接口已改为
  「登录即可访问」，不再判定任何权限码（注册表中已删除定义，接口转入
  ``registry.EXEMPT_ROUTES``）；
- 原装配关系：模块负责人 / 模块代表内置角色默认持有该码，用于在本模块配置页
  指派代表、新建授权时选人。改为登录即可后，这两个角色不应再夹带平台级码；
- 启动同步只做「增/改」（``_sync_role_permissions``），注册表删掉的码不会自动
  从库里移除，故必须由本迁移清理。

处理方式：
- ``permission.role_permissions``：该码的角色绑定置 ``is_deleted=true``
  （不物理删除，保留审计可追溯；唯一约束含软删行，复活走新行即可）；
- ``permission.permissions``：该码置 ``status='deprecated'``
  （权限目录发布后不可删、只能退役；``_sync_permissions`` 不改 status，不会复活）；
- ``permission.api_bindings``：该路由的绑定置 ``status='deprecated'``
  （注册表已不再声明，保留行用于追溯历史绑定关系）。

不处理权限缓存：已无任何接口判定该码，Redis 里残留一条码不影响判定，随 TTL 淘汰。

downgrade 不复活：退役是一次性治理动作，误删应由管理员在界面上重新授予，
而不是靠回滚把历史绑定静默恢复。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0205_permission_retire_person_lookup"
down_revision: str | None = "0204_permission_retire_agent_roles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 与已退役的 registry 定义保持一致（该常量已从 registry 删除，迁移内自持字面量）
_RETIRED_CODE = "platform:person:lookup"
_RETIRED_ROUTE = ("GET", "/api/v1/identity/users/lookup")


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text(
            """
            UPDATE permission.role_permissions
               SET is_deleted = true
             WHERE permission_code = :code
               AND is_deleted = false
            """
        ),
        {"code": _RETIRED_CODE},
    )

    conn.execute(
        sa.text(
            """
            UPDATE permission.permissions
               SET status = 'deprecated'
             WHERE code = :code
               AND status <> 'deprecated'
            """
        ),
        {"code": _RETIRED_CODE},
    )

    conn.execute(
        sa.text(
            """
            UPDATE permission.api_bindings
               SET status = 'deprecated'
             WHERE method = :method
               AND route_template = :route
               AND is_deleted = false
               AND status <> 'deprecated'
            """
        ),
        {"method": _RETIRED_ROUTE[0], "route": _RETIRED_ROUTE[1]},
    )


def downgrade() -> None:
    """不恢复：退役的权限码与绑定已无判定入口，恢复应由管理员在界面上重新操作。"""
