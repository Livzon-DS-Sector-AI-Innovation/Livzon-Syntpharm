"""HR module public API for cross-module consumption."""

from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hr.models import EmployeeProfile, HrDepartment
from app.modules.hr.repository import EmployeeRepository

# Valid filter keys accepted by EmployeeRepository.list_employees / _apply_filters
_VALID_FILTER_KEYS = {
    "department",
    "status",
    "keyword",
    "team",
    "position",
    "job_category",
    "level",
    "gender",
    "education",
    "political_status",
    "marital_status",
    "status_category",
    "age_min",
    "age_max",
    "birth_year_min",
    "birth_year_max",
    "hire_date_after",
    "hire_date_before",
    "factory_entry_date_after",
    "factory_entry_date_before",
    "work_start_date_after",
    "work_start_date_before",
}


def _normalize_filters(filters: dict[str, Any]) -> dict[str, Any]:
    """Normalize raw filter dict for EmployeeRepository queries.

    - Maps ``name`` → ``keyword`` (LLM planners often emit ``name``).
    - Drops any keys not recognised by the repository.
    """
    normalized: dict[str, Any] = {}
    for key, value in filters.items():
        if key == "name" and value:
            normalized["keyword"] = value
        elif key in _VALID_FILTER_KEYS and value is not None:
            normalized[key] = value
    return normalized


def _employee_to_dict(emp: Any) -> dict[str, str | None]:
    """Convert an Employee ORM object to a lightweight dict for AI context."""
    return {
        "name": emp.name,
        "employee_number": emp.employee_number,
        "department": emp.department,
        "team": emp.team,
        "position": emp.position,
        "status": emp.status,
        "hire_date": str(emp.hire_date) if emp.hire_date else None,
        "gender": emp.gender,
        "education": emp.education,
        "age": str(emp.age) if emp.age is not None else None,
    }


async def list_employees_by_department(
    session: AsyncSession, department: str
) -> tuple[list[dict[str, str | None]], int]:
    """List employees by department name."""
    repo = EmployeeRepository(session)
    employees, total = await repo.list_employees(department=department, page=1, page_size=200)
    data = [_employee_to_dict(e) for e in employees]
    return data, total


async def query_employees(
    session: AsyncSession,
    *,
    filters: dict[str, Any],
    page: int = 1,
    page_size: int = 200,
) -> tuple[list[dict[str, str | None]], int]:
    """Flexible employee query for AI context injection.

    Args:
        filters: Dict of filter conditions (e.g. {"department": "生产部", "status": "在职"})
        page: Page number (1-based)
        page_size: Items per page

    Returns:
        Tuple of (employee dicts list, total count)
    """
    repo = EmployeeRepository(session)
    normalized = _normalize_filters(filters)
    employees, total = await repo.list_employees(**normalized, page=page, page_size=page_size)
    data = [_employee_to_dict(e) for e in employees]
    return data, total


async def count_employees(
    session: AsyncSession,
    *,
    filters: dict[str, Any],
) -> int:
    """Count employees matching flexible criteria."""
    repo = EmployeeRepository(session)
    normalized = _normalize_filters(filters)
    _, total = await repo.list_employees(**normalized, page=1, page_size=1)
    return total


async def search_employees_by_name(session: AsyncSession, name: str) -> list[dict[str, str | None]]:
    """Search employees by name keyword.

    Returns a lightweight list of employee facts for AI context injection.
    """
    repo = EmployeeRepository(session)
    employees, _ = await repo.list_employees(keyword=name, page=1, page_size=10)
    return [_employee_to_dict(e) for e in employees]


async def search_employees_fuzzy(session: AsyncSession, name: str) -> list[dict[str, str | None]]:
    """Fuzzy search: when exact match returns empty, search by each Chinese character.

    Returns employees whose name contains any character from the query name.
    """
    repo = EmployeeRepository(session)
    seen_ids: set[str] = set()
    results: list[dict[str, str | None]] = []

    for char in name:
        # Only search Chinese characters
        if "一" <= char <= "鿿":
            employees, _ = await repo.list_employees(keyword=char, page=1, page_size=10)
            for e in employees:
                uid = str(e.id)
                if uid not in seen_ids:
                    seen_ids.add(uid)
                    results.append(_employee_to_dict(e))
    return results


