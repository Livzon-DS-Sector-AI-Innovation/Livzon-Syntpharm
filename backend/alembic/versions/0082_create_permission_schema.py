"""create_permission_schema

Revision ID: 0082_create_permission_schema
Revises: 0066_add_knowledge_article_document_fields
Create Date: 2026-10-10

重建权限体系（permission schema）：权限目录、角色、角色权限、用户角色授权、接口绑定登记簿。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0082_create_permission_schema"
down_revision: str | None = "0066_add_knowledge_article_document_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _base_columns() -> list[sa.Column]:
    """BaseModel 通用列。"""
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    ]


def _base_fks() -> list[sa.ForeignKeyConstraint]:
    """BaseModel 的 created_by / updated_by 外键（与模型声明一致）。"""
    return [
        sa.ForeignKeyConstraint(["created_by"], ["identity.users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["identity.users.id"]),
    ]


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS permission")

    # 1. 权限目录（登记簿）
    op.create_table(
        "permissions",
        *_base_columns(),
        sa.Column("code", sa.String(length=128), nullable=False, comment="权限码：模块:资源:动作"),
        sa.Column("name", sa.String(length=200), nullable=False, comment="权限名称"),
        sa.Column("module", sa.String(length=64), nullable=False, comment="模块编码，如 quality"),
        sa.Column("resource", sa.String(length=64), nullable=False, comment="资源编码，如 deviation"),
        sa.Column("action", sa.String(length=64), nullable=False, comment="动作编码，如 approve"),
        sa.Column("description", sa.String(length=500), nullable=True, comment="权限说明"),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'active'"),
            nullable=False,
            comment="active / deprecated（退役不可删）",
        ),
        sa.Column(
            "is_builtin",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
            comment="是否内置（代码注册表产生）",
        ),
        sa.UniqueConstraint("code", name="uq_permission_permissions_code"),
        *_base_fks(),
        schema="permission",
    )
    op.create_index("ix_permission_permissions_module", "permissions", ["module"], schema="permission")
    op.create_index("ix_permission_permissions_status", "permissions", ["status"], schema="permission")

    # 2. 角色
    op.create_table(
        "roles",
        *_base_columns(),
        sa.Column("code", sa.String(length=128), nullable=False, comment="角色编码"),
        sa.Column("name", sa.String(length=200), nullable=False, comment="角色名称"),
        sa.Column("category", sa.String(length=32), nullable=False, comment="platform / module"),
        sa.Column("module_code", sa.String(length=64), nullable=True, comment="模块编码（模块角色必填）"),
        sa.Column("description", sa.String(length=500), nullable=True, comment="角色说明"),
        sa.Column("is_builtin", sa.Boolean(), server_default=sa.text("false"), nullable=False, comment="是否内置角色"),
        sa.Column(
            "is_superuser",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment="是否超级管理员（判定时直接放行）",
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'active'"),
            nullable=False,
            comment="active / disabled",
        ),
        sa.UniqueConstraint("code", name="uq_permission_roles_code"),
        *_base_fks(),
        schema="permission",
    )
    op.create_index("ix_permission_roles_category", "roles", ["category"], schema="permission")
    op.create_index("ix_permission_roles_module_code", "roles", ["module_code"], schema="permission")

    # 3. 角色→权限码关联
    op.create_table(
        "role_permissions",
        *_base_columns(),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False, comment="角色 ID"),
        sa.Column("permission_code", sa.String(length=128), nullable=False, comment="权限码"),
        sa.ForeignKeyConstraint(["role_id"], ["permission.roles.id"]),
        sa.UniqueConstraint("role_id", "permission_code", name="uq_permission_role_permissions"),
        *_base_fks(),
        schema="permission",
    )
    op.create_index("ix_permission_role_permissions_code", "role_permissions", ["permission_code"], schema="permission")

    # 4. 用户角色授权（单条授权判定单元）
    op.create_table(
        "user_role_grants",
        *_base_columns(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, comment="用户 ID"),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False, comment="角色 ID"),
        sa.Column(
            "scope_type",
            sa.String(length=32),
            server_default=sa.text("'all'"),
            nullable=False,
            comment="self / department / department_and_children / all",
        ),
        sa.Column(
            "scope_dept_codes",
            postgresql.JSONB(),
            nullable=True,
            comment="数据范围部门编码列表（hr.departments.code），scope_type 为 department* 时有效",
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'active'"),
            nullable=False,
            comment="active / disabled",
        ),
        sa.Column("granted_by", postgresql.UUID(as_uuid=True), nullable=True, comment="授权人 ID"),
        sa.Column(
            "version",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
            comment="授权版本号（并发控制 + 变更失效用）",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["identity.users.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["permission.roles.id"]),
        sa.ForeignKeyConstraint(["granted_by"], ["identity.users.id"]),
        *_base_fks(),
        schema="permission",
    )
    op.create_index("ix_permission_user_role_grants_user", "user_role_grants", ["user_id"], schema="permission")
    op.create_index("ix_permission_user_role_grants_role", "user_role_grants", ["role_id"], schema="permission")
    op.create_index("ix_permission_user_role_grants_status", "user_role_grants", ["status"], schema="permission")

    # 5. 接口精确绑定登记簿
    op.create_table(
        "api_bindings",
        *_base_columns(),
        sa.Column("permission_code", sa.String(length=128), nullable=False, comment="绑定的权限码"),
        sa.Column("method", sa.String(length=16), nullable=False, comment="HTTP 方法，大写"),
        sa.Column(
            "route_template",
            sa.String(length=256),
            nullable=False,
            comment="路由模板，如 /api/v1/quality/deviations/{id}",
        ),
        sa.Column(
            "scope_required",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment="是否需要在判定时携带数据范围",
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'active'"),
            nullable=False,
            comment="active / deprecated",
        ),
        sa.UniqueConstraint("method", "route_template", name="uq_permission_api_bindings_route"),
        *_base_fks(),
        schema="permission",
    )
    op.create_index("ix_permission_api_bindings_code", "api_bindings", ["permission_code"], schema="permission")
    op.create_index("ix_permission_api_bindings_status", "api_bindings", ["status"], schema="permission")


def downgrade() -> None:
    op.drop_table("api_bindings", schema="permission")
    op.drop_table("user_role_grants", schema="permission")
    op.drop_table("role_permissions", schema="permission")
    op.drop_table("roles", schema="permission")
    op.drop_table("permissions", schema="permission")
    op.execute("DROP SCHEMA IF EXISTS permission")
