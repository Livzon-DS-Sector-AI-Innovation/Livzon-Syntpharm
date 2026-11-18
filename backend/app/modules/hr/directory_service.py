"""Read models behind the HR public directory (ticket #219).

Departments are exposed with ``hr.departments.id`` as the business reference
(the Feishu id stays an internal sync key), and people only include current
employment rows of ``hr.employee_profiles``. Both helpers return plain dicts so
``public_api`` can hand them to other modules without leaking ORM objects.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.exceptions import BadRequestException
from app.modules.hr.models import EmployeeProfile, HrDepartment
from app.modules.hr.people_repository import resolve_filter_department_ids


def _path_names(row: HrDepartment) -> list[str]:
    names = [
        str(entry.get("name") or "")
        for entry in (row.department_path or [])
        if isinstance(entry, dict) and entry.get("name")
    ]
    return names or [row.name]


def _avatar(profile: EmployeeProfile) -> str:
    return profile.avatar_240 or profile.avatar_72 or profile.avatar_640 or profile.avatar_origin or ""


async def list_department_tree(session: AsyncSession) -> list[dict[str, Any]]:
    """Return the visible department mirror as a fully expanded tree."""
    result = await session.execute(
        select(HrDepartment).where(
            HrDepartment.is_deleted.is_(False),
            HrDepartment.status_is_deleted.is_(False),
        )
    )
    rows = list(result.scalars().all())
    by_feishu_id = {row.feishu_department_id: row for row in rows if row.feishu_department_id}

    nodes: dict[str, dict[str, Any]] = {}
    for row in rows:
        nodes[str(row.id)] = {
            "id": str(row.id),
            "code": row.code or "",
            "name": row.name,
            "parent_id": None,
            "level": row.level if row.level is not None else 0,
            "path_names": _path_names(row),
            "order": row.order or 0,
            "children": [],
        }

    roots: list[dict[str, Any]] = []
    for row in rows:
        node = nodes[str(row.id)]
        parent_row = by_feishu_id.get(row.parent_feishu_department_id or "")
        if parent_row is None or str(parent_row.id) == str(row.id):
            roots.append(node)
            continue
        node["parent_id"] = str(parent_row.id)
        nodes[str(parent_row.id)]["children"].append(node)

    def _sort(branch: list[dict[str, Any]]) -> None:
        branch.sort(key=lambda item: (item["order"], item["name"]))
        for item in branch:
            _sort(item["children"])

    _sort(roots)
    return roots


async def list_people(
    session: AsyncSession,
    *,
    keyword: str | None,
    department_id: str | None,
    offset: int,
    limit: int,
) -> tuple[list[dict[str, Any]], int]:
    """Return current employees, optionally filtered by department subtree."""
    conditions: list[ColumnElement[bool]] = [
        EmployeeProfile.is_deleted.is_(False),
        EmployeeProfile.is_current.is_(True),
    ]

    if department_id:
        try:
            department_uuid = uuid.UUID(department_id)
        except ValueError as exc:
            raise BadRequestException("无效的部门 ID") from exc
        department = await session.get(HrDepartment, department_uuid)
        if department is None:
            return [], 0
        scope = await resolve_filter_department_ids(session, department.feishu_department_id)
        if scope is not None:
            if not scope:
                return [], 0
            conditions.append(
                or_(*[EmployeeProfile.department_ids.contains([feishu_id]) for feishu_id in sorted(scope)])
            )

    if keyword and keyword.strip():
        pattern = f"%{keyword.strip()}%"
        conditions.append(
            or_(
                EmployeeProfile.name.ilike(pattern),
                EmployeeProfile.employee_no.ilike(pattern),
                EmployeeProfile.mobile.ilike(pattern),
            )
        )

    total = (await session.execute(select(func.count()).select_from(EmployeeProfile).where(*conditions))).scalar_one()
    result = await session.execute(
        select(EmployeeProfile)
        .where(*conditions)
        .order_by(EmployeeProfile.name.asc(), EmployeeProfile.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    items = [
        {
            "id": str(profile.id),
            "name": profile.name,
            "employee_no": profile.employee_no,
            "job_title_name": profile.job_title_name,
            "department_names": list(profile.department_names or []),
            "department_path": [
                {"id": str(entry.get("id", "")), "name": str(entry.get("name", ""))}
                for entry in (profile.department_path or [])
                if isinstance(entry, dict)
            ],
            "avatar_url": _avatar(profile),
        }
        for profile in result.scalars().all()
    ]
    return items, int(total)
