"""DB-backed org sync adapter test (ticket #197).

Verifies that the sync port maps onto the real ``identity.departments`` mirror
and persists the run log, not just into the in-memory fake used by the unit seam.
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_model import ModuleSetting
from app.modules.hr.models import HrDepartment as Department
from app.modules.hr.models import HrOrgSyncRun as OrgSyncRun
from app.modules.hr.org_repository import SqlAlchemyOrgDepartmentStore
from app.modules.hr.org_settings import ORG_SYNC_ROOT_ID_SETTING, ORG_SYNC_ROOT_NAME_SETTING, load_org_scope
from app.modules.hr.org_sync import sync_org_departments
from tests.fixtures.org_scope import DEFAULT_ORG_SCOPE, IN_SCOPE_COMPANY_ID, IN_SCOPE_COMPANY_NAME


class _Fetcher:
    async def fetch_departments(self) -> list[dict[str, Any]]:
        return [
            {
                "department_id": "od-101",
                "name": "101车间",
                "parent_department_id": IN_SCOPE_COMPANY_ID,
                "order": 5,
            }
        ]

    async def fetch_departments_detail(self, department_ids: list[str]) -> list[dict[str, Any]]:
        return [
            {
                "department_id": "od-101",
                "name": {"default_value": "101车间"},
                "parent_department_id": IN_SCOPE_COMPANY_ID,
                "enabled_status": True,
                "order_weight": "5",
                "leaders": [{"leader_id": "ou-leader"}],
                "department_count": {
                    "recursive_members_count": "20",
                    "direct_members_count": "8",
                    "recursive_departments_count": "2",
                    "direct_departments_count": "2",
                },
                "department_path_infos": [
                    {
                        "department_id": IN_SCOPE_COMPANY_ID,
                        "department_name": {"default_value": IN_SCOPE_COMPANY_NAME},
                    },
                    {"department_id": "od-101", "department_name": {"default_value": "101车间"}},
                ],
                "data_source": 1,
                "custom_field_values": [],
            }
        ]


async def test_sync_persists_mirror_fields_and_hides_stale_department(db_session: AsyncSession) -> None:
    db_session.add(
        Department(
            feishu_department_id="od-stale",
            name="已移除车间",
            parent_feishu_department_id=IN_SCOPE_COMPANY_ID,
            status_is_deleted=False,
            department_path=[
                {"id": IN_SCOPE_COMPANY_ID, "name": IN_SCOPE_COMPANY_NAME},
                {"id": "od-stale", "name": "已移除车间"},
            ],
        )
    )
    await db_session.flush()
    store = SqlAlchemyOrgDepartmentStore(db_session)

    stats = await sync_org_departments(store, _Fetcher(), scope=DEFAULT_ORG_SCOPE)

    assert stats.total == 1
    assert stats.created == 1
    assert stats.hidden == 1

    department = (
        await db_session.execute(select(Department).where(Department.feishu_department_id == "od-101"))
    ).scalar_one()
    assert department.name == "101车间"
    assert department.parent_feishu_department_id == IN_SCOPE_COMPANY_ID
    assert department.leader_ids == ["ou-leader"]
    assert department.recursive_members_count == 20
    assert department.direct_members_count == 8
    assert department.recursive_departments_count == 2
    assert department.direct_departments_count == 2
    assert department.enabled_status is True
    assert department.order_weight == "5"
    assert department.data_source == 1
    assert (department.department_path or [])[-1] == {"id": "od-101", "name": "101车间"}
    assert department.directory_synced_at is not None

    stale = (
        await db_session.execute(select(Department).where(Department.feishu_department_id == "od-stale"))
    ).scalar_one()
    assert stale.status_is_deleted is True

    run = (await db_session.execute(select(OrgSyncRun))).scalars().one()
    assert run.status == "success"
    assert run.department_count == 1
    assert run.people_count == 0
    assert run.finished_at is not None


async def test_load_org_scope_reads_runtime_settings(db_session: AsyncSession) -> None:
    db_session.add_all(
        [
            ModuleSetting(module="hr", key=ORG_SYNC_ROOT_ID_SETTING, value="od-configured-root"),
            ModuleSetting(module="hr", key=ORG_SYNC_ROOT_NAME_SETTING, value="配置的公司"),
        ]
    )
    await db_session.flush()

    scope = await load_org_scope(db_session)

    assert scope.department_id == "od-configured-root"
    assert scope.department_name == "配置的公司"


async def test_failed_sync_rolls_back_department_writes_and_records_failure(db_session: AsyncSession) -> None:
    db_session.add(
        Department(
            feishu_department_id="od-stale",
            name="已移除车间",
            parent_feishu_department_id=IN_SCOPE_COMPANY_ID,
            status_is_deleted=False,
            department_path=[
                {"id": IN_SCOPE_COMPANY_ID, "name": IN_SCOPE_COMPANY_NAME},
                {"id": "od-stale", "name": "已移除车间"},
            ],
        )
    )
    await db_session.commit()

    class _FailingStore(SqlAlchemyOrgDepartmentStore):
        async def hide_department(self, department_id: str) -> None:
            raise RuntimeError("database write failed")

    with pytest.raises(RuntimeError, match="database write failed"):
        await sync_org_departments(_FailingStore(db_session), _Fetcher(), scope=DEFAULT_ORG_SCOPE)

    created = (
        await db_session.execute(select(Department).where(Department.feishu_department_id == "od-101"))
    ).scalar_one_or_none()
    stale = (
        await db_session.execute(select(Department).where(Department.feishu_department_id == "od-stale"))
    ).scalar_one()
    assert created is None
    assert stale.status_is_deleted is False
    run = (await db_session.execute(select(OrgSyncRun).order_by(OrgSyncRun.started_at.desc()))).scalars().first()
    assert run is not None
    assert run.status == "failed"
    assert "database write failed" in (run.error_message or "")
