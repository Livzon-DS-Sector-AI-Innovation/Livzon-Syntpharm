"""Recursive Feishu org fetcher (multi-root, N-level)."""

from __future__ import annotations

from typing import Any

import pytest

from app.modules.hr import org_feishu
from app.modules.hr.org_domain import OrgScope
from app.modules.hr.org_feishu import FeishuOrgDepartmentFetcher


class _FakeClient:
    is_closed = False


class _TreeFetcher(FeishuOrgDepartmentFetcher):
    def __init__(
        self,
        tree: dict[str, list[dict[str, Any]]],
        *,
        roots: list[OrgScope],
        denied: set[str] | None = None,
    ) -> None:
        super().__init__(app_id="cli_x", app_secret="secret", roots=roots, client=_FakeClient())  # type: ignore[arg-type]
        self.tree = tree
        self.denied = denied or set()
        self.calls: list[str] = []

    async def _list_children(self, parent_id: str) -> list[dict[str, Any]]:
        self.calls.append(parent_id)
        if parent_id in self.denied:
            raise RuntimeError(f"飞书接口 /children 返回错误: code=40004, msg=no permission ({parent_id})")
        return list(self.tree.get(parent_id, []))


def _node(department_id: str, name: str) -> dict[str, Any]:
    return {"open_department_id": department_id, "name": name, "order": 0}


async def test_fetch_departments_walks_n_levels_for_two_roots() -> None:
    roots = [
        OrgScope(department_id="od-a", department_name="公司A"),
        OrgScope(department_id="od-b", department_name="公司B"),
    ]
    fetcher = _TreeFetcher(
        {
            "od-a": [_node("od-a1", "A一级")],
            "od-a1": [_node("od-a11", "A二级"), _node("od-a12", "A二级-2")],
            "od-a11": [_node("od-a111", "A三级")],
            "od-b": [_node("od-b1", "B一级")],
        },
        roots=roots,
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
    roots = [OrgScope(department_id="od-a", department_name="公司A")]
    fetcher = _TreeFetcher(
        {
            "od-a": [_node("od-a1", "可见一级"), _node("od-hidden", "不可见一级")],
            "od-hidden": [_node("od-hidden-1", "不可见二级")],
        },
        roots=roots,
        denied={"od-hidden"},
    )

    rows = await fetcher.fetch_departments()

    ids = {row["department_id"] for row in rows}
    assert "od-a1" in ids
    assert "od-hidden" in ids  # the department itself is still mirrored
    assert "od-hidden-1" not in ids


async def test_fetch_departments_fails_when_configured_root_is_invisible() -> None:
    roots = [OrgScope(department_id="od-invisible", department_name="不可见公司")]
    fetcher = _TreeFetcher({}, roots=roots, denied={"od-invisible"})

    with pytest.raises(RuntimeError, match="可见范围"):
        await fetcher.fetch_departments()


async def test_fetch_departments_dedupes_shared_children() -> None:
    roots = [
        OrgScope(department_id="od-a", department_name="公司A"),
        OrgScope(department_id="od-b", department_name="公司B"),
    ]
    fetcher = _TreeFetcher(
        {
            "od-a": [_node("od-shared", "共享部门")],
            "od-b": [_node("od-shared", "共享部门")],
        },
        roots=roots,
    )

    rows = await fetcher.fetch_departments()

    shared = [row for row in rows if row["department_id"] == "od-shared"]
    assert len(shared) == 1


async def test_fetch_departments_stops_at_depth_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(org_feishu, "_MAX_DEPARTMENT_DEPTH", 2)
    roots = [OrgScope(department_id="od-a", department_name="公司A")]
    fetcher = _TreeFetcher(
        {
            "od-a": [_node("od-l1", "L1")],
            "od-l1": [_node("od-l2", "L2")],
            "od-l2": [_node("od-l3", "L3")],
        },
        roots=roots,
    )

    rows = await fetcher.fetch_departments()

    assert {row["department_id"] for row in rows} == {"od-a", "od-l1", "od-l2"}
    assert "od-l2" not in fetcher.calls
