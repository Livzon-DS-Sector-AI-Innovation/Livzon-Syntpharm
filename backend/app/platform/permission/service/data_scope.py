"""数据范围过滤（单条授权判定 + fail-closed）。

四档范围：self / department / department_and_children / all。

fail-closed 细则（借鉴 NX）：
- 范围为空（scope_dept_codes 为空）时用 false 条件过滤，绝不跳过过滤（避免「空范围=全量」）。
- 缺少对应归属字段（owner_field / dept_code_field）时拒绝，而非放行。
"""

import uuid
from typing import Any

from sqlalchemy import Select, false, or_

from app.platform.permission.models import (
    SCOPE_ALL,
    SCOPE_DEPARTMENT,
    SCOPE_DEPARTMENT_AND_CHILDREN,
    SCOPE_SELF,
    UserRoleGrant,
)
from app.platform.permission.service.authorization import PermissionContext


def _grant_condition(
    grant: UserRoleGrant,
    user_id: uuid.UUID,
    owner_field: Any,
    dept_code_field: Any,
) -> Any:
    """单条授权生成过滤条件。返回 None 表示「该授权授予全部数据」。"""
    if grant.scope_type == SCOPE_ALL:
        return None

    if grant.scope_type == SCOPE_SELF:
        if owner_field is None:
            return false()
        return owner_field == user_id

    if grant.scope_type in (SCOPE_DEPARTMENT, SCOPE_DEPARTMENT_AND_CHILDREN):
        # V1：department_and_children 暂等价于 department。
        # 原因：hr.departments 是扁平表（无父子字段），树展开待部门树数据源补齐后实现。
        if dept_code_field is None:
            return false()
        codes = grant.scope_dept_codes or []
        if not codes:
            return false()  # fail-closed：空范围不变成全量
        return dept_code_field.in_(codes)

    return false()  # 未知范围类型，拒绝


def apply_scope_filter(
    query: Select,  # type: ignore[type-arg]
    ctx: PermissionContext,
    *,
    owner_field: Any = None,
    dept_code_field: Any = None,
) -> Select:  # type: ignore[type-arg]
    """给查询添加数据范围过滤。

    只基于 ctx.grants（授予目标权限码的授权）的范围做 OR 组合，
    保持「单条授权判定」——禁止跨授权拼凑范围。

    Args:
        query: SQLAlchemy Select 查询对象。
        ctx: require_permission 返回的权限上下文。
        owner_field: 资源归属人字段（用于 self 档），如 Model.created_by。
        dept_code_field: 资源部门编码字段（用于 department 档），如 Model.department_code。
    """
    if ctx.is_superuser or ctx.degraded:
        # 超管直接放行；degraded = 权限表未迁移，保持系统现状（无范围过滤）
        return query

    if not ctx.grants:
        return query.where(false())

    conditions = []
    for grant in ctx.grants:
        cond = _grant_condition(grant, ctx.user.id, owner_field, dept_code_field)
        if cond is None:
            return query  # 任一条授权为 all → 放行全部
        conditions.append(cond)

    if not conditions:
        return query.where(false())
    return query.where(or_(*conditions))
