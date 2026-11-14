"""HTTP seam for the 部门管理 org browser (ticket #197).

These tests observe only the public API payloads, against a transactional
database. They cover the recursive multi-company tree shape, scope filtering, hidden rows,
leader-name rendering and the persisted sync status.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hr.models import EmployeeProfile
from app.modules.hr.models import HrDepartment as Department
from app.modules.hr.models import HrOrgSyncRun as OrgSyncRun
from app.platform.identity.models import User
from tests.fixtures.org_scope import IN_SCOPE_COMPANY_ID, IN_SCOPE_COMPANY_NAME

pytestmark = pytest.mark.usefixtures("org_scope_settings")

TREE_URL = "/api/v1/hr/org/departments"
STATUS_URL = "/api/v1/hr/org/sync-status"
SYNC_URL = "/api/v1/hr/org/sync"


def _company_child(
    dept_id: str,
    name: str,
    *,
    order: int,
    hidden: bool = False,
    leaders: list[str] | None = None,
) -> Department:
    return Department(
        feishu_department_id=dept_id,
        name=name,
        parent_feishu_department_id=IN_SCOPE_COMPANY_ID,
        status_is_deleted=hidden,
        order=order,
        order_weight=str(order),
        leader_ids=leaders or [],
        enabled_status=True,
        recursive_members_count=10,
        direct_members_count=4,
        recursive_departments_count=1,
        direct_departments_count=1,
        data_source=1,
        department_path=[
            {"id": IN_SCOPE_COMPANY_ID, "name": IN_SCOPE_COMPANY_NAME},
            {"id": dept_id, "name": name},
        ],
    )


def _child_of(parent_id: str, dept_id: str, name: str, *, order: int) -> Department:
    return Department(
        feishu_department_id=dept_id,
        name=name,
        parent_feishu_department_id=parent_id,
        status_is_deleted=False,
        order=order,
        order_weight=str(order),
        enabled_status=False,
        recursive_members_count=5,
        direct_members_count=5,
        recursive_departments_count=0,
        direct_departments_count=0,
        data_source=1,
        department_path=[
            {"id": IN_SCOPE_COMPANY_ID, "name": IN_SCOPE_COMPANY_NAME},
            {"id": parent_id, "name": "101车间"},
            {"id": dept_id, "name": name},
        ],
    )


class TestOrgDepartmentTree:
    async def test_anonymous_is_rejected(self, anonymous_client: AsyncClient) -> None:
        response = await anonymous_client.get(TREE_URL)

        assert response.status_code == 401

    async def test_empty_tree_still_renders_configured_company(self, auth_client: AsyncClient) -> None:
        response = await auth_client.get(TREE_URL)

        assert response.status_code == 200
        body = response.json()
        assert body["code"] == 200
        assert body["data"]["companies"] == [
            {"id": IN_SCOPE_COMPANY_ID, "name": IN_SCOPE_COMPANY_NAME},
        ]
        assert [node["name"] for node in body["data"]["items"]] == [IN_SCOPE_COMPANY_NAME]
        assert body["data"]["items"][0]["level"] == 0
        assert body["data"]["items"][0]["children"] == []

    async def test_tree_renders_all_levels_under_company_root(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        db_session.add_all(
            [
                _company_child("od-101", "101车间", order=2),
                _company_child("od-102", "102车间", order=1),
                _child_of("od-101", "od-101-1", "合成工段", order=2),
                _child_of("od-101", "od-101-2", "精制工段", order=1),
                _child_of("od-101-1", "od-101-1-1", "超深班组", order=1),
                _company_child("od-gone", "已撤销车间", order=3, hidden=True),
                Department(
                    feishu_department_id="od-trade",
                    name="贸易一部",
                    parent_feishu_department_id="od-other-company",
                    status_is_deleted=False,
                    order=0,
                    enabled_status=True,
                    department_path=[
                        {"id": "od-other-company", "name": "珠海市丽珠医药贸易有限公司"},
                        {"id": "od-trade", "name": "贸易一部"},
                    ],
                ),
            ]
        )
        await db_session.flush()

        response = await auth_client.get(TREE_URL)

        assert response.status_code == 200
        items = response.json()["data"]["items"]
        assert [node["name"] for node in items] == [IN_SCOPE_COMPANY_NAME]
        company = items[0]
        assert company["level"] == 0
        assert [node["name"] for node in company["children"]] == ["102车间", "101车间"]
        parent = company["children"][1]
        assert parent["level"] == 1
        assert parent["parent_name"] == IN_SCOPE_COMPANY_NAME
        assert [child["name"] for child in parent["children"]] == ["精制工段", "合成工段"]
        assert parent["children"][0]["level"] == 2
        assert parent["children"][1]["children"][0]["name"] == "超深班组"
        assert parent["children"][1]["children"][0]["level"] == 3
        assert all(node["name"] != "已撤销车间" for node in company["children"])
        assert all(node["name"] != "贸易一部" for node in company["children"])

    async def test_tree_exposes_counts_path_status_ordering_and_leader_name(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        db_session.add(
            _company_child("od-101", "101车间", order=3, leaders=["ou-leader", "ou-missing"]),
        )
        # Leaders resolve through the personnel mirror, not identity.users.
        db_session.add_all(
            [
                EmployeeProfile(open_id="ou-leader", name="张三"),
                User(name="错误来源", employee_no="E-1001", feishu_open_id="ou-leader"),
            ]
        )
        await db_session.flush()

        response = await auth_client.get(TREE_URL)

        node = response.json()["data"]["items"][0]["children"][0]
        assert node["id"] == "od-101"
        assert node["leader_ids"] == ["ou-leader", "ou-missing"]
        assert node["leader_names"] == ["张三"]
        assert node["leader_display"] == "张三"
        assert node["recursive_members_count"] == 10
        assert node["direct_members_count"] == 4
        assert node["recursive_departments_count"] == 1
        assert node["direct_departments_count"] == 1
        assert node["department_path"][0]["id"] == IN_SCOPE_COMPANY_ID
        assert node["department_path"][-1] == {"id": "od-101", "name": "101车间"}
        assert node["enabled_status"] is True
        assert node["order_weight"] == "3"
        assert node["data_source"] == "飞书"

    async def test_titles_without_leader_render_dash(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        db_session.add(_company_child("od-101", "101车间", order=1))
        await db_session.flush()

        response = await auth_client.get(TREE_URL)

        node = response.json()["data"]["items"][0]["children"][0]
        assert node["leader_names"] == []
        assert node["leader_display"] == "—"


class TestOrgSyncStatus:
    async def test_never_synced(self, auth_client: AsyncClient) -> None:
        response = await auth_client.get(STATUS_URL)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "never"
        assert data["last_synced_at"] is None
        assert data["department_count"] == 0
        assert data["people_count"] == 0
        assert data["error_message"] is None

    async def test_latest_run_is_returned(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        db_session.add_all(
            [
                OrgSyncRun(
                    status="success",
                    department_count=42,
                    people_count=495,
                    error_message=None,
                    started_at=datetime(2026, 11, 12, 0, 0, tzinfo=UTC),
                    finished_at=datetime(2026, 11, 12, 0, 1, tzinfo=UTC),
                ),
                OrgSyncRun(
                    status="failed",
                    department_count=0,
                    people_count=0,
                    error_message="飞书接口不可用",
                    started_at=datetime(2026, 11, 13, 0, 0, tzinfo=UTC),
                    finished_at=datetime(2026, 11, 13, 0, 1, tzinfo=UTC),
                ),
            ]
        )
        await db_session.flush()

        response = await auth_client.get(STATUS_URL)

        data: dict[str, Any] = response.json()["data"]
        assert data["status"] == "failed"
        assert data["department_count"] == 0
        assert data["people_count"] == 0
        assert data["error_message"] == "飞书接口不可用"
        assert data["last_synced_at"].startswith("2026-11-13")


class TestOrgSyncTrigger:
    async def test_running_run_is_returned_by_status(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        db_session.add(
            OrgSyncRun(
                status="running",
                department_count=0,
                people_count=0,
                error_message=None,
                started_at=datetime(2026, 11, 12, 0, 0, tzinfo=UTC),
                finished_at=None,
            )
        )
        await db_session.flush()

        response = await auth_client.get(STATUS_URL)

        assert response.json()["data"]["status"] == "running"
        assert response.json()["data"]["last_synced_at"].startswith("2026-11-12")

    async def test_manual_sync_records_running_and_returns_immediately(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
        monkeypatch: Any,
    ) -> None:
        from app.modules.hr import org_service

        submitted: list[tuple[str, Any]] = []

        async def _fake_submit(name: str, runner: Any) -> None:
            submitted.append((name, runner))

        monkeypatch.setattr(org_service, "submit_job", _fake_submit)

        response = await auth_client.post(SYNC_URL)

        assert response.status_code == 200
        assert response.json()["data"]["status"] == "running"
        assert submitted and submitted[0][0] == org_service.SYNC_JOB_NAME
        run = (await db_session.execute(select(OrgSyncRun))).scalars().one()
        assert run.status == "running"
        assert run.finished_at is None
