"""#219：用户管理列表以 HR 员工档案为人员信息的唯一来源。

覆盖三件事：
- 姓名 / 手机 / 邮箱 / 工号 / 头像在返回前被 HR 值覆盖（本地列只作缺值回退）；
- 「是否在职」按 ``is_current`` 近似，且与账号 ``status`` 分开；
- 关键词搜索能命中 HR 侧命中的人（避免「列表显示新姓名却搜不到」）。
"""

from __future__ import annotations

import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hr.models import EmployeeProfile
from app.platform.identity.models import User

USERS_URL = "/api/v1/identity/users"


def _profile(open_id: str, name: str, **overrides: Any) -> EmployeeProfile:
    payload: dict[str, Any] = {
        "open_id": open_id,
        "name": name,
        "mobile": "13800000000",
        "email": "hr@example.com",
        "enterprise_email": "",
        "employee_no": "HR-001",
        "department_names": ["101车间", "合成工段"],
        "department_path": [{"id": "od-101", "name": "101车间"}],
        "department_ids": ["od-101"],
        "job_title_name": "车间班长",
        "avatar_240": "https://example.com/240.png",
        "is_current": True,
    }
    payload.update(overrides)
    return EmployeeProfile(**payload)


async def _seed(db_session: AsyncSession, suffix: str) -> dict[str, str]:
    """Seed three accounts: in-post with profile, removed profile, no profile at all."""
    active_user = f"hr_active_{suffix}"
    left_user = f"hr_left_{suffix}"
    none_user = f"hr_none_{suffix}"
    db_session.add_all(
        [
            # 本地快照故意写成旧值，用来证明列表展示的是 HR 值而非本地列
            User(
                username=active_user,
                name="本地旧名",
                employee_no=f"OLD-A-{suffix}",
                mobile="13000000000",
                email="local@example.com",
                feishu_open_id=f"ou-active-{suffix}",
            ),
            User(
                username=left_user,
                name="已移出账号",
                employee_no=f"OLD-L-{suffix}",
                feishu_open_id=f"ou-left-{suffix}",
            ),
            User(
                username=none_user,
                name="无档案账号",
                employee_no=f"OLD-N-{suffix}",
                feishu_open_id=f"ou-none-{suffix}",
            ),
            _profile(
                f"ou-active-{suffix}",
                f"HR新名{suffix}",
                employee_no=f"HR-A-{suffix}",
            ),
            _profile(
                f"ou-left-{suffix}",
                f"离职员工{suffix}",
                employee_no=f"HR-L-{suffix}",
                is_current=False,
            ),
        ]
    )
    await db_session.flush()
    return {"active": active_user, "left": left_user, "none": none_user, "suffix": suffix}


async def test_list_users_prefers_hr_profile_fields(client: AsyncClient, db_session: AsyncSession) -> None:
    suffix = uuid.uuid4().hex[:8]
    usernames = await _seed(db_session, suffix)

    resp = await client.get(USERS_URL, params={"limit": 100})
    assert resp.status_code == 200
    items = {row["username"]: row for row in resp.json()["data"]["items"]}

    active = items[usernames["active"]]
    assert active["name"] == f"HR新名{suffix}"
    assert active["mobile"] == "13800000000"
    assert active["email"] == "hr@example.com"
    assert active["employee_no"] == f"HR-A-{suffix}"
    assert active["department"] == "合成工段"
    assert active["position"] == "车间班长"
    assert active["has_profile"] is True
    assert active["employment_status"] == "active"
    assert active["employment_label"] == "在职"

    left = items[usernames["left"]]
    assert left["has_profile"] is True
    assert left["employment_status"] == "left"
    assert left["employment_label"] == "已离职/调出"

    none = items[usernames["none"]]
    assert none["has_profile"] is False
    assert none["employment_status"] is None
    assert none["employment_label"] == "未建档案"


async def test_list_users_keyword_matches_hr_name(client: AsyncClient, db_session: AsyncSession) -> None:
    """本地 name 是旧值，只在 HR 侧命中才算通过。"""
    suffix = uuid.uuid4().hex[:8]
    usernames = await _seed(db_session, suffix)

    resp = await client.get(USERS_URL, params={"keyword": f"HR新名{suffix}"})
    assert resp.status_code == 200
    rows = resp.json()["data"]["items"]
    assert [row["username"] for row in rows] == [usernames["active"]]
