"""Pure department-domain helpers for the Feishu-backed org browser (ticket #197).

Kept deliberately free of SQLAlchemy and HTTP so the mirror mapping and the
two-level tree rules can be tested without a database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

IN_SCOPE_COMPANY_ID = "od-9c7089e0d3edc7822c0650a9b2ff4318"
IN_SCOPE_COMPANY_NAME = "珠海保税区丽珠合成制药有限公司"
OUT_OF_SCOPE_COMPANY_NAME = "珠海市丽珠医药贸易有限公司"

ROOT_LEVEL = 1
SECOND_LEVEL = 2

_DATA_SOURCE_LABELS: dict[int, str] = {
    1: "飞书",
    2: "第三方",
}


@dataclass
class OrgDepartmentRecord:
    """A row of the department mirror, independent of the ORM."""

    id: str | None
    name: str
    parent_id: str | None
    order: int = 0
    order_weight: str | None = None
    hidden: bool = False
    leader_ids: list[str] = field(default_factory=list)
    department_path: list[dict[str, str]] = field(default_factory=list)
    enabled_status: bool | None = None
    recursive_members_count: int = 0
    direct_members_count: int = 0
    recursive_departments_count: int = 0
    direct_departments_count: int = 0
    data_source: int | None = None
    custom_fields: list[dict[str, Any]] = field(default_factory=list)

    @property
    def department_id(self) -> str | None:
        """Feishu open_department_id (alias for the mirror row id)."""
        return self.id

    @property
    def parent_department_id(self) -> str | None:
        """Feishu parent open_department_id (alias for ``parent_id``)."""
        return self.parent_id


def _text(value: Any) -> str:
    """Read an i18n text object or a plain string as a display name."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        default = value.get("default_value")
        if isinstance(default, str):
            return default.strip()
        i18n = value.get("i18n_value")
        if isinstance(i18n, dict):
            for key in ("zh_cn", "zh-CN", "en_us"):
                candidate = i18n.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()
    return ""


