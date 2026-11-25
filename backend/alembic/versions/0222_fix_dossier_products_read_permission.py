"""fix dossier-writer products list permission binding

Revision ID: 0222_fix_dossier_products_read_permission
Revises: 0221_registration_product_registration_numbers
Create Date: 2026-11-24

`GET /api/v1/registration/dossier-writer/products`（申报资料撰写列表）在代码注册表里
被误绑为 `registration:authorization-letter:read`，而同一资源的创建/详情/更新/删除
均为 `registration:dossier:*`。后果是只拥有「申报资料」权限的账号打开列表会被 403，
而只拥有「授权书管理」只读权限的账号反而能看。注册表已修正。

`sync_registry()` 只新增缺失的 (method, route_template) 绑定、不更新已存在行的
permission_code（见 app/platform/permission/service/management.py），因此 DB 镜像表
需要用本迁移同步修正，否则线上仍按旧权限码鉴权。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0222_fix_dossier_products_read_permission"
down_revision: str | None = "0221_registration_product_registration_numbers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_METHOD = "GET"
_ROUTE_TEMPLATE = "/api/v1/registration/dossier-writer/products"
_WRONG_CODE = "registration:authorization-letter:read"
_RIGHT_CODE = "registration:dossier:read"

_UPDATE_BINDING = sa.text(
    "UPDATE permission.api_bindings SET permission_code = :new_code "
    "WHERE method = :method AND route_template = :route_template AND permission_code = :old_code"
)


def _set_permission_code(old_code: str, new_code: str) -> None:
    """参数化更新绑定权限码（禁止字符串拼接）。"""
    op.execute(
        _UPDATE_BINDING.bindparams(
            new_code=new_code,
            method=_METHOD,
            route_template=_ROUTE_TEMPLATE,
            old_code=old_code,
        )
    )


def upgrade() -> None:
    _set_permission_code(_WRONG_CODE, _RIGHT_CODE)


def downgrade() -> None:
    _set_permission_code(_RIGHT_CODE, _WRONG_CODE)
