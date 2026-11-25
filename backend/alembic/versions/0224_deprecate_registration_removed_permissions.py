"""deprecate registration removed permissions

Revision ID: 0224_deprecate_registration_removed_permissions
Revises: 0223_drop_validation_audit_and_supplementary_reply_tables
Create Date: 2026-11-24

「验证审计」「补充回复」两个功能已下线，其权限码与接口绑定已从代码注册表
（app/platform/permission/registry.py）移除。

按 registry 的约定「权限码一经发布不可删除、不可复用，下线只能标记 deprecated」，
本迁移把 DB 镜像表中对应的权限码与接口绑定状态置为 deprecated，保留档案行以便
历史授权记录与操作日志可追溯。`permission.role_permissions` 中的历史关联行保留不动
（权限判定基于内存注册表，且路由已删除，这些码不再指向任何接口，无副作用）。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0224_deprecate_registration_removed_permissions"
down_revision: str | None = "0223_drop_validation_audit_and_supplementary_reply_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DEPRECATED = "deprecated"
_ACTIVE = "active"

_REMOVED_PERMISSION_CODES: tuple[str, ...] = (
    "registration:supplementary-reply:read",
    "registration:supplementary-reply:create",
    "registration:supplementary-reply:delete",
    "registration:validation-audit:read",
    "registration:validation-audit:create",
    "registration:validation-audit:update",
    "registration:validation-audit:delete",
)

_UPDATE_PERMISSIONS = sa.text("UPDATE permission.permissions SET status = :status WHERE code IN :codes").bindparams(
    sa.bindparam("codes", value=[], expanding=True)
)
_UPDATE_API_BINDINGS = sa.text(
    "UPDATE permission.api_bindings SET status = :status WHERE permission_code IN :codes"
).bindparams(sa.bindparam("codes", value=[], expanding=True))


def _set_status(statement: sa.TextClause, status: str) -> None:
    """按权限码批量更新状态（参数化，禁止字符串拼接）。"""
    op.execute(statement.bindparams(status=status, codes=list(_REMOVED_PERMISSION_CODES)))


def upgrade() -> None:
    _set_status(_UPDATE_PERMISSIONS, _DEPRECATED)
    _set_status(_UPDATE_API_BINDINGS, _DEPRECATED)


def downgrade() -> None:
    _set_status(_UPDATE_PERMISSIONS, _ACTIVE)
    _set_status(_UPDATE_API_BINDINGS, _ACTIVE)