def _int(value: Any) -> int:
    if value is None or value == "":
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _path_from_raw(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    path: list[dict[str, str]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        dept_id = str(entry.get("department_id") or "").strip()
        if not dept_id or dept_id == "0":
            continue
        path.append({"id": dept_id, "name": _text(entry.get("department_name"))})
    return path


def parse_directory_department(raw: dict[str, Any]) -> OrgDepartmentRecord:
    """Map a ``directory/v1/departments/mget`` department payload to mirror fields."""
    department_id = str(raw.get("department_id") or "").strip()
    if not department_id or department_id == "0":
        department_id = ""

    parent_id = str(raw.get("parent_department_id") or "").strip()
    if not parent_id or parent_id == "0":
        parent_id = ""

    leaders_raw = raw.get("leaders")
    leader_ids: list[str] = []
    if isinstance(leaders_raw, list):
        for leader in leaders_raw:
            if not isinstance(leader, dict):
                continue
            leader_id = str(leader.get("leader_id") or "").strip()
            if leader_id and leader_id != "0" and leader_id not in leader_ids:
                leader_ids.append(leader_id)

    counts_raw = raw.get("department_count")
    counts = counts_raw if isinstance(counts_raw, dict) else {}

    order_weight = str(raw.get("order_weight")).strip() if raw.get("order_weight") not in (None, "") else None
    try:
        order = int(order_weight) if order_weight is not None else 0
    except ValueError:
        order = 0

    custom_raw = raw.get("custom_field_values")
    custom_fields = [item for item in custom_raw if isinstance(item, dict)] if isinstance(custom_raw, list) else []

    name = _text(raw.get("name"))
    path = _path_from_raw(raw.get("department_path_infos"))
    if path and department_id and path[-1]["id"] != department_id:
        path.append({"id": department_id, "name": name})

    return OrgDepartmentRecord(
        id=department_id or None,
        name=name,
        parent_id=parent_id or None,
        order=order,
        order_weight=order_weight,
        hidden=False,
        leader_ids=leader_ids,
        department_path=path,
        enabled_status=raw.get("enabled_status") if isinstance(raw.get("enabled_status"), bool) else None,
        recursive_members_count=_int(counts.get("recursive_members_count")),
        direct_members_count=_int(counts.get("direct_members_count")),
        recursive_departments_count=_int(counts.get("recursive_departments_count")),
        direct_departments_count=_int(counts.get("direct_departments_count")),
        data_source=_optional_int(raw.get("data_source")),
        custom_fields=custom_fields,
    )


def data_source_label(value: int | None) -> str:
    if value is None:
        return "—"
    return _DATA_SOURCE_LABELS.get(value, str(value))


def _sort_key(record: OrgDepartmentRecord) -> tuple[int, str, str]:
    return (record.order, record.name, record.id or "")


def _path_for(record: OrgDepartmentRecord, parent: OrgDepartmentRecord | None) -> list[dict[str, str]]:
    if record.department_path:
        return record.department_path
    root = {"id": IN_SCOPE_COMPANY_ID, "name": IN_SCOPE_COMPANY_NAME}
    if parent is None:
        return [root, {"id": record.id or "", "name": record.name}]
    parent_path = parent.department_path or [root, {"id": parent.id or "", "name": parent.name}]
    return [*parent_path, {"id": record.id or "", "name": record.name}]


def _node(
    record: OrgDepartmentRecord,
    *,
    level: int,
    parent: OrgDepartmentRecord | None,
    leader_names: dict[str, str],
    children: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    resolved = [leader_names[leader_id] for leader_id in record.leader_ids if leader_names.get(leader_id)]
    return {
        "id": record.id,
        "name": record.name,
        "level": level,
        "parent_id": record.parent_id,
        "parent_name": parent.name if parent else IN_SCOPE_COMPANY_NAME,
        "leader_ids": record.leader_ids,
        "leader_names": resolved,
        "leader_display": "、".join(resolved) if resolved else "—",
        "recursive_members_count": record.recursive_members_count,
        "direct_members_count": record.direct_members_count,
        "recursive_departments_count": record.recursive_departments_count,
        "direct_departments_count": record.direct_departments_count,
        "department_path": _path_for(record, parent),
        "enabled_status": record.enabled_status,
        "order_weight": record.order_weight,
        "data_source": data_source_label(record.data_source),
        "custom_fields": record.custom_fields,
        "children": children or [],
    }


def build_org_tree(
    records: list[OrgDepartmentRecord],
    *,
    leader_names: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Build the two-level tree: 一级部门 under the company root, then 二级部门.

    The company root itself is not a level, out-of-scope branches are dropped,
    hidden/removed rows are dropped, and anything deeper than level 2 is ignored.
    """
    names = leader_names or {}
    visible = [record for record in records if record.id and not record.hidden]

    level_one = sorted(
        (record for record in visible if record.parent_id == IN_SCOPE_COMPANY_ID),
        key=_sort_key,
    )
    level_one_ids = {record.id for record in level_one}

    children_by_parent: dict[str, list[OrgDepartmentRecord]] = {}
    for record in visible:
        if record.parent_id in level_one_ids:
            children_by_parent.setdefault(record.parent_id or "", []).append(record)

    tree: list[dict[str, Any]] = []
    for parent in level_one:
        children = sorted(children_by_parent.get(parent.id or "", []), key=_sort_key)
        child_nodes = [_node(child, level=SECOND_LEVEL, parent=parent, leader_names=names) for child in children]
        tree.append(_node(parent, level=ROOT_LEVEL, parent=None, leader_names=names, children=child_nodes))
    return tree


def select_departments_to_hide(
    rows: list[dict[str, Any]],
    *,
    seen_ids: set[str],
) -> list[str]:
    """Return previously in-scope mirror ids that Feishu no longer returns.

    Only rows whose stored path descends from the in-scope company are touched;
    departments belonging to other companies in the shared mirror are left alone.
    """
    to_hide: list[str] = []
    for row in rows:
        if row.get("hidden"):
            continue
        dept_id = str(row.get("id") or "")
        if not dept_id or dept_id in seen_ids or dept_id == IN_SCOPE_COMPANY_ID:
            continue
        path = row.get("department_path")
        if not isinstance(path, list):
            continue
        if any(isinstance(entry, dict) and entry.get("id") == IN_SCOPE_COMPANY_ID for entry in path):
            to_hide.append(dept_id)
    return to_hide
