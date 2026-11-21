"""选人下拉（``/identity/users/lookup``）只返回「HR 在册的系统账号」。

2026-11-20 口径：
- 只列 ``status=active`` 且 HR 档案 ``is_current=true`` 的账号；
- 已离职/调出（历史档案）与无 HR 档案的本地账号（admin、测试账号）都不参与选人；
- 准入只要求登录，不再挂 ``platform:person:lookup``（该码已随 0205 退役）。
"""

from __future__ import annotations

import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hr.models import EmployeeProfile
from app.platform.identity.models import User
from app.platform.permission.registry import ALL_PERMISSIONS, API_BINDINGS, EXEMPT_ROUTES

LOOKUP_URL = "/api/v1/identity/users/lookup"
LOOKUP_ROUTE = ("GET", "/api/v1/identity/users/lookup")


def _profile(open_id: str, name: str, **overrides: Any) -> EmployeeProfile:
    payload: dict[str, Any] = {
        "open_id": open_id,
        "name": name,
        "employee_no": "HR-001",
        "department_names": ["101车间"],
        "job_title_name": "车间班长",
        "is_current": True,
    }
    payload.update(overrides)
    return EmployeeProfile(**payload)


async def _seed(db_session: AsyncSession, suffix: str) -> dict[str, str]:
    """种三个账号：在册有档案 / 离职档案 / 完全无档案。"""
    active = f"lookup_active_{suffix}"
    left = f"lookup_left_{suffix}"
    none = f"lookup_none_{suffix}"
    db_session.add_all(
        [
            User(username=active, name=f"在册人员{suffix}", feishu_open_id=f"ou-lk-active-{suffix}"),
            User(username=left, name=f"离职人员{suffix}", feishu_open_id=f"ou-lk-left-{suffix}"),
            User(username=none, name=f"无档案人员{suffix}", feishu_open_id=f"ou-lk-none-{suffix}"),
            _profile(f"ou-lk-active-{suffix}", f"在册人员{suffix}", employee_no=f"HR-A-{suffix}"),
            _profile(
                f"ou-lk-left-{suffix}",
                f"离职人员{suffix}",
                employee_no=f"HR-L-{suffix}",
                is_current=False,
            ),
        ]
    )
    await db_session.flush()
    return {"active": active, "left": left, "none": none}


async def test_lookup_only_returns_in_service_profiles(client: AsyncClient, db_session: AsyncSession) -> None:
    suffix = uuid.uuid4().hex[:10]
    names = await _seed(db_session, suffix)

    resp = await client.get(LOOKUP_URL, params={"keyword": suffix, "limit": 100})
    assert resp.status_code == 200

    data = resp.json()["data"]
    assert [item["username"] for item in data["items"]] == [names["active"]]
    # 计数与分页同口径：总数为过滤后的行数，不是过滤前的命中数
    assert data["total"] == 1


async def test_lookup_total_matches_filtered_page(client: AsyncClient, db_session: AsyncSession) -> None:
    """分页续载依赖 total；过滤条件必须同时作用于 count，否则前端会无限加载。"""
    suffix = uuid.uuid4().hex[:10]
    await _seed(db_session, suffix)

    first = await client.get(LOOKUP_URL, params={"keyword": suffix, "offset": 0, "limit": 1})
    assert first.status_code == 200
    assert len(first.json()["data"]["items"]) == 1
    assert first.json()["data"]["total"] == 1

    second = await client.get(LOOKUP_URL, params={"keyword": suffix, "offset": 1, "limit": 1})
    assert second.json()["data"]["items"] == []
    assert second.json()["data"]["total"] == 1


async def test_lookup_requires_login_only(anonymous_client: AsyncClient) -> None:
    resp = await anonymous_client.get(LOOKUP_URL)
    assert resp.status_code == 401


def test_lookup_route_is_exempt_and_permission_code_retired() -> None:
    """选人下拉只要求登录：路由进豁免清单、不登记绑定，权限码已从注册表删除。"""
    assert LOOKUP_ROUTE in EXEMPT_ROUTES
    assert all(binding.route_template != LOOKUP_ROUTE[1] for binding in API_BINDINGS)
    assert "platform:person:lookup" not in {permission.code for permission in ALL_PERMISSIONS}
