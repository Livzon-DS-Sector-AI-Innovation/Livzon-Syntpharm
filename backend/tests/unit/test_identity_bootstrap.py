# mypy: ignore-errors
"""引导账号 bootstrap：软删不 INSERT、不复活；单条冲突不终止启动。

根因回归（2026-11-21 UAT 事故）：`uq_identity_users_username` 不区分 is_deleted。
旧实现用带软删过滤的 `get_by_username` 判存在，软删账号被判为「不存在」→ INSERT
撞唯一键 → 启动失败 → 容器崩溃循环。本文件钉住修复后的行为。
"""

from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy.exc import IntegrityError

from app.platform.identity import service as identity_service
from app.platform.identity.models import User
from app.platform.identity.service import (
    BOOTSTRAP_ACCOUNT_DELETE_FORBIDDEN,
    bootstrap_local_users,
    is_bootstrap_username,
)


class _FakeNested:
    """模拟 `session.begin_nested()`：异常继续上抛，交由被测算的 except 处理。"""

    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    async def __aenter__(self) -> _FakeNested:
        self._session.savepoints.append("begin")
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        self._session.savepoints.append("rollback" if exc_type else "release")
        return False


class _FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.savepoints: list[str] = []

    async def commit(self) -> None:
        self.commits += 1

    def begin_nested(self) -> _FakeNested:
        return _FakeNested(self)


class _FakeSessionFactory:
    """模拟 `async_session_factory()` 的 async 上下文管理器。"""

    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    def __call__(self) -> _FakeSessionFactory:
        return self

    async def __aenter__(self) -> _FakeSession:
        return self._session

    async def __aexit__(self, *exc: Any) -> bool:
        return False


class _FakeRepo:
    def __init__(self, *, existing: dict[str, User] | None = None, conflict_on: set[str] | None = None) -> None:
        self._existing = existing or {}
        self._conflict_on = conflict_on or set()
        self.lookups: list[str] = []
        self.created: list[str] = []

    async def get_by_username_including_deleted(self, session: Any, username: str) -> User | None:
        self.lookups.append(username)
        return self._existing.get(username.strip().lower())

    async def create(self, session: Any, **kwargs: Any) -> User:
        username = str(kwargs.get("username") or "")
        if username.strip().lower() in self._conflict_on:
            raise IntegrityError("INSERT INTO identity.users", {}, Exception("duplicate key"))
        self.created.append(username)
        return User(name=str(kwargs.get("name") or username), username=username, status="active")


def _settings(*, admin: str = "", user: str = "", force_reset: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        BOOTSTRAP_ADMIN_USERNAME=admin,
        BOOTSTRAP_ADMIN_PASSWORD="admin-pass" if admin else "",
        BOOTSTRAP_ADMIN_NAME="系统管理员",
        BOOTSTRAP_ADMIN_EMAIL="",
        BOOTSTRAP_USER_USERNAME=user,
        BOOTSTRAP_USER_PASSWORD="user-pass" if user else "",
        BOOTSTRAP_USER_NAME="普通用户",
        BOOTSTRAP_USER_EMAIL="",
        BOOTSTRAP_ADMIN_FORCE_RESET=force_reset,
    )


def _user(*, username: str, is_deleted: bool = False, status: str = "active", password_hash: str = "keep") -> User:
    user = User(name=username, username=username, status=status, password_hash=password_hash)
    user.is_deleted = is_deleted
    return user


def _patch(
    monkeypatch: pytest.MonkeyPatch,
    *,
    repo: _FakeRepo,
    session: _FakeSession,
    settings: SimpleNamespace,
) -> None:
    async def fake_system_admin(db: Any) -> None:
        return None

    monkeypatch.setattr(identity_service, "async_session_factory", _FakeSessionFactory(session))
    monkeypatch.setattr(identity_service, "_repo", repo)
    monkeypatch.setattr(identity_service, "get_settings", lambda: settings)
    monkeypatch.setattr(identity_service, "get_or_create_system_admin", fake_system_admin)
    monkeypatch.setattr(identity_service, "hash_password", lambda password: f"hashed:{password}")


