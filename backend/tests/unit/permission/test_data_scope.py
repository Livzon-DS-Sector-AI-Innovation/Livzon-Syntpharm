"""数据范围过滤与单条授权判定的单元测试。

覆盖两个关键语义：
1. 单条授权判定：数据范围只基于「授予目标权限码」的授权，禁止跨授权拼凑。
2. fail-closed：空范围用 false 过滤，绝不变成全量。
"""

import uuid

from sqlalchemy import column, false, select, table

from app.platform.permission.models import (
    SCOPE_ALL,
    SCOPE_DEPARTMENT,
    SCOPE_SELF,
    UserRoleGrant,
)
from app.platform.permission.service.authorization import PermissionContext
from app.platform.permission.service.data_scope import _grant_condition, apply_scope_filter


def _make_grant(scope_type: str, codes: list[str] | None = None) -> UserRoleGrant:
    return UserRoleGrant(
        user_id=uuid.uuid4(),
        role_id=uuid.uuid4(),
        scope_type=scope_type,
        scope_dept_codes=codes,
    )


def _make_ctx(user_id: uuid.UUID, grants: list[UserRoleGrant], is_superuser: bool = False) -> PermissionContext:
    user = type("FakeUser", (), {"id": user_id})()
    return PermissionContext(user=user, permission_code="x", grants=grants, is_superuser=is_superuser)


def test_grant_condition_all_returns_none():
    grant = _make_grant(SCOPE_ALL)
    assert _grant_condition(grant, uuid.uuid4(), column("created_by"), column("dept")) is None


def test_grant_condition_self_filters_by_owner():
    user_id = uuid.uuid4()
    grant = _make_grant(SCOPE_SELF)
    cond = _grant_condition(grant, user_id, column("created_by"), column("dept"))
    assert cond is not None
    assert "created_by" in str(cond)


def test_grant_condition_department_empty_scope_is_fail_closed():
    grant = _make_grant(SCOPE_DEPARTMENT, codes=[])
    cond = _grant_condition(grant, uuid.uuid4(), column("created_by"), column("dept"))
    assert cond is not None
    assert cond.compare(false())


def test_grant_condition_department_with_codes_filters_in():
    grant = _make_grant(SCOPE_DEPARTMENT, codes=["QA", "QC"])
    cond = _grant_condition(grant, uuid.uuid4(), column("created_by"), column("dept"))
    assert cond is not None
    assert "dept" in str(cond)


def test_apply_scope_filter_superuser_unchanged():
    t = table("t", column("created_by"), column("dept"))
    query = select(t)
    user_id = uuid.uuid4()
    ctx = _make_ctx(user_id, [], is_superuser=True)
    assert apply_scope_filter(query, ctx, owner_field=t.c.created_by) is query


def test_apply_scope_filter_empty_grants_fail_closed():
    t = table("t", column("created_by"), column("dept"))
    query = select(t)
    ctx = _make_ctx(uuid.uuid4(), [])
    result = apply_scope_filter(query, ctx, owner_field=t.c.created_by)
    assert result is not query
    assert result.whereclause is not None


def test_apply_scope_filter_any_all_grant_unchanged():
    t = table("t", column("created_by"), column("dept"))
    query = select(t)
    user_id = uuid.uuid4()
    ctx = _make_ctx(user_id, [_make_grant(SCOPE_DEPARTMENT, ["QA"]), _make_grant(SCOPE_ALL)])
    assert apply_scope_filter(query, ctx, owner_field=t.c.created_by, dept_code_field=t.c.dept) is query
