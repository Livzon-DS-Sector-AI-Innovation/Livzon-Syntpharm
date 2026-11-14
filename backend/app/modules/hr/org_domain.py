"""Pure department-domain helpers for the Feishu-backed org browser (ticket #197).

Kept deliberately free of SQLAlchemy and HTTP so the mirror mapping and the
recursive tree rules can be tested without a database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.modules.hr.feishu_values import int_value, optional_int_value, text_value

COMPANY_LEVEL = 0


@dataclass(frozen=True)
class OrgScope:
    """The company subtree the org browser mirrors.

    Both the sync and the read model take this value object instead of
    comparing against a module-level company id, so the root can be changed
    through HR system settings without touching domain logic.
    """

    department_id: str
    department_name: str

    @property
    def root_path_node(self) -> dict[str, str]:
        return {"id": self.department_id, "name": self.department_name}

    def is_root(self, department_id: str | None) -> bool:
        return department_id == self.department_id

    def is_direct_child(self, parent_id: str | None) -> bool:
        return parent_id == self.department_id

    def covers_path(self, path: list[dict[str, str]] | None) -> bool:
        return any(isinstance(entry, dict) and entry.get("id") == self.department_id for entry in path or [])


@dataclass(frozen=True)
class OrgScopes:
    """The configured company subtrees the org browser mirrors."""

    roots: tuple[OrgScope, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.roots)

    def is_root(self, department_id: str | None) -> bool:
        return any(root.is_root(department_id) for root in self.roots)

    def is_direct_child(self, parent_id: str | None) -> bool:
        return any(root.is_direct_child(parent_id) for root in self.roots)

    def covers_path(self, path: list[dict[str, str]] | None) -> bool:
        return any(root.covers_path(path) for root in self.roots)

    @property
    def root_path_nodes(self) -> list[dict[str, str]]:
        return [root.root_path_node for root in self.roots]

    def root_for_path(self, path: list[dict[str, str]] | None) -> OrgScope | None:
        """Return the configured root contained in ``path`` (nearest first)."""
        for entry in path or []:
            if not isinstance(entry, dict):
                continue
            for root in self.roots:
                if entry.get("id") == root.department_id:
                    return root
        return None

    def root_for_id(self, department_id: str | None) -> OrgScope | None:
        return next((root for root in self.roots if root.department_id == department_id), None)

    def root_for_chain(
        self,
        contact_by_id: dict[str, OrgDepartmentRecord],
        department_id: str | None,
    ) -> OrgScope | None:
        """Walk parents until a configured root is reached."""
        current = department_id
        visited: set[str] = set()
        while current and current not in visited:
            visited.add(current)
            root = self.root_for_id(current)
            if root is not None:
                return root
            record = contact_by_id.get(current)
            current = record.parent_id if record and record.parent_id else None
        return None


def trim_path_to_root(path: list[dict[str, str]] | None, root_id: str) -> list[dict[str, str]]:
    """Drop any ancestor above the configured root (e.g. an invisible parent)."""
    entries = path or []
    for index, entry in enumerate(entries):
        if isinstance(entry, dict) and entry.get("id") == root_id:
            return entries[index:]
    return entries


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
    level: int | None = None
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
        path.append({"id": dept_id, "name": text_value(entry.get("department_name"))})
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

    name = text_value(raw.get("name"))
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
        recursive_members_count=int_value(counts.get("recursive_members_count")),
        direct_members_count=int_value(counts.get("direct_members_count")),
        recursive_departments_count=int_value(counts.get("recursive_departments_count")),
        direct_departments_count=int_value(counts.get("direct_departments_count")),
        data_source=optional_int_value(raw.get("data_source")),
        custom_fields=custom_fields,
    )


def data_source_label(value: int | None) -> str:
    if value is None:
        return "—"
    return _DATA_SOURCE_LABELS.get(value, str(value))


def _sort_key(record: OrgDepartmentRecord) -> tuple[int, str, str]:
    return (record.order, record.name, record.id or "")


def _path_for(
    record: OrgDepartmentRecord,
    parent: OrgDepartmentRecord | None,
    scope: OrgScope,
) -> list[dict[str, str]]:
    root = scope.root_path_node
    if scope.is_root(record.id):
        return [root]
    if record.department_path:
        trimmed = trim_path_to_root(record.department_path, scope.department_id)
        if trimmed and any(isinstance(entry, dict) and entry.get("id") == scope.department_id for entry in trimmed):
            return trimmed
    if parent is None:
        return [root, {"id": record.id or "", "name": record.name}]
    parent_path = parent.department_path or [root, {"id": parent.id or "", "name": parent.name}]
    parent_path = trim_path_to_root(parent_path, scope.department_id) or [root]
    return [*parent_path, {"id": record.id or "", "name": record.name}]


def _node(
    record: OrgDepartmentRecord,
    *,
    level: int,
    parent: OrgDepartmentRecord | None,
    leader_names: dict[str, str],
    leader_avatars: dict[str, str],
    scope: OrgScope,
    children: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    resolved_ids = [leader_id for leader_id in record.leader_ids if leader_names.get(leader_id)]
    resolved = [leader_names[leader_id] for leader_id in resolved_ids]
    avatars = [leader_avatars.get(leader_id, "") for leader_id in resolved_ids]
    return {
        "id": record.id,
        "name": record.name,
        "level": level,
        "parent_id": record.parent_id,
        "parent_name": None if level == COMPANY_LEVEL else (parent.name if parent else scope.department_name),
        "leader_ids": record.leader_ids,
        "leader_names": resolved,
        "leader_avatars": avatars,
        "leader_display": "、".join(resolved) if resolved else "—",
        "recursive_members_count": record.recursive_members_count,
        "direct_members_count": record.direct_members_count,
        "recursive_departments_count": record.recursive_departments_count,
        "direct_departments_count": record.direct_departments_count,
        "department_path": _path_for(record, parent, scope),
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
    leader_avatars: dict[str, str] | None = None,
    scopes: OrgScopes,
) -> list[dict[str, Any]]:
    """Build one recursive company tree per configured root.

    Each root is level 0; its descendants are rendered at their real depth, with
    no fixed two-level limit. A root row missing from the mirror is synthesized
    from the configured id/name so the page works before the first sync.
    """
    names = leader_names or {}
    avatars = leader_avatars or {}
    visible = [record for record in records if record.id and not record.hidden]
    children_by_parent: dict[str, list[OrgDepartmentRecord]] = {}
    for record in visible:
        children_by_parent.setdefault(record.parent_id or "", []).append(record)

    def build_node(
        record: OrgDepartmentRecord,
        *,
        level: int,
        parent: OrgDepartmentRecord | None,
        scope: OrgScope,
        visited: set[str],
    ) -> dict[str, Any]:
        if record.id:
            visited.add(record.id)
        children = sorted(
            (child for child in children_by_parent.get(record.id or "", []) if child.id and child.id not in visited),
            key=_sort_key,
        )
        child_nodes = [
            build_node(child, level=level + 1, parent=record, scope=scope, visited=visited) for child in children
        ]
        return _node(
            record,
            level=level,
            parent=parent,
            leader_names=names,
            leader_avatars=avatars,
            scope=scope,
            children=child_nodes,
        )

    companies: list[dict[str, Any]] = []
    for scope in scopes.roots:
        company = next((record for record in visible if scope.is_root(record.id)), None)
        if company is None:
            company = OrgDepartmentRecord(
                id=scope.department_id,
                name=scope.department_name,
                parent_id=None,
                level=COMPANY_LEVEL,
                department_path=[scope.root_path_node],
            )
        companies.append(build_node(company, level=COMPANY_LEVEL, parent=None, scope=scope, visited=set()))
    return companies


def select_departments_to_hide(
    rows: list[dict[str, Any]],
    *,
    seen_ids: set[str],
    scopes: OrgScopes,
) -> list[str]:
    """Return mirror ids that Feishu no longer returns inside the configured scopes.

    Every department that is not part of the current snapshot is flagged hidden,
    including branches outside all configured companies. Configured roots are
    never hidden.
    """
    return [
        str(row["id"])
        for row in rows
        if not row.get("hidden")
        and str(row.get("id") or "")
        and str(row.get("id")) not in seen_ids
        and not scopes.is_root(str(row.get("id")))
    ]
