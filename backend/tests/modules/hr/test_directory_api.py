"""HTTP seam for the HR public directory (ticket #219).

The directory is the single picker source for every module, so these tests
observe:
- anonymous access is rejected while any authenticated user is accepted;
- the directory routes carry no ``require_permission`` dependency (a quality or
  safety user must be able to open a picker without HR module permissions);
- the department tree is fully expanded and keyed by ``hr.departments.id``;
- people come from current rows only, with keyword and department-subtree
  filters.
"""

from __future__ import annotations

import inspect
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hr.models import EmployeeProfile
from app.modules.hr.models import HrDepartment as Department
from tests.fixtures.org_scope import IN_SCOPE_COMPANY_ID, IN_SCOPE_COMPANY_NAME

DEPARTMENTS_URL = "/api/v1/hr/directory/departments"
PEOPLE_URL = "/api/v1/hr/directory/people"


def _department(
    dept_id: str,
    name: str,
    parent_id: str | None,
    path: list[dict[str, str]],
    *,
    code: str | None = None,
    level: int | None = None,
) -> Department:
    return Department(
        feishu_department_id=dept_id,
        name=name,
        code=code,
        parent_feishu_department_id=parent_id,
        status_is_deleted=False,
        order=0,
        level=level,
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
        "education": "",
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
    }
    payload.update(overrides)
    return EmployeeProfile(**payload)


async def _seed(db_session: AsyncSession) -> None:
    root_path = [{"id": IN_SCOPE_COMPANY_ID, "name": IN_SCOPE_COMPANY_NAME}]
    level1_path = [*root_path, {"id": "od-101", "name": "101车间"}]
    level2_path = [*level1_path, {"id": "od-101-1", "name": "合成工段"}]
    db_session.add_all(
        [
            _department(IN_SCOPE_COMPANY_ID, IN_SCOPE_COMPANY_NAME, None, root_path, level=0),
            _department("od-101", "101车间", IN_SCOPE_COMPANY_ID, level1_path, level=1),
            _department("od-101-1", "合成工段", "od-101", level2_path, level=2),
            _profile(
                "ou-zhang",
                "张三",
                department_ids=["od-101-1"],
                department_names=["101车间", "合成工段"],
                department_path=level2_path,
                employee_no="109000586",
                job_title_name="车间班长",
                mobile="13800000000",
                avatar_240="https://a/240.png",
            ),
            _profile(
                "ou-li",
                "李四",
                department_ids=["od-101"],
                department_names=["101车间"],
                department_path=level1_path,
                employee_no="109001832",
                job_title_name="工艺员",
            ),
            # Removed from the directory: kept as history, must not be pickable.
            _profile(
                "ou-gone",
                "离职员工",
                department_ids=["od-101"],
                department_names=["101车间"],
                department_path=level1_path,
                employee_no="109999999",
                is_current=False,
            ),
        ]
    )
    await db_session.flush()


def _annotation_texts(route: Any) -> list[str]:
    return [str(parameter.annotation) for parameter in inspect.signature(route.endpoint).parameters.values()]


def test_directory_routes_do_not_require_hr_permission_codes() -> None:
    from app.modules.hr.directory_api import router as directory_router
    from app.modules.hr.people_api import router as people_router

    directory_annotations = [text for route in directory_router.routes for text in _annotation_texts(route)]
    people_annotations = [text for route in people_router.routes for text in _annotation_texts(route)]

    assert any("PermissionContext" in text for text in people_annotations)
    assert not any("PermissionContext" in text for text in directory_annotations)


class TestDirectoryAuth:
    async def test_anonymous_is_rejected(self, anonymous_client: AsyncClient) -> None:
        assert (await anonymous_client.get(DEPARTMENTS_URL)).status_code == 401
        assert (await anonymous_client.get(PEOPLE_URL)).status_code == 401

    async def test_any_authenticated_user_can_read(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        await _seed(db_session)

        assert (await auth_client.get(DEPARTMENTS_URL)).status_code == 200
        assert (await auth_client.get(PEOPLE_URL)).status_code == 200


class TestDirectoryDepartments:
    async def test_tree_is_fully_expanded_and_keyed_by_hr_uuid(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        await _seed(db_session)

        body = (await auth_client.get(DEPARTMENTS_URL)).json()
        roots = body["data"]["items"]

        assert len(roots) == 1
        root = roots[0]
        assert root["name"] == IN_SCOPE_COMPANY_NAME
        assert root["level"] == 0
        assert root["parent_id"] is None
        assert root["path_names"] == [IN_SCOPE_COMPANY_NAME]
        # Reference key is the HR UUID, not the Feishu open_department_id.
        assert root["id"] != IN_SCOPE_COMPANY_ID

        level1 = root["children"][0]
        assert level1["name"] == "101车间"
        assert level1["parent_id"] == root["id"]
        assert level1["path_names"] == [IN_SCOPE_COMPANY_NAME, "101车间"]

        level2 = level1["children"][0]
        assert level2["name"] == "合成工段"
        assert level2["level"] == 2
        assert level2["parent_id"] == level1["id"]

    async def test_hidden_departments_are_excluded(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        await _seed(db_session)
        hidden = _department(
            "od-hidden", "已隐藏部门", IN_SCOPE_COMPANY_ID, [{"id": "od-hidden", "name": "已隐藏部门"}]
        )
        hidden.status_is_deleted = True
        db_session.add(hidden)
        await db_session.flush()

        body = (await auth_client.get(DEPARTMENTS_URL)).json()

        assert "已隐藏部门" not in str(body)


class TestDirectoryPeople:
    async def test_only_current_rows_are_listed(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        await _seed(db_session)

        body = (await auth_client.get(PEOPLE_URL)).json()

        assert body["data"]["total"] == 2
        assert {item["name"] for item in body["data"]["items"]} == {"张三", "李四"}

    async def test_item_exposes_hr_profile_id_and_display_fields(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        await _seed(db_session)

        body = (await auth_client.get(PEOPLE_URL, params={"keyword": "张三"})).json()
        item = body["data"]["items"][0]

        assert item["employee_no"] == "109000586"
        assert item["job_title_name"] == "车间班长"
        assert item["department_names"] == ["101车间", "合成工段"]
        assert item["avatar_url"] == "https://a/240.png"
        assert item["id"] != "ou-zhang"

    async def test_department_filter_accepts_hr_uuid_and_includes_children(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        await _seed(db_session)
        tree = (await auth_client.get(DEPARTMENTS_URL)).json()["data"]["items"]
        level1_id = tree[0]["children"][0]["id"]

        body = (await auth_client.get(PEOPLE_URL, params={"department_id": level1_id})).json()

        assert body["data"]["total"] == 2
        assert {item["name"] for item in body["data"]["items"]} == {"张三", "李四"}

    async def test_invalid_department_id_is_rejected(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        await _seed(db_session)

        response = await auth_client.get(PEOPLE_URL, params={"department_id": "not-a-uuid"})

        assert response.status_code == 400
