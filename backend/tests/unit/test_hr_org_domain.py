"""部门管理 org domain seams (ticket #197).

Seams under test:
1. ``parse_directory_department`` — turns a raw Feishu ``directory/v1/departments/mget``
   payload into mirror fields. Catches: i18n name handling, "0" ids, empty arrays,
   string counts.
2. ``build_org_tree`` — turns mirror rows into a recursive tree per configured
   company root. Catches: missing synthetic roots, deeper levels, hidden rows,
   multi-company filtering, ordering, leader-name fallback "—".
3. ``OrgScopes`` / ``trim_path_to_root`` — any-root checks and invisible-parent
   trimming.

These are pure functions: no DB, no HTTP.
"""

from __future__ import annotations

from app.modules.hr.org_domain import (
    OrgDepartmentRecord,
    OrgScope,
    OrgScopes,
    build_org_tree,
    parse_directory_department,
    select_departments_to_hide,
    trim_path_to_root,
)
from tests.fixtures.org_scope import (
    DEFAULT_ORG_SCOPE,
    DEFAULT_ORG_SCOPES,
    IN_SCOPE_COMPANY_ID,
    IN_SCOPE_COMPANY_NAME,
)


def _mget_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "department_id": "od-level2",
        "parent_department_id": "od-level1",
        "name": {"default_value": "合成工段", "i18n_value": {"zh_cn": "合成工段"}},
        "enabled_status": False,
        "order_weight": "20",
        "leaders": [{"leader_type": 1, "leader_id": "ou-leader-b"}, {"leader_id": "ou-leader-a"}],
        "department_count": {
            "recursive_members_count": "42",
            "direct_members_count": "12",
            "recursive_departments_count": "0",
            "direct_departments_count": "0",
        },
        "department_path_infos": [
            {"department_id": "0", "department_name": {"default_value": "Root"}},
            {
                "department_id": IN_SCOPE_COMPANY_ID,
                "department_name": {"default_value": IN_SCOPE_COMPANY_NAME},
            },
            {"department_id": "od-level1", "department_name": {"default_value": "101车间"}},
            {"department_id": "od-level2", "department_name": {"default_value": "合成工段"}},
        ],
        "data_source": 1,
        "custom_field_values": [],
    }
    payload.update(overrides)
    return payload


def test_parse_directory_department_maps_all_mirror_fields() -> None:
    parsed = parse_directory_department(_mget_payload())

    assert parsed.department_id == "od-level2"
    assert parsed.name == "合成工段"
    assert parsed.parent_department_id == "od-level1"
    assert parsed.enabled_status is False
    assert parsed.order_weight == "20"
    assert parsed.leader_ids == ["ou-leader-b", "ou-leader-a"]
    assert parsed.recursive_members_count == 42
    assert parsed.direct_members_count == 12
    assert parsed.recursive_departments_count == 0
    assert parsed.direct_departments_count == 0
    assert parsed.data_source == 1
    assert parsed.department_path == [
        {"id": IN_SCOPE_COMPANY_ID, "name": IN_SCOPE_COMPANY_NAME},
        {"id": "od-level1", "name": "101车间"},
        {"id": "od-level2", "name": "合成工段"},
    ]
    assert parsed.custom_fields == []


def test_parse_directory_department_tolerates_empty_and_zero_ids() -> None:
    parsed = parse_directory_department(
        {
            "department_id": "0",
            "name": {"default_value": ""},
            "leaders": [],
            "department_count": {
                "recursive_members_count": "",
                "direct_members_count": None,
            },
            "department_path_infos": [],
            "custom_field_values": [],
        }
    )

    assert parsed.department_id is None
    assert parsed.leader_ids == []
    assert parsed.recursive_members_count == 0
    assert parsed.direct_members_count == 0
    assert parsed.department_path == []
    assert parsed.order_weight is None
    assert parsed.enabled_status is None


