"""#219：个人中心 ``/identity/me`` 以 HR 员工档案为人员信息来源。

覆盖三件事：
- HR 有值时覆盖账号快照（姓名 / 手机 / 邮箱 / 工号 / 部门 / 职位 / 头像）；
- HR 档案存在但字段为空（如部门尚未同步）时逐字段回退账号快照，不能被空值清空；
- 无档案 / 档案已移出 / 无飞书 open_id 时保持账号快照。
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any, cast

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.hr.models import EmployeeProfile
from app.platform.identity.deps import get_current_user
from app.platform.identity.models import User

ME_URL = "/api/v1/identity/me"


def _profile(open_id: str, **overrides: Any) -> EmployeeProfile:
    """构造一条完整字段的 HR 在任档案，避免依赖数据库 server_default。"""
    payload: dict[str, Any] = {
        "open_id": open_id,
        "name": "HR姓名",
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


def _user(suffix: str, *, open_id: str | None) -> User:
    """本地登录快照故意写成旧值，用来证明 HR 值优先、空值回退。"""
    return User(
        name="本地旧名",
        username=f"me-{suffix}",
        employee_no=f"LOCAL-{suffix}",
        mobile="13000000000",
        email="local@example.com",
        department="本地部门",
        position="本地职位",
        avatar_url="https://example.com/local.png",
        feishu_open_id=open_id,
    )


async def _get_me(db_session: AsyncSession, user: User) -> dict[str, Any]:
    """用指定账号调用 /identity/me（只覆盖本次用例的依赖）。"""
    from app.main import app as fastapi_app

    # mypy 把 ``app`` 解析成包名，这里显式还原成 FastAPI 实例
    application = cast(FastAPI, fastapi_app)

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    async def _override_get_current_user() -> User | None:
        return user

    application.dependency_overrides[get_db] = _override_get_db
    application.dependency_overrides[get_current_user] = _override_get_current_user
    try:
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(ME_URL)
    finally:
        application.dependency_overrides.clear()

    assert resp.status_code == 200
    return cast(dict[str, Any], resp.json()["data"])


async def test_me_prefers_hr_profile_fields(db_session: AsyncSession) -> None:
    suffix = uuid.uuid4().hex[:8]
    user = _user(suffix, open_id=f"ou-me-{suffix}")
    db_session.add_all([user, _profile(f"ou-me-{suffix}", employee_no=f"HR-{suffix}")])
    await db_session.flush()

    data = await _get_me(db_session, user)

    assert data["name"] == "HR姓名"
    assert data["mobile"] == "13800000000"
    assert data["email"] == "hr@example.com"
    assert data["employee_no"] == f"HR-{suffix}"
    # 多部门取叶子部门，与用户管理列表口径一致
    assert data["department"] == "合成工段"
    assert data["position"] == "车间班长"
    assert data["avatar_url"] == "https://example.com/240.png"


async def test_me_falls_back_when_hr_fields_empty(db_session: AsyncSession) -> None:
    """HR 档案存在但部门等字段未同步时，不能被空值覆盖（个人中心显示为空的回归）。"""
    suffix = uuid.uuid4().hex[:8]
    user = _user(suffix, open_id=f"ou-me-empty-{suffix}")
    db_session.add_all(
        [
            user,
            _profile(
                f"ou-me-empty-{suffix}",
                name="",
                mobile="",
                email="",
                employee_no="",
                department_ids=[],
                department_names=[],
                department_path=[],
                job_title_name="",
                avatar_240="",
            ),
        ]
    )
    await db_session.flush()

    data = await _get_me(db_session, user)

    assert data["name"] == "本地旧名"
    assert data["mobile"] == "13000000000"
    assert data["email"] == "local@example.com"
    assert data["employee_no"] == f"LOCAL-{suffix}"
    assert data["department"] == "本地部门"
    assert data["position"] == "本地职位"
    assert data["avatar_url"] == "https://example.com/local.png"


async def test_me_keeps_snapshot_without_current_profile(db_session: AsyncSession) -> None:
    suffix = uuid.uuid4().hex[:8]
    user = _user(suffix, open_id=f"ou-me-left-{suffix}")
    db_session.add_all(
        [
            user,
            _profile(f"ou-me-left-{suffix}", name="已移出员工", is_current=False),
        ]
    )
    await db_session.flush()

    data = await _get_me(db_session, user)

    assert data["name"] == "本地旧名"
    assert data["department"] == "本地部门"
    assert data["position"] == "本地职位"


async def test_me_keeps_snapshot_without_open_id(db_session: AsyncSession) -> None:
    suffix = uuid.uuid4().hex[:8]
    user = _user(suffix, open_id=None)
    db_session.add(user)
    await db_session.flush()

    data = await _get_me(db_session, user)

    assert data["name"] == "本地旧名"
    assert data["department"] == "本地部门"
    assert data["employee_no"] == f"LOCAL-{suffix}"
