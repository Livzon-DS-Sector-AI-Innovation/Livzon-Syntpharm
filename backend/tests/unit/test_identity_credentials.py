# mypy: ignore-errors
"""本地账号凭据：默认用户名分配、随机密码、管理员重置与自助改密。

设计约定（2026-10-14）：
- 飞书首次登录只补用户名，**不**自动发密码；
- 密码由管理员按需随机生成，明文只在响应里返回一次（库里只存哈希）；
- 重置与随机生成都会置 `must_change_password`，强制用户首登后自行修改。
"""

from typing import Any

import pytest
from pydantic import ValidationError

from app.platform.identity import service
from app.platform.identity.models import User
from app.platform.identity.schemas import LocalUserCreate
from app.platform.identity.service import (
    DEFAULT_PASSWORD_LENGTH,
    PASSWORD_ALPHABET,
    change_own_password,
    ensure_default_username,
    generate_random_password,
    hash_password,
    reset_password_by_admin,
    validate_password_strength,
    verify_password,
)


class StubSession:
    """最小 AsyncSession 替身：只记录 commit 次数。"""

    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class StubUserRepository:
    """替身：只实现用户名分配。"""

    def __init__(self) -> None:
        self.prefixes: list[str] = []

    async def allocate_username(self, session: Any, *, prefix: str, max_attempts: int = 20) -> str:
        self.prefixes.append(prefix)
        return f"{prefix}000001"


def _stub_user(password: str | None = None) -> User:
    return User(
        name="张三",
        username="YTH000001",
        password_hash=hash_password(password) if password else None,
    )


# ── 随机密码 ─────────────────────────────────────────────────────────


def test_random_password_length_and_alphabet() -> None:
    password = generate_random_password()

    assert len(password) == DEFAULT_PASSWORD_LENGTH
    assert set(password) <= set(PASSWORD_ALPHABET)


def test_random_password_excludes_ambiguous_characters() -> None:
    """去掉 0/O、1/l/I：管理员口头/手抄初始密码时最容易抄错的就是这几个。"""
    for ambiguous in ("0", "O", "1", "l", "I"):
        assert ambiguous not in PASSWORD_ALPHABET


def test_random_password_is_not_repeated() -> None:
    assert generate_random_password() != generate_random_password()


def test_random_password_falls_back_for_too_short_length() -> None:
    assert len(generate_random_password(3)) == DEFAULT_PASSWORD_LENGTH


# ── 管理员重置 ───────────────────────────────────────────────────────


async def test_reset_by_admin_generates_password_and_flags_user() -> None:
    session = StubSession()
    user = _stub_user()

    generated = await reset_password_by_admin(session, user=user, password=None)

    assert generated
    assert verify_password(generated, user.password_hash)
    assert user.must_change_password is True
    assert user.password_updated_at is not None
    assert session.commits == 1


async def test_reset_by_admin_returns_no_plaintext_for_manual_password() -> None:
    session = StubSession()
    user = _stub_user()

    generated = await reset_password_by_admin(session, user=user, password="Manual#2026")

    assert generated == ""  # 管理员自己填的密码无需回显
    assert verify_password("Manual#2026", user.password_hash)
    assert user.must_change_password is True


# ── 自助改密 ─────────────────────────────────────────────────────────


async def test_change_own_password_clears_forced_flag() -> None:
    session = StubSession()
    old = generate_random_password()
    user = _stub_user(old)
    user.must_change_password = True

    await change_own_password(session, user=user, old_password=old, new_password="NewPass#2026")

    assert verify_password("NewPass#2026", user.password_hash)
    assert verify_password(old, user.password_hash) is False
    assert user.must_change_password is False


async def test_change_own_password_rejects_wrong_old_password() -> None:
    from app.core.exceptions import BadRequestException

    session = StubSession()
    user = _stub_user("OldPass#2026")

    with pytest.raises(BadRequestException):
        await change_own_password(session, user=user, old_password="wrong", new_password="NewPass#2026")

    assert verify_password("OldPass#2026", user.password_hash)
    assert session.commits == 0


async def test_change_own_password_rejects_same_password() -> None:
    from app.core.exceptions import BadRequestException

    session = StubSession()
    user = _stub_user("SamePass#2026")

    with pytest.raises(BadRequestException):
        await change_own_password(session, user=user, old_password="SamePass#2026", new_password="SamePass#2026")


# ── 密码复杂度 ───────────────────────────────────────────────────────


def test_validate_password_strength_accepts_valid() -> None:
    assert validate_password_strength("Abc12345") is None
    assert validate_password_strength("a1b2c3d4e5") is None


def test_validate_password_strength_rejects_too_short() -> None:
    assert validate_password_strength("Ab1") is not None
    assert validate_password_strength("Abc1234") is not None  # 7 位


