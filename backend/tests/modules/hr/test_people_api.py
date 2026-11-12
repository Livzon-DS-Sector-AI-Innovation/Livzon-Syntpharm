"""HTTP seam for the 员工档案 personnel browser (ticket #198).

Observes only public API payloads against a transactional database: tree
selection, department/status/keyword filters, pagination and the full detail
payload (including “—” for empty values).
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hr.models import EmployeeProfile
from app.modules.hr.org_domain import IN_SCOPE_COMPANY_ID, IN_SCOPE_COMPANY_NAME
from app.platform.identity.models import Department

LIST_URL = "/api/v1/hr/people"
TREE_URL = "/api/v1/hr/people/departments"

ROOT = {"id": IN_SCOPE_COMPANY_ID, "name": IN_SCOPE_COMPANY_NAME}


def _department(dept_id: str, name: str, parent_id: str, path: list[dict[str, str]]) -> Department:
    return Department(
        feishu_department_id=dept_id,
        name=name,
        parent_feishu_department_id=parent_id,
        status_is_deleted=False,
        order=0,
        department_path=path,
    )


def _profile(
    open_id: str,
    name: str,
    *,
    department_ids: list[str],
    department_names: list[str],
    department_path: list[dict[str, str]],
    **overrides: Any,
) -> EmployeeProfile:
    payload: dict[str, Any] = {
        "open_id": open_id,
        "name": name,
        "mobile": "",
        "email": "",
        "enterprise_email": "",
        "email_aliases": [],
        "description": "",
        "avatar_72": "",
        "avatar_240": "",
        "avatar_640": "",
        "avatar_origin": "",
        "background_image": "",
        "geo_name": "",
        "resign_time": "",
        "employee_no": "",
        "job_title_id": "",
        "job_title_name": "",
        "work_country_or_region": "",
        "work_place_id": "",
        "work_place_name": "",
        "work_station": "",
        "extension_number": "",
        "dotted_line_leader_ids": [],
        "resign_type": "",
        "resign_reason": "",
        "resign_remark": "",
        "positions": [],
        "job_level_id": "",
        "job_level_name": "",
        "job_family_id": "",
        "job_family_name": "",
        "department_ids": department_ids,
        "department_names": department_names,
        "department_path": department_path,
        "last_synced_at": datetime(2026, 11, 12, 0, 0, tzinfo=UTC),
    }
    payload.update(overrides)
    return EmployeeProfile(**payload)


async def _seed(db_session: AsyncSession) -> None:
    level1_path = [ROOT, {"id": "od-101", "name": "101车间"}]
    level2_path = [ROOT, {"id": "od-101", "name": "101车间"}, {"id": "od-101-1", "name": "合成工段"}]
    level2b_path = [ROOT, {"id": "od-102", "name": "102车间"}, {"id": "od-102-1", "name": "精制工段"}]
    db_session.add_all(
        [
            _department("od-101", "101车间", IN_SCOPE_COMPANY_ID, level1_path),
            _department("od-101-1", "合成工段", "od-101", level2_path),
            _department("od-102", "102车间", IN_SCOPE_COMPANY_ID, [ROOT, {"id": "od-102", "name": "102车间"}]),
            _department("od-102-1", "精制工段", "od-102", level2b_path),
            _profile(
                "ou-zhang",
                "张三",
                department_ids=["od-101-1"],
                department_names=["101车间", "合成工段"],
                department_path=level2_path,
                employee_no="109000586",
                job_title_name="车间班长",
                staff_status=1,
                gender=2,
                mobile="13800000000",
                email="zhangsan@example.com",
                enterprise_email="zhangsan@livzon.cn",
                email_aliases=["zs@livzon.cn"],
                description="认真做事",
                avatar_240="https://a/240.png",
                background_image="https://bg.png",
                geo_name="cn",
                active_status=2,
                is_admin=True,
                data_source=1,
                hire_date=date(2018, 3, 6),
                employment_type=1,
                positions=[{"id": "P-1", "name": "班长"}],
                job_level_name="M1",
                job_family_name="生产序列",
            ),
            _profile(
                "ou-li",
                "李四",
                department_ids=["od-101"],
                department_names=["101车间"],
                department_path=level1_path,
                employee_no="109001832",
                job_title_name="工艺员",
                staff_status=2,
                is_resigned=True,
                resign_date=date(2026, 10, 1),
                resign_type="主动离职",
                resign_reason="个人原因",
            ),
            _profile(
                "ou-wang",
                "王五",
                department_ids=["od-102-1"],
                department_names=["102车间", "精制工段"],
                department_path=level2b_path,
                job_title_name="操作工",
                staff_status=1,
            ),
        ]
    )
    await db_session.flush()


class TestPeopleList:
    async def test_anonymous_is_rejected(self, anonymous_client: AsyncClient) -> None:
        response = await anonymous_client.get(LIST_URL)

        assert response.status_code == 401

    async def test_lists_all_in_scope_people_with_total_and_last_sync(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        await _seed(db_session)

        response = await auth_client.get(LIST_URL)

        assert response.status_code == 200
        body = response.json()
        assert {item["name"] for item in body["data"]["items"]} == {"张三", "李四", "王五"}
        assert body["meta"]["total"] == 3
        assert body["meta"]["page"] == 1
        assert body["data"]["last_synced_at"].startswith("2026-11-12")

    async def test_company_node_returns_all_people(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        await _seed(db_session)

        response = await auth_client.get(LIST_URL, params={"department_id": IN_SCOPE_COMPANY_ID})

        assert response.json()["meta"]["total"] == 3

    async def test_level_one_department_includes_its_level_two_people(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        await _seed(db_session)

        response = await auth_client.get(LIST_URL, params={"department_id": "od-101"})

        body = response.json()
        assert body["meta"]["total"] == 2
        assert {item["name"] for item in body["data"]["items"]} == {"张三", "李四"}

    async def test_level_two_department_filters_exactly(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        await _seed(db_session)

        response = await auth_client.get(LIST_URL, params={"department_id": "od-102-1"})

        body = response.json()
        assert body["meta"]["total"] == 1
        assert body["data"]["items"][0]["name"] == "王五"
        assert body["data"]["items"][0]["department_level1_name"] == "102车间"
        assert body["data"]["items"][0]["department_level2_name"] == "精制工段"

    async def test_status_filter_accepts_label_and_enum(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        await _seed(db_session)

        by_label = await auth_client.get(LIST_URL, params={"status": "离职"})
        by_enum = await auth_client.get(LIST_URL, params={"status": "2"})

        assert [item["name"] for item in by_label.json()["data"]["items"]] == ["李四"]
        assert [item["name"] for item in by_enum.json()["data"]["items"]] == ["李四"]

    async def test_keyword_matches_name_employee_no_job_title_and_department(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        await _seed(db_session)

        for keyword, expected in [
            ("张三", {"张三"}),
            ("109001832", {"李四"}),
            ("车间班长", {"张三"}),
            ("精制工段", {"王五"}),
        ]:
            response = await auth_client.get(LIST_URL, params={"keyword": keyword})
            assert {item["name"] for item in response.json()["data"]["items"]} == expected

    async def test_pagination_keeps_total(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        await _seed(db_session)

        response = await auth_client.get(LIST_URL, params={"page": 2, "page_size": 2})

        body = response.json()
        assert len(body["data"]["items"]) == 1
        assert body["meta"]["total"] == 3
        assert body["meta"]["page"] == 2


class TestPeopleTree:
    async def test_tree_is_two_levels_under_company_root(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        await _seed(db_session)

        response = await auth_client.get(TREE_URL)

        assert response.status_code == 200
        items = response.json()["data"]["items"]
        assert [node["name"] for node in items] == ["101车间", "102车间"]
        assert [child["name"] for child in items[0]["children"]] == ["合成工段"]


class TestPeopleDetail:
    async def test_detail_by_id_shows_every_group_and_labels(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        await _seed(db_session)
        profile = (
            await db_session.execute(select(EmployeeProfile).where(EmployeeProfile.open_id == "ou-zhang"))
        ).scalar_one()
        profile_id = str(profile.id)

        response = await auth_client.get(f"{LIST_URL}/{profile_id}")

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == "张三"
        assert data["open_id"] == "ou-zhang"
        assert data["gender_label"] == "女"
        assert data["staff_status_label"] == "在职"
        assert data["active_status_label"] == "已激活"
        assert data["data_source_label"] == "飞书"
        assert data["employee_no"] == "109000586"
        assert data["job_title_name"] == "车间班长"
        assert data["hire_date"] == "2018-03-06"
        assert data["department_level1_name"] == "101车间"
        assert data["department_level2_name"] == "合成工段"
        assert data["email_aliases"] == ["zs@livzon.cn"]
        assert data["positions"] == [{"id": "P-1", "name": "班长"}]
        assert data["job_level_name"] == "M1"
        assert data["job_family_name"] == "生产序列"

    async def test_detail_by_open_id_and_empty_values(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        await _seed(db_session)

        response = await auth_client.get(f"{LIST_URL}/ou-wang")

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == "王五"
        assert data["mobile"] == ""
        assert data["email_aliases"] == []
        assert data["description"] == ""
        assert data["hire_date"] is None
        assert data["work_place_name"] == ""
        assert data["dotted_line_leader_ids"] == []
        assert data["positions"] == []

    async def test_unknown_person_returns_404(self, auth_client: AsyncClient) -> None:
        response = await auth_client.get(f"{LIST_URL}/ou-missing")

        assert response.status_code == 404
