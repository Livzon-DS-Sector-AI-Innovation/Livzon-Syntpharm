"""Department-management org domain seams (ticket #197).

Seams under test:
1. ``parse_directory_department`` — raw Feishu ``directory/v1/departments/mget``
   payload → mirror fields.
2. ``build_org_tree`` — mirror rows → recursive tree. Roots are derived from the
   data (parent missing/None), so multiple visible companies appear naturally.
3. ``select_departments_to_hide`` — rows no longer visible to the app.

Pure functions: no DB, no HTTP.
"""

from __future__ import annotations

from app.modules.hr.org_domain import (
    OrgDepartmentRecord,
    build_org_tree,
    parse_directory_department,
    select_departments_to_hide,
)
from tests.fixtures.org_scope import IN_SCOPE_COMPANY_ID, IN_SCOPE_COMPANY_NAME


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


def _root_record(dept_id: str = IN_SCOPE_COMPANY_ID, name: str = IN_SCOPE_COMPANY_NAME) -> OrgDepartmentRecord:
    return _record(dept_id, name, parent=None, path=[{"id": dept_id, "name": name}], level=0)


def test_build_org_tree_renders_company_and_all_levels() -> None:
    records = [
        _root_record(),
        _record("od-a", "101车间", parent=IN_SCOPE_COMPANY_ID, order=2),
        _record("od-b", "102车间", parent=IN_SCOPE_COMPANY_ID, order=1),
        _record("od-a1", "合成工段", parent="od-a", order=1),
        _record("od-a1x", "更深的组", parent="od-a1"),
        _record("od-other", "珠海市丽珠医药贸易有限公司", parent=None),
        _record("od-other-1", "贸易一部", parent="od-other"),
    ]

    tree = build_org_tree(records, leader_names={})

    assert [node["name"] for node in tree] == [IN_SCOPE_COMPANY_NAME, "珠海市丽珠医药贸易有限公司"]
    company = tree[0]
    assert company["level"] == 0
    assert [child["name"] for child in company["children"]] == ["102车间", "101车间"]
    assert company["children"][1]["level"] == 1
    assert [child["name"] for child in company["children"][1]["children"]] == ["合成工段"]
    assert company["children"][1]["children"][0]["level"] == 2
    assert company["children"][1]["children"][0]["children"][0]["name"] == "更深的组"
    assert company["children"][1]["children"][0]["children"][0]["level"] == 3
    assert [child["name"] for child in tree[1]["children"]] == ["贸易一部"]


def test_build_org_tree_derives_roots_when_company_row_is_missing() -> None:
    records = [
        _record("od-a", "101车间", parent=IN_SCOPE_COMPANY_ID, leaders=["ou-known", "ou-missing"]),
        _record("od-b", "已撤销车间", parent=IN_SCOPE_COMPANY_ID, hidden=True),
    ]

    tree = build_org_tree(
        records,
        leader_names={"ou-known": "张三"},
        leader_avatars={"ou-known": "https://example.com/avatar.png"},
    )

    assert [node["name"] for node in tree] == ["101车间"]
    child = tree[0]
    assert child["level"] == 0
    assert child["parent_name"] is None
    assert child["leader_names"] == ["张三"]
    assert child["leader_avatars"] == ["https://example.com/avatar.png"]
    assert child["leader_display"] == "张三"

    records[0].leader_ids = ["ou-missing"]
    tree = build_org_tree(records, leader_names={})
    assert tree[0]["leader_names"] == []
    assert tree[0]["leader_display"] == "—"


def test_build_org_tree_renders_two_parentless_companies() -> None:
    second = _root_record("od-company-b", "第二公司")
    records = [
        _root_record(),
        _record("od-a", "101车间", parent=IN_SCOPE_COMPANY_ID),
        second,
        _record("od-b", "201车间", parent="od-company-b"),
    ]

    tree = build_org_tree(records, leader_names={})

    assert [node["name"] for node in tree] == [IN_SCOPE_COMPANY_NAME, "第二公司"]
    assert [node["level"] for node in tree] == [0, 0]
    assert [child["name"] for child in tree[0]["children"]] == ["101车间"]
    assert [child["name"] for child in tree[1]["children"]] == ["201车间"]


def test_build_org_tree_treats_missing_parent_as_root() -> None:
    records = [
        _record("od-a", "101车间", parent="od-invisible-parent"),
        _record("od-a1", "合成工段", parent="od-a"),
    ]

    tree = build_org_tree(records, leader_names={})

    assert [node["name"] for node in tree] == ["101车间"]
    assert [child["name"] for child in tree[0]["children"]] == ["合成工段"]


def test_select_departments_to_hide_hides_every_unseen_row() -> None:
    rows = [
        {"id": IN_SCOPE_COMPANY_ID, "hidden": False},
        {"id": "od-company-b", "hidden": False},
        {"id": "od-stale", "hidden": False},
        {"id": "od-out-of-scope", "hidden": False},
        {"id": "od-already-hidden", "hidden": True},
    ]

    to_hide = select_departments_to_hide(rows, seen_ids={"od-stale"})

    assert to_hide == [IN_SCOPE_COMPANY_ID, "od-company-b", "od-out-of-scope"]
