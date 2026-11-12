"""Pure personnel-mirror mapping for 员工档案 (ticket #198).

Kept free of SQLAlchemy and HTTP so the Feishu ``directory/v1/employees/mget``
mapping, empty-value rules and display labels can be unit tested.

Feishu omits keys with no value. Absence therefore means "empty", never an
error, and the mirror always writes every retained field on each sync.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

_DATA_SOURCE_LABELS: dict[int, str] = {
    1: "飞书",
    2: "第三方",
}

_GENDER_LABELS: dict[int, str] = {
    1: "男",
    2: "女",
}

_STAFF_STATUS_LABELS: dict[int, str] = {
    1: "在职",
    2: "离职",
    3: "待入职",
    4: "取消入职",
}


@dataclass
class EmployeeProfileRecord:
    """A personnel mirror row, independent of the ORM."""

    open_id: str
    name: str = ""
    mobile: str = ""
    email: str = ""
    enterprise_email: str = ""
    email_aliases: list[str] = field(default_factory=list)
    gender: int | None = None
    education: str = ""
    age: int | None = None
    description: str = ""
    avatar_72: str = ""
    avatar_240: str = ""
    avatar_640: str = ""
    avatar_origin: str = ""
    background_image: str = ""
    geo_name: str = ""
    active_status: int | None = None
    is_resigned: bool = False
    resign_time: str = ""
    is_admin: bool = False
    is_primary_admin: bool = False
    data_source: int | None = None
    employee_no: str = ""
    job_title_id: str = ""
    job_title_name: str = ""
    hire_date: date | None = None
    employment_type: int | None = None
    staff_status: int | None = None
    work_country_or_region: str = ""
    work_place_id: str = ""
    work_place_name: str = ""
    work_station: str = ""
    extension_number: str = ""
    dotted_line_leader_ids: list[str] = field(default_factory=list)
    resign_date: date | None = None
    resign_type: str = ""
    resign_reason: str = ""
    resign_remark: str = ""
    positions: list[dict[str, str]] = field(default_factory=list)
    job_level_id: str = ""
    job_level_name: str = ""
    job_family_id: str = ""
    job_family_name: str = ""
    department_ids: list[str] = field(default_factory=list)
    department_names: list[str] = field(default_factory=list)
    department_path: list[dict[str, str]] = field(default_factory=list)
    last_synced_at: datetime | None = None


def _text(value: Any) -> str:
    """Read an i18n text object or a plain string as display text."""
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
        for key in ("name", "text", "value"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    return ""


def _str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _optional_int(value: Any) -> int | None:
    if value is None or value == "" or value == "0":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    return bool(value)


def _date(value: Any) -> date | None:
    text = _str(value)
    if not text or text == "0":
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for entry in value:
        text = _text(entry) if isinstance(entry, dict) else _str(entry)
        if text and text != "0" and text not in items:
            items.append(text)
    return items


def _object_fields(value: Any, id_key: str, name_key: str, *, name_aliases: tuple[str, ...] = ()) -> tuple[str, str]:
    if not isinstance(value, dict):
        return "", ""
    object_id = _str(value.get(id_key))
    name = _text(value.get(name_key))
    for alias in name_aliases:
        if not name:
            name = _text(value.get(alias))
    return object_id, name


def _positions(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    positions: list[dict[str, str]] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        position_id = _str(entry.get("position_code") or entry.get("id"))
        name = _text(entry.get("position_name")) or _text(entry.get("name"))
        if position_id or name:
            positions.append({"id": position_id, "name": name})
    return positions


def _department_ids(raw: dict[str, Any]) -> list[str]:
    for key in ("department_ids", "employee_order_in_departments", "departments"):
        value = raw.get(key)
        if not isinstance(value, list):
            continue
        ids: list[str] = []
        for entry in value:
            if isinstance(entry, dict):
                dept_id = _str(entry.get("department_id") or entry.get("id"))
            else:
                dept_id = _str(entry)
            if dept_id and dept_id != "0" and dept_id not in ids:
                ids.append(dept_id)
        if ids:
            return ids
    return []


def _department_names(raw: dict[str, Any]) -> list[str]:
    value = raw.get("department_names")
    if not isinstance(value, list):
        return []
    names: list[str] = []
    for entry in value:
        name = _text(entry) if isinstance(entry, dict) else _str(entry)
        if name:
            names.append(name)
    return names


def _department_path(raw: dict[str, Any]) -> list[dict[str, str]]:
    for key in ("department_path", "department_path_infos"):
        value = raw.get(key)
        if not isinstance(value, list):
            continue
        path: list[dict[str, str]] = []
        for entry in value:
            if not isinstance(entry, dict):
                continue
            dept_id = _str(entry.get("department_id") or entry.get("id"))
            if not dept_id or dept_id == "0":
                continue
            name = _text(entry.get("department_name")) or _text(entry.get("name"))
            path.append({"id": dept_id, "name": name})
        if path:
            return path
    return []


def parse_directory_employee(raw: dict[str, Any]) -> EmployeeProfileRecord | None:
    """Map a ``directory/v1/employees/mget`` employee payload to mirror fields.

    ``open_id`` is the mirror key; a payload without it is skipped.
    """
    open_id = _str(raw.get("open_id"))
    if not open_id:
        return None

    avatar_raw = raw.get("avatar")
    avatar = avatar_raw if isinstance(avatar_raw, dict) else {}

    place_raw = raw.get("work_place")
    place = place_raw if isinstance(place_raw, dict) else {}
    place_id = _str(place.get("place_id"))
    if place_id == "0":
        place_id = ""
    place_name = _text(place.get("place_name")) if place_id else ""

    job_title_id, job_title_name = _object_fields(
        raw.get("job_title"), "job_title_id", "job_title_name", name_aliases=("name",)
    )
    job_level_id, job_level_name = _object_fields(
        raw.get("job_level"), "job_level_id", "job_level_name", name_aliases=("name",)
    )
    job_family_id, job_family_name = _object_fields(
        raw.get("job_family"), "job_family_id", "job_family_name", name_aliases=("name",)
    )

    resign_time = _str(raw.get("resign_time"))
    if resign_time == "0":
        resign_time = ""

    aliases = _str_list(raw.get("enterprise_email_aliases") or raw.get("email_alias"))

    return EmployeeProfileRecord(
        open_id=open_id,
        name=_text(raw.get("name")),
        mobile=_str(raw.get("mobile")),
        email=_str(raw.get("email")),
        enterprise_email=_str(raw.get("enterprise_email")),
        email_aliases=aliases,
        gender=_optional_int(raw.get("gender")),
        education=_str(raw.get("education")),
        age=_optional_int(raw.get("age")),
        description=_str(raw.get("description")),
        avatar_72=_str(avatar.get("avatar_72")),
        avatar_240=_str(avatar.get("avatar_240")),
        avatar_640=_str(avatar.get("avatar_640")),
        avatar_origin=_str(avatar.get("avatar_origin")),
        background_image=_str(raw.get("background_image")),
        geo_name=_str(raw.get("geo_name") or raw.get("geo")),
        active_status=_optional_int(raw.get("active_status")),
        is_resigned=_bool(raw.get("is_resigned")),
        resign_time=resign_time,
        is_admin=_bool(raw.get("is_admin")),
        is_primary_admin=_bool(raw.get("is_primary_admin")),
        data_source=_optional_int(raw.get("data_source")),
        employee_no=_str(raw.get("job_number") or raw.get("employee_no")),
        job_title_id=job_title_id,
        job_title_name=job_title_name,
        hire_date=_date(raw.get("join_date") or raw.get("hire_date")),
        employment_type=_optional_int(raw.get("employment_type")),
        staff_status=_optional_int(raw.get("staff_status")),
        work_country_or_region=_str(raw.get("work_country_or_region")),
        work_place_id=place_id,
        work_place_name=place_name,
        work_station=_str(raw.get("work_station")),
        extension_number=_str(raw.get("extension_number") or raw.get("extension")),
        dotted_line_leader_ids=_str_list(raw.get("dotted_line_leader_ids")),
        resign_date=_date(raw.get("resign_date")),
        resign_type=_str(raw.get("resign_type")),
        resign_reason=_str(raw.get("resign_reason")),
        resign_remark=_str(raw.get("resign_remark")),
        positions=_positions(raw.get("positions")),
        job_level_id=job_level_id,
        job_level_name=job_level_name,
        job_family_id=job_family_id,
        job_family_name=job_family_name,
        department_ids=_department_ids(raw),
        department_names=_department_names(raw),
        department_path=_department_path(raw),
    )


def gender_label(value: int | None) -> str:
    if value is None:
        return "未知"
    return _GENDER_LABELS.get(value, "未知")


def staff_status_label(value: int | None) -> str:
    if value is None:
        return "—"
    return _STAFF_STATUS_LABELS.get(value, str(value))


def active_status_label(value: int | None) -> str:
    if value is None:
        return "—"
    return {1: "未激活", 2: "已激活"}.get(value, str(value))


def data_source_label(value: int | None) -> str:
    if value is None:
        return "—"
    return _DATA_SOURCE_LABELS.get(value, str(value))


def department_levels_from(
    department_path: list[dict[str, Any]] | None,
    department_names: list[str] | None,
) -> tuple[str, str]:
    """Return (一级部门, 二级部门) from the stored root → level 1 → level 2 path.

    The first path entry is the company root, which is not a level. Records
    without a path fall back to the stored department names.
    """
    path = [entry for entry in (department_path or []) if entry.get("name")]
    if len(path) >= 3:
        return path[1]["name"], path[2]["name"]
    if len(path) == 2:
        return path[1]["name"], ""
    names = [name for name in (department_names or []) if name]
    if len(names) >= 2:
        return names[0], names[1]
    if names:
        return names[0], ""
    return "", ""


def department_levels(record: EmployeeProfileRecord) -> tuple[str, str]:
    return department_levels_from(record.department_path, record.department_names)
