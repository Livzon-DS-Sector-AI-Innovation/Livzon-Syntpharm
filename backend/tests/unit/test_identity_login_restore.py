# mypy: ignore-errors
"""软删账号再次飞书登录的复活逻辑。

背景：账号「删除」是软删（`is_deleted=True` + `status=disabled`，飞书字段保留），
但 `identity.users` 的唯一约束不过滤 `is_deleted`。登录链路带 `is_deleted == False`
查询查不到软删行 → 走新建 → 撞 `uq_identity_users_feishu_user_id` → 登录失败。

产品口径（2026-11-19，用户确认）：
- 删除后本人再次飞书登录：原地复活为「活跃但零权限」，需管理员重新授角色；
- 「禁用」仍是硬拦截：`is_deleted=False` + `status=disabled` 不复活，直接拒绝；
- 本地密码账号被删后**不**自动复活，给出「账号已被删除」的明确提示。
"""

import uuid
from typing import Any
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedException
from app.platform.audit.models import AuditLog
from app.platform.identity.models import User
from app.platform.identity.service import (
    AccountDeletedError,
    authenticate_local_user,
    handle_oauth_callback,
)


def _soft_deleted_user(
    open_id: str,
    *,
    auth_source: str = "feishu",
    employee_no: str | None = None,
) -> User:
    return User(
        name="被删用户",
        username=f"YTH9{uuid.uuid4().hex[:6].upper()}",
        feishu_open_id=open_id,
        feishu_user_id=f"on-{open_id}",
        employee_no=employee_no,
        status="disabled",
        auth_source=auth_source,
        is_deleted=True,
    )


async def _count_by_open_id(db_session: AsyncSession, open_id: str) -> int:
    result = await db_session.execute(select(func.count()).select_from(User).where(User.feishu_open_id == open_id))
    return int(result.scalar_one())


async def _restore_audits(db_session: AsyncSession) -> list[AuditLog]:
    result = await db_session.execute(select(AuditLog).where(AuditLog.action == "user.restore"))
    return list(result.scalars().all())


@pytest.fixture
def feishu_login(monkeypatch: pytest.MonkeyPatch):
    """把飞书换取用户信息与通讯录补齐都换成本地假数据。"""

    def _install(open_id: str) -> None:
        fake_oauth = AsyncMock()
        fake_oauth.exchange_code.return_value = {"access_token": "dummy"}
        fake_oauth.get_user_info.return_value = {
            "open_id": open_id,
            "user_id": f"on-{open_id}",
            "name": "被删用户",
        }
        monkeypatch.setattr(
            "app.platform.identity.service.FeishuOAuthClient.from_settings",
            lambda: fake_oauth,
        )
        monkeypatch.setattr(
            "app.platform.identity.service.enrich_user_from_feishu_contact",
            AsyncMock(return_value=None),
        )

    return _install


@pytest.fixture
def grant_revoker(monkeypatch: pytest.MonkeyPatch):
    """接管授权清理，记录调用并按指定数量返回。"""
    calls: list[uuid.UUID] = []

    def _install(revoked: int = 1) -> list[uuid.UUID]:
        async def _fake(db: Any, user_id: uuid.UUID) -> int:
            calls.append(user_id)
            return revoked

        monkeypatch.setattr("app.platform.permission.public_api.revoke_all_user_grants", _fake)
        return calls

    return _install


async def test_soft_deleted_user_revived_on_login(
    db_session: AsyncSession,
    feishu_login,
    grant_revoker,
) -> None:
    user = _soft_deleted_user("ou-revive-login", employee_no="E-REVIVE-1")
    db_session.add(user)
    await db_session.flush()
    original_username = user.username
    grant_revoker(revoked=0)
    feishu_login("ou-revive-login")

    restored, token = await handle_oauth_callback(db_session, "dummy-code")

    assert restored.id == user.id
    assert restored.is_deleted is False
    assert restored.status == "active"
    assert restored.username == original_username
    assert restored.employee_no == "E-REVIVE-1"
    assert restored.last_login_at is not None
    assert token
    # 复用同一行，不新建账号（否则会撞 feishu_user_id 唯一约束）
    assert await _count_by_open_id(db_session, "ou-revive-login") == 1


async def test_revive_clears_grants_and_records_it(
    db_session: AsyncSession,
    feishu_login,
    grant_revoker,
) -> None:
    user = _soft_deleted_user("ou-revive-grants")
    db_session.add(user)
    await db_session.flush()
    calls = grant_revoker(revoked=3)
    feishu_login("ou-revive-grants")

    await handle_oauth_callback(db_session, "dummy-code")

    assert calls == [user.id]
    audits = await _restore_audits(db_session)
    assert len(audits) == 1
    assert audits[0].resource_id == user.id
    assert audits[0].new_value["revoked_grants"] == 3
    assert audits[0].new_value["trigger"] == "feishu_login"


async def test_live_disabled_user_still_rejected(
    db_session: AsyncSession,
    feishu_login,
    grant_revoker,
) -> None:
    user = User(
        name="被禁用用户",
        username="YTH9DISABLED",
        feishu_open_id="ou-live-disabled",
        feishu_user_id="on-ou-live-disabled",
        status="disabled",
        auth_source="feishu",
        is_deleted=False,
    )
    db_session.add(user)
    await db_session.flush()
    calls = grant_revoker()
    feishu_login("ou-live-disabled")

    with pytest.raises(PermissionError):
        await handle_oauth_callback(db_session, "dummy-code")

    assert calls == []  # 禁用不走复活分支，不会清授权
    assert user.is_deleted is False
    assert user.status == "disabled"


async def test_deleted_local_account_is_not_revived(
    db_session: AsyncSession,
    feishu_login,
    grant_revoker,
) -> None:
    user = _soft_deleted_user("ou-deleted-local", auth_source="local")
    db_session.add(user)
    await db_session.flush()
    calls = grant_revoker()
    feishu_login("ou-deleted-local")

    with pytest.raises(AccountDeletedError):
        await handle_oauth_callback(db_session, "dummy-code")

    assert calls == []
    assert user.is_deleted is True
    assert user.status == "disabled"


async def test_revive_is_idempotent(
    db_session: AsyncSession,
    feishu_login,
    grant_revoker,
) -> None:
    user = _soft_deleted_user("ou-revive-twice")
    db_session.add(user)
    await db_session.flush()
    grant_revoker(revoked=1)
    feishu_login("ou-revive-twice")

    await handle_oauth_callback(db_session, "dummy-code")
    await handle_oauth_callback(db_session, "dummy-code")

    assert await _count_by_open_id(db_session, "ou-revive-twice") == 1
    assert user.is_deleted is False
    # 第二次是 live 命中，不再重复写 user.restore
    assert len(await _restore_audits(db_session)) == 1


async def test_soft_deleted_account_cannot_use_password_login(db_session: AsyncSession) -> None:
    user = _soft_deleted_user("ou-password-deleted", auth_source="local")
    db_session.add(user)
    await db_session.flush()

    with pytest.raises(UnauthorizedException):
        await authenticate_local_user(db_session, username=user.username or "", password="whatever")