async def group_count_employees(
    session: AsyncSession,
    *,
    group_by: str,
    filters: dict[str, Any],
) -> list[dict[str, Any]]:
    """Group employees by a field and count occurrences.

    Args:
        group_by: Field name to group by (e.g. "education", "department")
        filters: Filter conditions

    Returns:
        List of {"value": field_value, "count": int} sorted by count descending.
    """
    repo = EmployeeRepository(session)
    normalized = _normalize_filters(filters)
    return await repo.group_count(group_by, **normalized)  # type: ignore[no-any-return]


async def get_distinct_employee_values(
    session: AsyncSession,
    *,
    field: str,
    filters: dict[str, Any],
) -> list[str]:
    """Get distinct non-null values for a field.

    Args:
        field: Field name (e.g. "department", "education")
        filters: Filter conditions

    Returns:
        List of distinct values.
    """
    repo = EmployeeRepository(session)
    normalized = _normalize_filters(filters)
    return await repo.get_distinct_values(field, **normalized)  # type: ignore[no-any-return]


async def get_department_by_name(session: AsyncSession, name: str) -> HrDepartment | None:
    """Get a department by its exact name.

    Args:
        session: Database session
        name: Exact department name to search for

    Returns:
        HrDepartment if found, None otherwise
    """
    from app.modules.hr.repository import DepartmentRepository

    repo = DepartmentRepository(session)
    result = await repo.get_by_name(name)
    return result if result is None or isinstance(result, HrDepartment) else None


async def list_all_departments(session: AsyncSession) -> list[HrDepartment]:
    """List all non-deleted departments.

    Args:
        session: Database session

    Returns:
        List of all HrDepartment objects
    """
    from app.modules.hr.repository import DepartmentRepository

    repo = DepartmentRepository(session)
    departments, _ = await repo.list_departments(page=1, page_size=10000)
    return departments


def _profile_payload(profile: EmployeeProfile) -> dict[str, Any]:
    """Serialize the fields other modules need to display a person."""
    return {
        "id": str(profile.id),
        "open_id": profile.open_id,
        "name": profile.name,
        "employee_no": profile.employee_no,
        "department_names": list(profile.department_names or []),
        "department_path": [
            {"id": str(entry.get("id", "")), "name": str(entry.get("name", ""))}
            for entry in (profile.department_path or [])
            if isinstance(entry, dict)
        ],
        "job_title_name": profile.job_title_name,
        "avatar_url": profile.avatar_240 or profile.avatar_72 or profile.avatar_640 or profile.avatar_origin or "",
    }


async def list_directory_departments(session: AsyncSession) -> list[dict[str, Any]]:
    """Return the visible department tree keyed by ``hr.departments.id``.

    Cross-module callers must not import ``hr.models`` themselves; this is the
    read seam introduced by #219.
    """
    from app.modules.hr.directory_service import list_department_tree

    return await list_department_tree(session)