def test_is_bootstrap_username_matches_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(identity_service, "get_settings", lambda: _settings(admin="admin", user="user"))

    assert is_bootstrap_username(" ADMIN ") is True
    assert is_bootstrap_username("user") is True
    assert is_bootstrap_username("other") is False
    assert is_bootstrap_username(None) is False
    assert is_bootstrap_username("") is False


def test_is_bootstrap_username_false_when_env_blank(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(identity_service, "get_settings", lambda: _settings())

    assert is_bootstrap_username(" admin ") is False
    assert is_bootstrap_username("") is False


def test_delete_message_is_the_documented_one() -> None:
    assert BOOTSTRAP_ACCOUNT_DELETE_FORBIDDEN == "引导账号不允许删除，请在部署配置中调整 BOOTSTRAP_* 后再操作"


async def test_bootstrap_skips_soft_deleted_without_create(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    soft_deleted = _user(username="admin", is_deleted=True, status="disabled", password_hash="keep")
    repo = _FakeRepo(existing={"admin": soft_deleted})
    session = _FakeSession()
    _patch(monkeypatch, repo=repo, session=session, settings=_settings(admin="admin"))

    with caplog.at_level(logging.INFO, logger=identity_service.__name__):
        await bootstrap_local_users()

    assert repo.lookups == ["admin"]
    assert repo.created == []
    assert soft_deleted.is_deleted is True
    assert soft_deleted.status == "disabled"
    assert soft_deleted.password_hash == "keep"
    assert session.commits == 1

    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 1
    assert warnings[0].bootstrap_username == "admin"
    assert "软删除" in warnings[0].getMessage()


async def test_bootstrap_skips_soft_deleted_even_with_force_reset(monkeypatch: pytest.MonkeyPatch) -> None:
    soft_deleted = _user(username="admin", is_deleted=True, status="disabled", password_hash="keep")
    repo = _FakeRepo(existing={"admin": soft_deleted})
    session = _FakeSession()
    _patch(monkeypatch, repo=repo, session=session, settings=_settings(admin="admin", force_reset=True))
    monkeypatch.setattr(identity_service, "verify_password", lambda password, hashed: False)

    await bootstrap_local_users()

    assert repo.created == []
    assert soft_deleted.is_deleted is True
    assert soft_deleted.status == "disabled"
    assert soft_deleted.password_hash == "keep"
    assert session.commits == 1


async def test_bootstrap_creates_missing_account(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _FakeRepo()
    session = _FakeSession()
    _patch(monkeypatch, repo=repo, session=session, settings=_settings(admin="admin"))

    await bootstrap_local_users()

    assert repo.lookups == ["admin"]
    assert repo.created == ["admin"]
    assert session.savepoints == ["begin", "release"]
    assert session.commits == 1


async def test_bootstrap_integrity_error_does_not_abort_startup(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    repo = _FakeRepo(conflict_on={"admin"})
    session = _FakeSession()
    _patch(monkeypatch, repo=repo, session=session, settings=_settings(admin="admin", user="user"))

    with caplog.at_level(logging.INFO, logger=identity_service.__name__):
        await bootstrap_local_users()

    assert repo.lookups == ["admin", "user"]
    assert repo.created == ["user"]
    assert session.savepoints == ["begin", "rollback", "begin", "release"]
    assert session.commits == 1

    warnings = [r for r in caplog.records if r.levelname == "WARNING" and r.bootstrap_username == "admin"]
    assert len(warnings) == 1
    errors = [r for r in caplog.records if r.levelname == "ERROR" and r.bootstrap_username == "admin"]
    assert len(errors) == 1
    assert errors[0].exc_info is not None


async def test_bootstrap_logs_info_when_existing_disabled(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    existing = _user(username="admin", status="disabled")
    repo = _FakeRepo(existing={"admin": existing})
    session = _FakeSession()
    _patch(monkeypatch, repo=repo, session=session, settings=_settings(admin="admin"))

    with caplog.at_level(logging.INFO, logger=identity_service.__name__):
        await bootstrap_local_users()

    assert repo.created == []
    assert session.commits == 1
    infos = [r for r in caplog.records if r.levelname == "INFO" and r.bootstrap_username == "admin"]
    assert len(infos) == 1
    assert "disabled" in infos[0].getMessage()
