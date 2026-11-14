"""DB-backed personnel sync adapter test (ticket #198).

Verifies the sync port maps onto the real ``hr.employee_profiles`` mirror,
resolves department names/path from ``hr.departments``, scopes the department
ids passed to the Feishu filter, and records a real people count on the org
sync run.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hr.models import EmployeeProfile
from app.modules.hr.models import HrDepartment as Department
from app.modules.hr.models import HrOrgSyncRun as OrgSyncRun
from app.modules.hr.org_repository import SqlAlchemyOrgDepartmentStore
from app.modules.hr.org_sync import sync_org_departments
from app.modules.hr.people_repository import SqlAlchemyEmployeeProfileStore
from app.modules.hr.people_sync import sync_employee_profiles
from tests.fixtures.org_scope import DEFAULT_ORG_SCOPES, IN_SCOPE_COMPANY_ID, IN_SCOPE_COMPANY_NAME

ROOT = {"id": IN_SCOPE_COMPANY_ID, "name": IN_SCOPE_COMPANY_NAME}


class _EmployeeFetcher:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.department_requests: list[list[str]] = []

    async def fetch_employees_by_filter(self, department_ids: list[str]) -> list[dict[str, Any]]:
        self.department_requests.append(list(department_ids))
        return [self.payload] if department_ids else []


def _department(dept_id: str, name: str, parent_id: str, path: list[dict[str, str]]) -> Department:
    return Department(
        feishu_department_id=dept_id,
        name=name,
        parent_feishu_department_id=parent_id,
        status_is_deleted=False,
        order=0,
        level=max(len(path) - 1, 0) if path else None,
        department_path=path,
    )


async def test_sync_persists_profile_and_resolves_department_names_and_path(db_session: AsyncSession) -> None:
    level1_path = [ROOT, {"id": "od-101", "name": "101车间"}]
    level2_path = [ROOT, {"id": "od-101", "name": "101车间"}, {"id": "od-101-1", "name": "合成工段"}]
    db_session.add_all(
        [
            _department("od-101", "101车间", IN_SCOPE_COMPANY_ID, level1_path),
            _department("od-101-1", "合成工段", "od-101", level2_path),
        ]
    )
    await db_session.flush()
    fetcher = _EmployeeFetcher(
        {
            "base_info": {
                "employee_id": "ou-zhang",
                "name": {"name": {"default_value": "张三"}},
                "mobile": "13800000000",
                "departments": [
                    {"department_id": "od-101-1", "name": {"default_value": "合成工段"}},
                    {"department_id": "od-101", "name": {"default_value": "101车间"}},
                ],
            },
            "work_info": {
                "job_number": "109000586",
                "job_title": {"job_title_id": "jt-1", "job_title_name": {"default_value": "车间班长"}},
                "join_date": "2018-03-06",
                "staff_status": 1,
            },
        }
    )

    stats = await sync_employee_profiles(SqlAlchemyEmployeeProfileStore(db_session), fetcher)

    assert stats.total == 1
    profile = (
        await db_session.execute(select(EmployeeProfile).where(EmployeeProfile.open_id == "ou-zhang"))
    ).scalar_one()
    assert profile.name == "张三"
    assert profile.mobile == "13800000000"
    assert profile.employee_no == "109000586"
    assert profile.job_title_name == "车间班长"
    assert profile.hire_date == date(2018, 3, 6)
    assert profile.staff_status == 1
    assert profile.department_ids == ["od-101-1", "od-101"]
    assert profile.department_names == ["合成工段", "101车间"]
    assert profile.department_path == level2_path
    assert profile.last_synced_at is not None


async def test_scope_department_ids_exclude_company_root_hidden_and_trade(db_session: AsyncSession) -> None:
    db_session.add_all(
        [
            Department(
                feishu_department_id=IN_SCOPE_COMPANY_ID,
                name=IN_SCOPE_COMPANY_NAME,
                parent_feishu_department_id=None,
                level=0,
                status_is_deleted=False,
                order=0,
            ),
            _department("od-101", "101车间", IN_SCOPE_COMPANY_ID, [ROOT, {"id": "od-101", "name": "101车间"}]),
            _department(
                "od-101-1",
                "合成工段",
                "od-101",
                [ROOT, {"id": "od-101", "name": "101车间"}, {"id": "od-101-1", "name": "合成工段"}],
            ),
            Department(
                feishu_department_id="od-trade",
                name="贸易一部",
                parent_feishu_department_id="od-other-company",
                level=1,
                status_is_deleted=True,
                order=0,
            ),
        ]
    )
    await db_session.flush()

    ids = await SqlAlchemyEmployeeProfileStore(db_session).list_scope_department_ids()

    assert set(ids) == {IN_SCOPE_COMPANY_ID, "od-101", "od-101-1"}


async def test_org_sync_records_real_people_count(db_session: AsyncSession) -> None:
    await db_session.flush()

    class _DepartmentFetcher:
        async def fetch_departments(self) -> list[dict[str, Any]]:
            return [
                {
                    "department_id": "od-101",
                    "name": "101车间",
                    "parent_department_id": IN_SCOPE_COMPANY_ID,
                    "order": 1,
                }
            ]

        async def fetch_departments_detail(self, department_ids: list[str]) -> list[dict[str, Any]]:
            return [
                {
                    "department_id": "od-101",
                    "name": {"default_value": "101车间"},
                    "parent_department_id": IN_SCOPE_COMPANY_ID,
                    "department_path_infos": [
                        {
                            "department_id": IN_SCOPE_COMPANY_ID,
                            "department_name": {"default_value": IN_SCOPE_COMPANY_NAME},
                        },
                        {"department_id": "od-101", "department_name": {"default_value": "101车间"}},
                    ],
                    "department_count": {},
                }
            ]

    stats = await sync_org_departments(
        SqlAlchemyOrgDepartmentStore(db_session),
        _DepartmentFetcher(),
        people_store=SqlAlchemyEmployeeProfileStore(db_session),
        scopes=DEFAULT_ORG_SCOPES,
        people_fetcher=_EmployeeFetcher(
            {
                "base_info": {
                    "employee_id": "ou-zhang",
                    "name": {"name": {"default_value": "张三"}},
                    "departments": [{"department_id": "od-101"}],
                },
                "work_info": {"staff_status": 1},
            }
        ),
    )

    assert stats.people == 1
    run = (await db_session.execute(select(OrgSyncRun))).scalars().one()
    assert run.department_count == 1
    assert run.people_count == 1