async def list_current_profiles(
    session: AsyncSession,
    *,
    keyword: str | None = None,
    department_id: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    """Return current employees (``is_current=True``) with a department filter."""
    from app.modules.hr.directory_service import list_people

    return await list_people(
        session,
        keyword=keyword,
        department_id=department_id,
        offset=offset,
        limit=limit,
    )


async def get_profile_by_id(session: AsyncSession, profile_id: UUID) -> dict[str, Any] | None:
    """Return a single employee profile by its HR UUID.

    Used by pre-login permission grants: a role is granted to a person who may
    never have logged in yet, so the account row is materialised from here.
    """
    result = await session.execute(
        select(EmployeeProfile).where(
            EmployeeProfile.id == profile_id,
            EmployeeProfile.is_deleted.is_(False),
        )
    )
    profile = result.scalar_one_or_none()
    return _profile_payload(profile) if profile is not None else None


async def get_profile_by_open_id(session: AsyncSession, open_id: str) -> dict[str, Any] | None:
    """Return the current profile of a Feishu open id, or ``None``.

    Used by the identity module to assemble display fields for an account row
    without reaching into HR tables.
    """
    result = await session.execute(
        select(EmployeeProfile).where(
            EmployeeProfile.open_id == open_id,
            EmployeeProfile.is_deleted.is_(False),
            EmployeeProfile.is_current.is_(True),
        )
    )
    profile = result.scalar_one_or_none()
    return _profile_payload(profile) if profile is not None else None


async def find_profiles_by_name(session: AsyncSession, name: str) -> list[dict[str, Any]]:
    """Return current profiles whose name matches exactly (同名多人时返回全部）."""
    if not name or not name.strip():
        return []
    result = await session.execute(
        select(EmployeeProfile).where(
            EmployeeProfile.name == name.strip(),
            EmployeeProfile.is_deleted.is_(False),
            EmployeeProfile.is_current.is_(True),
        )
    )
    return [_profile_payload(profile) for profile in result.scalars().all()]


async def find_profile_by_feishu_id(session: AsyncSession, feishu_id: str) -> dict[str, Any] | None:
    """Look a current profile up by Feishu open id (the only synced identity key)."""
    if not feishu_id:
        return None
    return await get_profile_by_open_id(session, feishu_id.strip())


async def find_profile_by_email(session: AsyncSession, email: str) -> dict[str, Any] | None:
    """Look a current profile up by email / enterprise email."""
    if not email or not email.strip():
        return None
    value = email.strip()
    result = await session.execute(
        select(EmployeeProfile).where(
            or_(EmployeeProfile.email == value, EmployeeProfile.enterprise_email == value),
            EmployeeProfile.is_deleted.is_(False),
            EmployeeProfile.is_current.is_(True),
        )
    )
    profile = result.scalars().first()
    return _profile_payload(profile) if profile is not None else None


def _department_row(row: HrDepartment) -> dict[str, Any]:
    """Serialize the department fields leadership resolution needs."""
    return {
        "id": str(row.id),
        "name": row.name,
        "code": row.code or "",
        "feishu_department_id": row.feishu_department_id or "",
        "parent_feishu_department_id": row.parent_feishu_department_id or "",
        "leader_ids": list(row.leader_ids or []),
        "level": row.level,
        "order": row.order or 0,
    }


async def find_department_row_by_name(session: AsyncSession, name: str) -> dict[str, Any] | None:
    """Resolve a department by name: exact match first, then suffix/contains.

    Safety notifications resolve the responsible leader from a free-text
    department name, so the lookup mirrors the legacy behaviour (exact →
    ends-with → contains, first hit wins).
    """
    if not name or not name.strip():
        return None
    value = name.strip()
    base = select(HrDepartment).where(
        HrDepartment.is_deleted.is_(False),
        HrDepartment.status_is_deleted.is_(False),
    )
    exact = (await session.execute(base.where(HrDepartment.name == value))).scalars().first()
    if exact is not None:
        return _department_row(exact)
    fuzzy = (
        (
            await session.execute(
                base.where(or_(HrDepartment.name.ilike(f"%{value}"), HrDepartment.name.ilike(f"%{value}%"))).order_by(
                    HrDepartment.order, HrDepartment.name
                )
            )
        )
        .scalars()
        .all()
    )
    return _department_row(fuzzy[0]) if fuzzy else None


async def list_department_rows(session: AsyncSession) -> list[dict[str, Any]]:
    """Return every visible department with leader names and member counts.

    Used by safety's org-chart / leader resolution after ``identity.departments``
    was retired (#219). Leader ids are Feishu open ids.
    """
    from app.modules.hr.org_repository import resolve_leader_names

    result = await session.execute(
        select(HrDepartment)
        .where(
            HrDepartment.is_deleted.is_(False),
            HrDepartment.status_is_deleted.is_(False),
        )
        .order_by(HrDepartment.order, HrDepartment.name)
    )
    rows = list(result.scalars().all())
    leader_ids = {leader_id for row in rows for leader_id in (row.leader_ids or []) if leader_id}
    leader_names = await resolve_leader_names(session, leader_ids)
    return [
        {
            **_department_row(row),
            "member_count": row.recursive_members_count or 0,
            "leader_names": [
                leader_names.get(leader_id, leader_id) for leader_id in (row.leader_ids or []) if leader_id
            ],
        }
        for row in rows
    ]


async def get_department_row_by_feishu_id(session: AsyncSession, feishu_department_id: str) -> dict[str, Any] | None:
    """Look a visible department up by its Feishu department id."""
    if not feishu_department_id:
        return None
    result = await session.execute(
        select(HrDepartment).where(
            HrDepartment.feishu_department_id == feishu_department_id,
            HrDepartment.is_deleted.is_(False),
            HrDepartment.status_is_deleted.is_(False),
        )
    )
    row = result.scalars().first()
    return _department_row(row) if row is not None else None


async def get_profiles_by_open_ids(session: AsyncSession, open_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Batch variant of :func:`get_profile_by_open_id` to avoid N+1 queries."""
    ids = [open_id for open_id in open_ids if open_id]
    if not ids:
        return {}
    result = await session.execute(
        select(EmployeeProfile).where(
            EmployeeProfile.open_id.in_(ids),
            EmployeeProfile.is_deleted.is_(False),
            EmployeeProfile.is_current.is_(True),
        )
    )
    return {profile.open_id: _profile_payload(profile) for profile in result.scalars().all()}