def _record(
    dept_id: str,
    name: str,
    *,
    parent: str | None,
    order: int = 0,
    hidden: bool = False,
    leaders: list[str] | None = None,
    path: list[dict[str, str]] | None = None,
    level: int | None = None,
) -> OrgDepartmentRecord:
    return OrgDepartmentRecord(
        id=dept_id,
        name=name,
        parent_id=parent,
        level=level,
        order=order,
        order_weight=str(order),
        hidden=hidden,
        leader_ids=leaders or [],
        department_path=path
        or [
            {"id": IN_SCOPE_COMPANY_ID, "name": IN_SCOPE_COMPANY_NAME},
            {"id": dept_id, "name": name},
        ],
        enabled_status=True,
        recursive_members_count=0,
        direct_members_count=0,
        recursive_departments_count=0,
        direct_departments_count=0,
        data_source=1,
        custom_fields=[],
    )


def _root_record() -> OrgDepartmentRecord:
    return _record(
        IN_SCOPE_COMPANY_ID,
        IN_SCOPE_COMPANY_NAME,
        parent=None,
        path=[{"id": IN_SCOPE_COMPANY_ID, "name": IN_SCOPE_COMPANY_NAME}],
        level=0,
    )


def test_build_org_tree_renders_company_and_all_levels() -> None:
    records = [
        _root_record(),
        _record("od-a", "101车间", parent=IN_SCOPE_COMPANY_ID, order=2),
        _record("od-b", "102车间", parent=IN_SCOPE_COMPANY_ID, order=1),
        _record("od-a1", "合成工段", parent="od-a", order=1),
        _record("od-a1x", "更深的组", parent="od-a1"),
        _record("od-other", "珠海市丽珠医药贸易有限公司", parent="0"),
        _record("od-other-1", "贸易一部", parent="od-other"),
    ]

    tree = build_org_tree(records, leader_names={}, scopes=DEFAULT_ORG_SCOPES)

    assert len(tree) == 1
    company = tree[0]
    assert company["id"] == IN_SCOPE_COMPANY_ID
    assert company["level"] == 0
    assert [child["name"] for child in company["children"]] == ["102车间", "101车间"]
    assert company["children"][1]["level"] == 1
    assert [child["name"] for child in company["children"][1]["children"]] == ["合成工段"]
    assert company["children"][1]["children"][0]["level"] == 2
    assert company["children"][1]["children"][0]["children"][0]["name"] == "更深的组"
    assert company["children"][1]["children"][0]["children"][0]["level"] == 3
    assert all(node["name"] != "珠海市丽珠医药贸易有限公司" for node in tree)


def test_build_org_tree_synthesizes_missing_root_and_leaders_fallback_to_dash() -> None:
    records = [
        _record("od-a", "101车间", parent=IN_SCOPE_COMPANY_ID, leaders=["ou-known", "ou-missing"]),
        _record("od-b", "已撤销车间", parent=IN_SCOPE_COMPANY_ID, hidden=True),
    ]

    tree = build_org_tree(
        records,
        leader_names={"ou-known": "张三"},
        leader_avatars={"ou-known": "https://example.com/avatar.png"},
        scopes=DEFAULT_ORG_SCOPES,
    )

    assert [node["name"] for node in tree] == [IN_SCOPE_COMPANY_NAME]
    assert tree[0]["id"] == IN_SCOPE_COMPANY_ID
    assert [child["name"] for child in tree[0]["children"]] == ["101车间"]
    child = tree[0]["children"][0]
    assert child["level"] == 1
    assert child["leader_names"] == ["张三"]
    assert child["leader_avatars"] == ["https://example.com/avatar.png"]
    assert child["leader_display"] == "张三"

    records[0].leader_ids = ["ou-missing"]
    tree = build_org_tree(records, leader_names={}, scopes=DEFAULT_ORG_SCOPES)
    assert tree[0]["children"][0]["leader_names"] == []
    assert tree[0]["children"][0]["leader_display"] == "—"


