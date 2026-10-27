"""权限体系 ORM 模型（permission schema）。

设计要点（对照《权限体系设计对比报告》第六节）：
- 权限目录 permissions：代码注册表为唯一权威，DB 只做只读镜像 + 生命周期登记（发布后不可删、只能退役）。
- 角色 roles：平台角色（super_admin / permission_admin / config_admin）+
  模块角色（{module}:admin/operator/approver/viewer）。
- role_permissions：角色→权限码（纯动作授权，不含数据范围）。
- user_role_grants：用户角色授权，是「单条授权判定」的最小单元——动作权限与数据范围必须落在同一条授权内。
- api_bindings：接口精确绑定登记簿（方法 + 路由模板），未登记受保护接口一律 403。
"""

import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

# 确保 identity.users 表注册（BaseModel 的 created_by/updated_by 外键目标），
# 否则单独 import 本模块时 FK 解析报 NoReferencedTableError
import app.platform.identity.models  # noqa: F401
from app.shared.base_model import BaseModel

# 权限目录状态
PERMISSION_ACTIVE = "active"
PERMISSION_DEPRECATED = "deprecated"

# 角色类别
ROLE_CATEGORY_PLATFORM = "platform"
ROLE_CATEGORY_MODULE = "module"

# 数据范围档位
SCOPE_SELF = "self"
SCOPE_DEPARTMENT = "department"
SCOPE_DEPARTMENT_AND_CHILDREN = "department_and_children"
SCOPE_ALL = "all"

# 授权状态
GRANT_ACTIVE = "active"
GRANT_DISABLED = "disabled"


class Permission(BaseModel):
    """权限目录（登记簿）。代码注册表是唯一权威，本表为只读镜像。"""

    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("code", name="uq_permission_permissions_code"),
        Index("ix_permission_permissions_module", "module"),
        Index("ix_permission_permissions_status", "status"),
        {"schema": "permission"},
    )

    code: Mapped[str] = mapped_column(String(128), nullable=False, comment="权限码：模块:资源:动作")
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="权限名称")
    module: Mapped[str] = mapped_column(String(64), nullable=False, comment="模块编码，如 quality")
    resource: Mapped[str] = mapped_column(String(64), nullable=False, comment="资源编码，如 deviation")
    action: Mapped[str] = mapped_column(String(64), nullable=False, comment="动作编码，如 approve")
    description: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="权限说明")
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=PERMISSION_ACTIVE,
        server_default=PERMISSION_ACTIVE,
        comment="active / deprecated（退役不可删）",
    )
    is_builtin: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="是否内置（代码注册表产生）",
    )


class Role(BaseModel):
    """角色。"""

    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("code", name="uq_permission_roles_code"),
        Index("ix_permission_roles_category", "category"),
        Index("ix_permission_roles_module_code", "module_code"),
        {"schema": "permission"},
    )

    code: Mapped[str] = mapped_column(String(128), nullable=False, comment="角色编码")
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="角色名称")
    category: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="platform / module",
    )
    module_code: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="模块编码（模块角色必填）")
    description: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="角色说明")
    is_builtin: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="是否内置角色",
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="是否超级管理员（判定时直接放行）",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=GRANT_ACTIVE,
        server_default=GRANT_ACTIVE,
        comment="active / disabled",
    )


class RolePermission(BaseModel):
    """角色→权限码关联（纯动作授权，不含数据范围）。"""

    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_code", name="uq_permission_role_permissions"),
        Index("ix_permission_role_permissions_code", "permission_code"),
        {"schema": "permission"},
    )

    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("permission.roles.id"),
        nullable=False,
        comment="角色 ID",
    )
    permission_code: Mapped[str] = mapped_column(String(128), nullable=False, comment="权限码")


class UserRoleGrant(BaseModel):
    """用户角色授权（单条授权判定单元）。

    动作权限（经角色）+ 数据范围必须落在同一条授权内同时满足，
    禁止「先合并所有动作权限、再合并所有数据范围」的交叉组合。
    """

    __tablename__ = "user_role_grants"
    __table_args__ = (
        Index("ix_permission_user_role_grants_user", "user_id"),
        Index("ix_permission_user_role_grants_role", "role_id"),
        Index("ix_permission_user_role_grants_status", "status"),
        {"schema": "permission"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("identity.users.id"),
        nullable=False,
        comment="用户 ID",
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("permission.roles.id"),
        nullable=False,
        comment="角色 ID",
    )
    scope_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=SCOPE_ALL,
        server_default=SCOPE_ALL,
        comment="self / department / department_and_children / all",
    )
    scope_dept_codes: Mapped[list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="数据范围部门编码列表（hr.departments.code），scope_type 为 department* 时有效",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=GRANT_ACTIVE,
        server_default=GRANT_ACTIVE,
        comment="active / disabled",
    )
    granted_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("identity.users.id"),
        nullable=True,
        comment="授权人 ID",
    )
    version: Mapped[int] = mapped_column(
        nullable=False,
        default=1,
        server_default="1",
        comment="授权版本号（并发控制 + 变更失效用）",
    )


class ApiBinding(BaseModel):
    """接口精确绑定登记簿（方法 + 路由模板）。

    受保护前缀下的请求，若 method + route_template 未登记，一律 403（fail-closed 兜底）。
    """

    __tablename__ = "api_bindings"
    __table_args__ = (
        UniqueConstraint("method", "route_template", name="uq_permission_api_bindings_route"),
        Index("ix_permission_api_bindings_code", "permission_code"),
        Index("ix_permission_api_bindings_status", "status"),
        {"schema": "permission"},
    )

    permission_code: Mapped[str] = mapped_column(String(128), nullable=False, comment="绑定的权限码")
    method: Mapped[str] = mapped_column(String(16), nullable=False, comment="HTTP 方法，大写")
    route_template: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        comment="路由模板，如 /api/v1/quality/deviations/{id}",
    )
    scope_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="是否需要在判定时携带数据范围",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=PERMISSION_ACTIVE,
        server_default=PERMISSION_ACTIVE,
        comment="active / deprecated",
    )
