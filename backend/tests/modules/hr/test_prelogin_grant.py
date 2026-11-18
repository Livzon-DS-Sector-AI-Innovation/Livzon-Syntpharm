"""Pre-login permission grant seam (ticket #219).

Permissions stay keyed on ``identity.users.id``, but a role may be granted to an
employee who has never logged in. ``ensure_identity_user`` materialises the
account row from the HR employee profile and must be idempotent so repeated
grants never create duplicate accounts.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.hr.models import EmployeeProfile
from app.platform.identity.models import User
from app.platform.identity.service import ensure_identity_user


def _profile(open_id: str, name: str) -> EmployeeProfile:
    return EmployeeProfile(open_id=open_id, name=name)


async def _users_for(db_session: AsyncSession, open_id: str) -> list[User]:
    result = await db_session.execute(select(User).where(User.feishu_open_id == open_id))
    return list(result.scalars().all())


async def test_ensure_identity_user_creates_minimal_account(db_session: AsyncSession) -> None:
    profile = _profile("ou-never-logged-in", "新员工")
    db_session.add(profile)
    await db_session.flush()

    user = await ensure_identity_user(db_session, profile.id)
    await db_session.flush()

    assert user.id is not None
    assert user.name == "新员工"
    assert user.feishu_open_id == "ou-never-logged-in"
    assert user.auth_source == "feishu"
    assert user.password_hash is None
    assert user.status == "active"
    # A local username is allocated so the account can also use password login.
    assert user.username


async def test_ensure_identity_user_is_idempotent(db_session: AsyncSession) -> None:
    profile = _profile("ou-grant-twice", "重复授权")
    db_session.add(profile)
    await db_session.flush()

    first = await ensure_identity_user(db_session, profile.id)
    second = await ensure_identity_user(db_session, profile.id)
    await db_session.flush()

    assert first.id == second.id
    assert len(await _users_for(db_session, "ou-grant-twice")) == 1


async def test_ensure_identity_user_reuses_an_existing_account(db_session: AsyncSession) -> None:
    db_session.add(User(name="已存在账号", feishu_open_id="ou-existing", auth_source="local"))
    profile = _profile("ou-existing", "HR 姓名")
    db_session.add(profile)
    await db_session.flush()

    user = await ensure_identity_user(db_session, profile.id)
    await db_session.flush()

    assert user.name == "已存在账号"
    assert len(await _users_for(db_session, "ou-existing")) == 1


async def test_ensure_identity_user_rejects_unknown_profile(db_session: AsyncSession) -> None:
    import uuid

    with pytest.raises(AppException):
        await ensure_identity_user(db_session, uuid.uuid4())