def test_validate_password_strength_rejects_missing_letter_or_digit() -> None:
    assert validate_password_strength("12345678") is not None  # 纯数字
    assert validate_password_strength("abcdefgh") is not None  # 纯字母


async def test_change_own_password_rejects_weak_password() -> None:
    from app.core.exceptions import BadRequestException

    session = StubSession()
    user = _stub_user("OldPass#2026")

    with pytest.raises(BadRequestException):
        await change_own_password(session, user=user, old_password="OldPass#2026", new_password="12345678")

    assert verify_password("OldPass#2026", user.password_hash)
    assert session.commits == 0


async def test_reset_by_admin_rejects_weak_manual_password() -> None:
    from app.core.exceptions import BadRequestException

    session = StubSession()
    user = _stub_user()

    with pytest.raises(BadRequestException):
        await reset_password_by_admin(session, user=user, password="abcdefgh")

    assert session.commits == 0


# ── 默认用户名 ───────────────────────────────────────────────────────


async def test_ensure_default_username_backfills_missing_username(monkeypatch: pytest.MonkeyPatch) -> None:
    """「先同步、后登录」的账号（只有飞书字段）必须在这里补上用户名。"""
    stub_repo = StubUserRepository()
    monkeypatch.setattr(service, "_repo", stub_repo)

    async def fake_setting(module: str, key: str, default: str = "") -> str:
        assert module == "identity"
        assert key == service.USERNAME_PREFIX_SETTING_KEY
        return "abc"  # 小写配置 → 统一转大写

    monkeypatch.setattr(service, "get_module_setting", fake_setting)

    user = User(name="李四", feishu_open_id="ou_sync_only")

    username = await ensure_default_username(StubSession(), user)

    assert username == "ABC000001"
    assert user.username == "ABC000001"
    assert stub_repo.prefixes == ["ABC"]


async def test_ensure_default_username_keeps_existing_username(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_repo = StubUserRepository()
    monkeypatch.setattr(service, "_repo", stub_repo)

    async def fake_setting(module: str, key: str, default: str = "") -> str:
        return "YTH"

    monkeypatch.setattr(service, "get_module_setting", fake_setting)

    user = User(name="王五", username="YTH000007")

    assert await ensure_default_username(StubSession(), user) == "YTH000007"
    assert stub_repo.prefixes == []  # 已有用户名时不应消耗序列


async def test_resolve_username_prefix_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    async def empty_setting(module: str, key: str, default: str = "") -> str:
        return "   "

    monkeypatch.setattr(service, "get_module_setting", empty_setting)

    assert await service.resolve_username_prefix() == service.DEFAULT_USERNAME_PREFIX


# ── 新建用户的用户名字符集 ────────────────────────────────────────────


def _create_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"username": "zhangsan01", "password": "Abc12345", "name": "张三"}
    payload.update(overrides)
    return payload


def test_local_user_create_accepts_ascii_username() -> None:
    """字母开头 + 字母数字，与飞书自动分配的 YTH000001 同风格。"""
    assert LocalUserCreate(**_create_payload()).username == "zhangsan01"
    assert LocalUserCreate(**_create_payload(username="YTH000001")).username == "YTH000001"


def test_local_user_create_strips_username_before_validation() -> None:
    assert LocalUserCreate(**_create_payload(username="  abc123  ")).username == "abc123"


@pytest.mark.parametrize(
    "username",
    [
        "张三",  # 中文
        "zhang三",  # 中英混排
        "zhang_san",  # 下划线
        "1zhangsan",  # 数字开头（与手机号/工号登录标识歧义）
        "abc-123",  # 连字符
        "a",  # 不足 2 位
        "a" * 65,  # 超过 64 位
    ],
)
def test_local_user_create_rejects_invalid_username(username: str) -> None:
    with pytest.raises(ValidationError):
        LocalUserCreate(**_create_payload(username=username))


async def test_resolve_username_prefix_drops_non_ascii(monkeypatch: pytest.MonkeyPatch) -> None:
    """中文前缀不能生成中文用户名，剩余部分仍可用。"""

    async def chinese_setting(module: str, key: str, default: str = "") -> str:
        return "研01发"

    monkeypatch.setattr(service, "get_module_setting", chinese_setting)

    assert await service.resolve_username_prefix() == "01"


async def test_resolve_username_prefix_falls_back_when_all_non_ascii(monkeypatch: pytest.MonkeyPatch) -> None:
    async def all_chinese_setting(module: str, key: str, default: str = "") -> str:
        return "研发中心"

    monkeypatch.setattr(service, "get_module_setting", all_chinese_setting)

    assert await service.resolve_username_prefix() == service.DEFAULT_USERNAME_PREFIX
