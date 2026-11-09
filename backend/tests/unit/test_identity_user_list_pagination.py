# mypy: ignore-errors
"""用户管理列表：offset/limit 服务端分页契约。

背景（2026-11-05）：前端用户列表曾经只发一次请求（后端按默认 offset=0/limit=20 返回），
并且把响应里的 total 丢掉，表格于是按 dataSource.length 算页数 → 永远只有 1 页，
第 2 页的账号看不到。本文件守住两件事：

- 接口把 offset/limit 原样透传给 repository（不在中间层被裁掉）；
- 响应 data 里带 total/offset/limit，且 total 是「满足筛选的总行数」而不是「本页行数」。
"""

import uuid
from typing import Any

import pytest

from app.platform.identity import api as identity_api
from app.platform.identity.api import list_users_management
from app.platform.identity.models import User
from app.platform.permission.public_api import PermissionContext


class StubRepo:
    """最小仓库替身：记录分页参数，返回预置的一页数据。"""

    def __init__(self, page: list[User], total: int) -> None:
        self.page = page
        self.total = total
        self.calls: dict[str, Any] = {}

    async def list_users(self, session: Any, **kwargs: Any) -> tuple[list[User], int]:
        self.calls = kwargs
        return self.page, self.total

    async def get_roles_for_users(self, session: Any, user_ids: list[Any]) -> dict[Any, list[str]]:
        return {}


def _user(*, username: str, auth_source: str = "local") -> User:
    """未落库的 User：从 ORM 对象直接 model_validate，布尔/枚举字段必须显式赋值。"""
    user = User(
        name=username,
        username=username,
        status="active",
        auth_source=auth_source,
        must_change_password=False,
    )
    user.id = uuid.uuid4()
    return user


def _ctx(*, is_superuser: bool = True) -> PermissionContext:
    return PermissionContext(
        user=_user(username="root"),
        permission_code="platform:user:read",
        is_superuser=is_superuser,
    )


def _patch(
    monkeypatch: pytest.MonkeyPatch,
    repo: StubRepo,
    *,
    actor_is_superuser: bool = True,
    super_ids: list[Any] | None = None,
) -> None:
    """接管仓库与权限判定（端点内部对权限 public_api 是局部 import，patch 模块属性生效）。"""

    async def fake_is_superuser(db: Any, user: User) -> bool:
        return actor_is_superuser

    async def fake_list_super_ids(db: Any) -> list[Any]:
        return super_ids or []

    monkeypatch.setattr(identity_api, "UserRepository", lambda: repo)
    monkeypatch.setattr("app.platform.permission.public_api.user_is_superuser", fake_is_superuser)
    monkeypatch.setattr("app.platform.permission.public_api.list_superuser_user_ids", fake_list_super_ids)


async def _call(
    *,
    offset: int,
    limit: int,
    ctx: PermissionContext | None = None,
    keyword: str | None = None,
) -> Any:
    """直调端点：Query(...) 默认值不是可用实参，因此所有查询参数都显式传入。"""
    return await list_users_management(
        ctx=ctx or _ctx(),
        keyword=keyword,
        status=None,
        auth_source=None,
        unbound_only=False,
        must_change_password=None,
        offset=offset,
        limit=limit,
        db=object(),
    )


async def test_second_page_passes_offset_and_limit_and_reports_total(monkeypatch: pytest.MonkeyPatch) -> None:
    """第 2 页：offset/limit 必须原样到 repository，响应回显同值并带总行数。"""
    repo = StubRepo([_user(username="u21"), _user(username="u22")], total=22)
    _patch(monkeypatch, repo)

    resp = await _call(offset=20, limit=20)

    assert repo.calls["offset"] == 20
    assert repo.calls["limit"] == 20
    assert resp.data["offset"] == 20
    assert resp.data["limit"] == 20
    # total 是总行数（22），不是本页行数（2）——前端分页器靠它算页数
    assert resp.data["total"] == 22
    assert [item["username"] for item in resp.data["items"]] == ["u21", "u22"]


async def test_first_page_reports_total_beyond_page_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    """第 1 页：页长 20 但总共 22 行时，total 仍须是 22，否则分页器算不出第 2 页。"""
    repo = StubRepo([_user(username=f"u{i:02d}") for i in range(1, 21)], total=22)
    _patch(monkeypatch, repo)

    resp = await _call(offset=0, limit=20)

    assert repo.calls["offset"] == 0
    assert len(resp.data["items"]) == 20
    assert resp.data["total"] == 22


async def test_filters_are_passed_through_together_with_paging(monkeypatch: pytest.MonkeyPatch) -> None:
    """分页参数不能挤掉筛选参数：keyword 与 offset/limit 同时生效。"""
    repo = StubRepo([], total=0)
    _patch(monkeypatch, repo)

    await _call(offset=40, limit=10, keyword="张")

    assert repo.calls["keyword"] == "张"
    assert repo.calls["offset"] == 40
    assert repo.calls["limit"] == 10


async def test_non_superuser_still_hides_superuser_ids_when_paging(monkeypatch: pytest.MonkeyPatch) -> None:
    """非超管翻页时，超管账号排除条件不能被分页参数改动带丢。"""
    super_id = uuid.uuid4()
    repo = StubRepo([], total=0)
    _patch(monkeypatch, repo, actor_is_superuser=False, super_ids=[super_id])

    await _call(offset=20, limit=20, ctx=_ctx(is_superuser=False))

    assert repo.calls["exclude_user_ids"] == [super_id]
    assert repo.calls["offset"] == 20
