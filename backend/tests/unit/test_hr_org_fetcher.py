"""Recursive Feishu org fetcher: root discovery, multi-root, N levels."""

from __future__ import annotations

from typing import Any

import pytest

from app.modules.hr import org_feishu
from app.modules.hr.org_feishu import FeishuOrgDepartmentFetcher


class _FakeClient:
    is_closed = False


class _TreeFetcher(FeishuOrgDepartmentFetcher):
    def __init__(
        self,
        tree: dict[str, list[dict[str, Any]]],
        *,
        visible_roots: list[str],
        denied: set[str] | None = None,
    ) -> None:
        super().__init__(app_id="cli_x", app_secret="secret", client=_FakeClient())  # type: ignore[arg-type]
        self.tree = tree
        self.visible_roots = visible_roots
        self.denied = denied or set()
        self.calls: list[str] = []

    async def _visible_root_ids(self) -> list[str]:
        return list(self.visible_roots)

    async def _list_children(self, parent_id: str) -> list[dict[str, Any]]:
        self.calls.append(parent_id)
        if parent_id in self.denied:
            raise RuntimeError(f"飞书接口 /children 返回错误: code=40004, msg=no permission ({parent_id})")
        return list(self.tree.get(parent_id, []))


def _node(department_id: str, name: str) -> dict[str, Any]:
    return {"open_department_id": department_id, "name": name, "order": 0}


async def test_fetch_departments_walks_n_levels_for_two_roots() -> None:
    fetcher = _TreeFetcher(
        {
            "od-a": [_node("od-a1", "A一级")],
            "od-a1": [_node("od-a11", "A二级"), _node("od-a12", "A二级-2")],
            "od-a11": [_node("od-a111", "A三级")],
            "od-b": [_node("od-b1", "B一级")],
        },
        visible_roots=["od-a", "od-b"],
    )

    rows = await fetcher.fetch_departments()

    by_id = {row["department_id"]: row for row in rows}
    assert set(by_id) == {"od-a", "od-a1", "od-a11", "od-a12", "od-a111", "od-b", "od-b1"}
    assert by_id["od-a"]["parent_department_id"] is None
    assert by_id["od-a"]["level"] == 0
    assert by_id["od-a1"]["parent_department_id"] == "od-a"
    assert by_id["od-a1"]["level"] == 1
    assert by_id["od-a11"]["level"] == 2
    assert by_id["od-a111"]["level"] == 3
    assert by_id["od-b"]["parent_department_id"] is None
    assert by_id["od-b1"]["level"] == 1


async def test_fetch_departments_skips_invisible_branch() -> None:
    fetcher = _TreeFetcher(
        {
            "od-a": [_node("od-a1", "可见一级"), _node("od-hidden", "不可见一级")],
            "od-hidden": [_node("od-hidden-1", "不可见二级")],
        },
        visible_roots=["od-a"],
        denied={"od-hidden"},
    )

    rows = await fetcher.fetch_departments()

    ids = {row["department_id"] for row in rows}
    assert "od-a1" in ids
    assert "od-hidden" in ids  # the department itself is still mirrored
    assert "od-hidden-1" not in ids


async def test_fetch_departments_fails_when_discovered_root_is_invisible() -> None:
    fetcher = _TreeFetcher({}, visible_roots=["od-invisible"], denied={"od-invisible"})

    with pytest.raises(RuntimeError, match="可见范围"):
        await fetcher.fetch_departments()


async def test_fetch_departments_dedupes_shared_children() -> None:
    fetcher = _TreeFetcher(
        {
            "od-a": [_node("od-shared", "共享部门")],
            "od-b": [_node("od-shared", "共享部门")],
        },
        visible_roots=["od-a", "od-b"],
    )

    rows = await fetcher.fetch_departments()

    shared = [row for row in rows if row["department_id"] == "od-shared"]
    assert len(shared) == 1


async def test_fetch_departments_stops_at_depth_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(org_feishu, "_MAX_DEPARTMENT_DEPTH", 2)
    fetcher = _TreeFetcher(
        {
            "od-a": [_node("od-l1", "L1")],
            "od-l1": [_node("od-l2", "L2")],
            "od-l2": [_node("od-l3", "L3")],
        },
        visible_roots=["od-a"],
    )

    rows = await fetcher.fetch_departments()

    assert {row["department_id"] for row in rows} == {"od-a", "od-l1", "od-l2"}
    assert "od-l2" not in fetcher.calls


class _ScopeFetcher(FeishuOrgDepartmentFetcher):
    def __init__(
        self,
        pages: list[dict[str, Any]],
        *,
        children: dict[str, list[dict[str, Any]]] | None = None,
        error: str | None = None,
    ) -> None:
        super().__init__(app_id="cli_x", app_secret="secret", client=_FakeClient())  # type: ignore[arg-type]
        self.pages = pages
        self.children = children or {}
        self.error = error
        self.calls = 0

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        if self.error and path.endswith("/scopes"):
            raise RuntimeError(self.error)
        page = self.pages[self.calls]
        self.calls += 1
        return page

    async def _list_children(self, parent_id: str) -> list[dict[str, Any]]:
        return list(self.children.get(parent_id, []))


async def test_visible_root_ids_paginates_and_dedupes() -> None:
    fetcher = _ScopeFetcher(
        [
            {"department_ids": ["od-a", "od-b"], "has_more": True, "page_token": "p2"},
            {"department_ids": ["od-b", "od-c", "0"], "has_more": False},
        ]
    )

    roots = await fetcher._visible_root_ids()

    assert roots == ["od-a", "od-b", "od-c"]
    assert fetcher.calls == 2


async def test_visible_root_ids_reports_missing_contact_scope() -> None:
    fetcher = _ScopeFetcher([], error="飞书接口 contact/v3/scopes 返回错误: code=40004, msg=no permission")

    with pytest.raises(RuntimeError, match="通讯录权限范围"):
        await fetcher._visible_root_ids()


async def test_visible_root_ids_falls_back_to_tenant_root_children() -> None:
    fetcher = _ScopeFetcher(
        [{"department_ids": [], "has_more": False}],
        children={"0": [_node("od-a", "A"), _node("od-b", "B")]},
    )

    roots = await fetcher._visible_root_ids()

    assert roots == ["od-a", "od-b"]