def test_build_org_tree_renders_two_companies() -> None:
    second = OrgScope(department_id="od-company-b", department_name="第二公司")
    scopes = OrgScopes(roots=(DEFAULT_ORG_SCOPE, second))
    records = [
        _root_record(),
        _record("od-a", "101车间", parent=IN_SCOPE_COMPANY_ID),
        _record("od-b", "201车间", parent="od-company-b"),
    ]

    tree = build_org_tree(records, leader_names={}, scopes=scopes)

    assert [node["name"] for node in tree] == [IN_SCOPE_COMPANY_NAME, "第二公司"]
    assert [node["level"] for node in tree] == [0, 0]
    assert [child["name"] for child in tree[0]["children"]] == ["101车间"]
    assert [child["name"] for child in tree[1]["children"]] == ["201车间"]


def test_build_org_tree_uses_configured_scope_root() -> None:
    scope = OrgScope(department_id="od-new-company", department_name="新公司")
    scoped = _record(
        "od-a",
        "101车间",
        parent="od-new-company",
        path=[{"id": "od-new-company", "name": "新公司"}, {"id": "od-a", "name": "101车间"}],
    )
    records = [
        scoped,
        _record("od-other", "旧公司部门", parent=IN_SCOPE_COMPANY_ID),
    ]

    tree = build_org_tree(records, leader_names={}, scopes=OrgScopes(roots=(scope,)))

    assert [node["name"] for node in tree] == ["新公司"]
    assert [child["name"] for child in tree[0]["children"]] == ["101车间"]
    assert tree[0]["children"][0]["parent_name"] == "新公司"
    assert tree[0]["children"][0]["department_path"][0] == {"id": "od-new-company", "name": "新公司"}
    assert DEFAULT_ORG_SCOPE.department_id == IN_SCOPE_COMPANY_ID


def test_select_departments_to_hide_protects_all_roots() -> None:
    rows = [
        {
            "id": IN_SCOPE_COMPANY_ID,
            "hidden": False,
            "department_path": [{"id": IN_SCOPE_COMPANY_ID, "name": IN_SCOPE_COMPANY_NAME}],
        },
        {
            "id": "od-company-b",
            "hidden": False,
            "department_path": [{"id": "od-company-b", "name": "第二公司"}],
        },
        {
            "id": "od-stale",
            "hidden": False,
            "department_path": [
                {"id": IN_SCOPE_COMPANY_ID, "name": IN_SCOPE_COMPANY_NAME},
                {"id": "od-stale", "name": "已移除部门"},
            ],
        },
        {
            "id": "od-out-of-scope",
            "hidden": False,
            "department_path": [
                {"id": "od-other-company", "name": "珠海市丽珠医药贸易有限公司"},
                {"id": "od-out-of-scope", "name": "贸易一部"},
            ],
        },
    ]
    scopes = OrgScopes(roots=(DEFAULT_ORG_SCOPE, OrgScope(department_id="od-company-b", department_name="第二公司")))

    to_hide = select_departments_to_hide(rows, seen_ids={"od-stale"}, scopes=scopes)

    assert to_hide == ["od-out-of-scope"]


def test_trim_path_to_root_drops_invisible_ancestors() -> None:
    path = [
        {"id": "od-invisible-parent", "name": "集团"},
        {"id": IN_SCOPE_COMPANY_ID, "name": IN_SCOPE_COMPANY_NAME},
        {"id": "od-a", "name": "101车间"},
    ]

    assert trim_path_to_root(path, IN_SCOPE_COMPANY_ID) == path[1:]
    assert trim_path_to_root(path, "od-missing") == path


def test_org_scopes_any_root_helpers() -> None:
    second = OrgScope(department_id="od-company-b", department_name="第二公司")
    scopes = OrgScopes(roots=(DEFAULT_ORG_SCOPE, second))

    assert scopes
    assert scopes.is_root(IN_SCOPE_COMPANY_ID)
    assert scopes.is_root("od-company-b")
    assert not scopes.is_root("od-a")
    assert scopes.is_direct_child(IN_SCOPE_COMPANY_ID)
    assert scopes.is_direct_child("od-company-b")
    assert scopes.covers_path([{"id": "od-company-b", "name": "第二公司"}, {"id": "od-b", "name": "201"}])
    assert not scopes.covers_path([{"id": "od-other", "name": "其他"}])
    assert scopes.root_for_path([{"id": "od-company-b", "name": "第二公司"}]) is second
