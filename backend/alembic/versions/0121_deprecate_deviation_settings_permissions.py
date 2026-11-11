"""deprecate deviation settings permissions

Revision ID: 0121_deprecate_deviation_settings_permissions
Revises: 0120_add_deviation_department_config_tables
Create Date: 2026-11-11

偏差管理改造要求下线旧「偏差流程设置 / 偏差提醒设置」与旧流程、旧报告接口，
代码侧已从 `permission/registry.py` 与 `api/router.py` 移除。

`sync_registry()` 只新增不删除（退役不可复活），因此 DB 镜像里会残留：
- `permission.permissions` 中 4 个 `quality:deviation-settings:*` 权限码
- `permission.role_permissions` 中对应的角色授权
- `permission.api_bindings` 中指向已下线路由的绑定

权限目录查询只过滤 `is_deleted`，因此这里同时置 `is_deleted = true` 与 `status = 'deprecated'`，
让退役权限不再出现在权限管理界面，又不丢失历史行。

台账自身（`/quality/deviation/ledger`、`/quality/deviation/notify`、
`/quality/deviation/weekly-confirmations`、`/quality/department-contacts`）的绑定保持不变。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0121_deprecate_deviation_settings_permissions"
down_revision: str = "0120_add_deviation_department_config_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_RETIRED_PERMISSION_PATTERN = "quality:deviation-settings:%"

# 已下线接口的路由前缀（台账、组织配置、通知与周确认保留）
_RETIRED_ROUTE_PATTERNS = (
    "/api/v1/quality/deviation-flow%",
    "/api/v1/quality/deviation-report%",
    "/api/v1/quality/deviation-settings%",
)

_SET_PERMISSION_FLAGS = sa.text(
    "UPDATE permission.permissions "
    "SET status = :status, is_deleted = :is_deleted, updated_at = now() "
    "WHERE code LIKE :pattern"
)
_SET_ROLE_GRANT_FLAGS = sa.text(
    "UPDATE permission.role_permissions SET is_deleted = :is_deleted, updated_at = now() "
    "WHERE permission_code LIKE :pattern"
)
_SET_BINDING_FLAGS = sa.text(
    "UPDATE permission.api_bindings "
    "SET status = :status, is_deleted = :is_deleted, updated_at = now() "
    "WHERE route_template LIKE :pattern"
)
# 旧偏差子资源绑定：保留 ledger / notify / weekly-confirmations
_SET_LEGACY_DEVIATION_BINDINGS = sa.text(
    "UPDATE permission.api_bindings "
    "SET status = :status, is_deleted = :is_deleted, updated_at = now() "
    "WHERE route_template LIKE '/api/v1/quality/deviation%' "
    "AND route_template NOT LIKE '/api/v1/quality/deviation/ledger%' "
    "AND route_template NOT IN ("
    "  '/api/v1/quality/deviation/notify',"
    "  '/api/v1/quality/deviation/weekly-confirmations'"
    ")"
)


def upgrade() -> None:
    bind = op.get_bind()
    retired = {"pattern": _RETIRED_PERMISSION_PATTERN, "status": "deprecated", "is_deleted": True}
    bind.execute(_SET_PERMISSION_FLAGS, retired)
    bind.execute(_SET_ROLE_GRANT_FLAGS, retired)
    bind.execute(_SET_LEGACY_DEVIATION_BINDINGS, {"status": "deprecated", "is_deleted": True})
    for pattern in _RETIRED_ROUTE_PATTERNS:
        bind.execute(_SET_BINDING_FLAGS, {"pattern": pattern, "status": "deprecated", "is_deleted": True})


def downgrade() -> None:
    """恢复权限码与授权；接口绑定由同步脚本重放即可重建。"""
    bind = op.get_bind()
    active = {"pattern": _RETIRED_PERMISSION_PATTERN, "status": "active", "is_deleted": False}
    bind.execute(_SET_PERMISSION_FLAGS, active)
    bind.execute(_SET_ROLE_GRANT_FLAGS, active)
    bind.execute(_SET_LEGACY_DEVIATION_BINDINGS, {"status": "active", "is_deleted": False})
    for pattern in _RETIRED_ROUTE_PATTERNS:
        bind.execute(_SET_BINDING_FLAGS, {"pattern": pattern, "status": "active", "is_deleted": False})