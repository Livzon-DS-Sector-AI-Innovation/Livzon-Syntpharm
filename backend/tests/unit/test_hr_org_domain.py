"""部门管理 org domain seams (ticket #197).

Seams under test:
1. ``parse_directory_department`` — turns a raw Feishu ``directory/v1/departments/mget``
   payload into mirror fields. Catches: i18n name handling, "0" ids, empty arrays,
   string counts.
2. ``build_org_tree`` — turns mirror rows into the two-level tree. Catches: company
   root leaking as a level, deeper levels leaking in, hidden rows leaking in,
   ordering, leader-name fallback "—".

These are pure functions: no DB, no HTTP.
"""

from __future__ import annotations

from app.modules.hr.org_domain import (
    IN_SCOPE_COMPANY_ID,
    IN_SCOPE_COMPANY_NAME,
    OrgDepartmentRecord,
    build_org_tree,
    parse_directory_department,
    select_departments_to_hide,
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
) -> OrgDepartmentRecord:
    return OrgDepartmentRecord(
        id=dept_id,
        name=name,
        parent_id=parent,
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


def test_build_org_tree_keeps_only_two_levels_under_company_root() -> None:
    records = [
        _record("od-root", IN_SCOPE_COMPANY_NAME, parent="0"),
        _record("od-a", "101车间", parent=IN_SCOPE_COMPANY_ID, order=2),
        _record("od-b", "102车间", parent=IN_SCOPE_COMPANY_ID, order=1),
        _record("od-a1", "合成工段", parent="od-a", order=1),
        _record("od-a2", "精制工段", parent="od-a", order=2),
        _record("od-a1x", "更深的组", parent="od-a1"),
        _record("od-other", "珠海市丽珠医药贸易有限公司", parent="0"),
        _record("od-other-1", "贸易一部", parent="od-other"),
    ]

    tree = build_org_tree(records, leader_names={})

    assert [node["name"] for node in tree] == ["102车间", "101车间"]
    assert tree[1]["level"] == 1
    assert [child["name"] for child in tree[1]["children"]] == ["合成工段", "精制工段"]
    assert tree[1]["children"][0]["level"] == 2
    assert all(child["name"] != "更深的组" for node in tree for child in node["children"])
    assert all(node["name"] != "珠海市丽珠医药贸易有限公司" for node in tree)
    assert all(node["name"] != IN_SCOPE_COMPANY_NAME for node in tree)


def test_build_org_tree_filters_hidden_and_renders_unresolved_leaders_as_dash() -> None:
    records = [
        _record("od-a", "101车间", parent=IN_SCOPE_COMPANY_ID, leaders=["ou-known", "ou-missing"]),
        _record("od-b", "已撤销车间", parent=IN_SCOPE_COMPANY_ID, hidden=True),
    ]

    tree = build_org_tree(records, leader_names={"ou-known": "张三"})

    assert [node["name"] for node in tree] == ["101车间"]
    assert tree[0]["leader_names"] == ["张三"]
    assert tree[0]["leader_display"] == "张三"

    records[0].leader_ids = ["ou-missing"]
    tree = build_org_tree(records, leader_names={})
    assert tree[0]["leader_names"] == []
    assert tree[0]["leader_display"] == "—"


def test_select_departments_to_hide_only_touches_previous_in_scope_rows() -> None:
    rows = [
        {
            "id": IN_SCOPE_COMPANY_ID,
            "hidden": False,
            "department_path": [
                {"id": IN_SCOPE_COMPANY_ID, "name": IN_SCOPE_COMPANY_NAME},
            ],
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
        {
            "id": "od-seen",
            "hidden": False,
            "department_path": [
                {"id": IN_SCOPE_COMPANY_ID, "name": IN_SCOPE_COMPANY_NAME},
                {"id": "od-seen", "name": "101车间"},
            ],
        },
    ]

    to_hide = select_departments_to_hide(rows, seen_ids={"od-seen"})

    assert to_hide == ["od-stale"]
