"""HTTP seam for the 2026 离职台账 (ticket #200).

Observes public API payloads against a transactional database: the person
snapshot and its freeze after the profile changes, computed 司龄, create /
update / soft delete, validation, filters, and removal of the old Feishu
bitable sync.
"""

from __future__ import annotations

import importlib.util
import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hr.models import DepartureRecord, EmployeeProfile

LIST_URL = "/api/v1/hr/departure-records"

_COMPANY_PATH = [
    {"id": "od-company", "name": "珠海保税区丽珠合成制药有限公司"},
    {"id": "od-1", "name": "头孢合成制造部"},
    {"id": "od-2", "name": "201车间"},
]


def _profile(**overrides: Any) -> EmployeeProfile:
    values: dict[str, Any] = {
        "open_id": f"ou-{uuid.uuid4().hex[:8]}",
        "name": "张伟",
        "gender": 1,
        "education": "本科",
        "age": 33,
        "job_title_name": "车间班长",
        "hire_date": date(2019, 3, 15),
        "department_ids": ["od-2"],
        "department_names": ["201车间", "头孢合成制造部"],
        "department_path": _COMPANY_PATH,
        "staff_status": 1,
    }
    values.update(overrides)
    return EmployeeProfile(**values)


def _payload(profile: EmployeeProfile, **overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "person_id": str(profile.id),
        "position_level": "主管级",
        "personnel_identity": "正式工",
        "leave_date": "2026-10-31",
        "leave_category": "主动离职",
        "leave_reason": "个人发展",
        "education": "本科",
        "age": 33,
        "group_classification": "生产一线：管理",
    }
    data.update(overrides)
    return data


def _record(profile: EmployeeProfile, **overrides: Any) -> DepartureRecord:
    values: dict[str, Any] = {
        "person_id": profile.id,
        "department_level1": "头孢合成制造部",
        "department_level2": "201车间",
        "name": profile.name,
        "gender": "男",
        "position": "车间班长",
        "position_level": "主管级",
        "personnel_identity": "正式工",
        "hire_date": date(2019, 3, 15),
        "leave_date": date(2026, 10, 31),
        "leave_category": "主动离职",
        "leave_reason": "个人发展",
        "education": "本科",
        "age": 33,
        "tenure_years": Decimal("7.6"),
        "group_classification": "生产一线：管理",
    }
    values.update(overrides)
    return DepartureRecord(**values)


async def _seed(db_session: AsyncSession, *profiles: EmployeeProfile) -> None:
    db_session.add_all(profiles)
    await db_session.flush()


class TestDepartureCreate:
    async def test_anonymous_is_rejected(self, anonymous_client: AsyncClient) -> None:
        response = await anonymous_client.post(LIST_URL, json={})

        assert response.status_code == 401

    async def test_snapshots_person_and_computes_tenure(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        profile = _profile()
        await _seed(db_session, profile)

        response = await auth_client.post(LIST_URL, json=_payload(profile))

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"]
        assert data["person_id"] == str(profile.id)
        assert data["department_level1"] == "头孢合成制造部"
        assert data["department_level2"] == "201车间"
        assert data["name"] == "张伟"
        assert data["gender"] == "男"
        assert data["position"] == "车间班长"
        assert data["hire_date"] == "2019-03-15"
        assert data["leave_date"] == "2026-10-31"
        assert data["leave_category"] == "主动离职"
        assert data["leave_reason"] == "个人发展"
        assert data["education"] == "本科"
        assert data["age"] == 33
        assert data["tenure_years"] == 7.6
        assert data["group_classification"] == "生产一线：管理"

    async def test_snapshot_survives_later_profile_changes(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        profile = _profile()
        await _seed(db_session, profile)
        created = (await auth_client.post(LIST_URL, json=_payload(profile))).json()["data"]

        profile.department_path = [
            {"id": "od-company", "name": "珠海保税区丽珠合成制药有限公司"},
            {"id": "od-9", "name": "质量保证部"},
            {"id": "od-10", "name": "质量研究室"},
        ]
        profile.job_title_name = "质量研究员"
        profile.gender = 2
        profile.education = "硕士"
        profile.age = 34
        profile.hire_date = date(2021, 1, 1)
        await db_session.flush()

        detail = (await auth_client.get(f"{LIST_URL}/{created['id']}")).json()["data"]
        assert detail["department_level1"] == "头孢合成制造部"
        assert detail["department_level2"] == "201车间"
        assert detail["position"] == "车间班长"
        assert detail["gender"] == "男"
        assert detail["education"] == "本科"
        assert detail["age"] == 33
        assert detail["hire_date"] == "2019-03-15"
        assert detail["tenure_years"] == 7.6

    async def test_client_snapshot_fields_are_ignored_when_profile_selected(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        profile = _profile()
        await _seed(db_session, profile)

        response = await auth_client.post(
            LIST_URL,
            json=_payload(profile, department_level1="伪造部门", name="伪造姓名"),
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["department_level1"] == "头孢合成制造部"
        assert data["name"] == "张伟"

    async def test_rejects_missing_required_field(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        profile = _profile()
        await _seed(db_session, profile)
        payload = _payload(profile)
        payload.pop("leave_category")

        response = await auth_client.post(LIST_URL, json=payload)

        assert response.status_code == 422

    async def test_rejects_unknown_leave_category(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        profile = _profile()
        await _seed(db_session, profile)

        response = await auth_client.post(LIST_URL, json=_payload(profile, leave_category="辞职"))

        assert response.status_code == 422

    async def test_rejects_leave_date_before_hire_date(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        profile = _profile()
        await _seed(db_session, profile)

        response = await auth_client.post(LIST_URL, json=_payload(profile, leave_date="2018-01-01"))

        assert response.status_code == 422

    async def test_unknown_person_returns_404(self, auth_client: AsyncClient) -> None:
        payload = _payload(_profile())
        payload["person_id"] = str(uuid.uuid4())

        response = await auth_client.post(LIST_URL, json=payload)

        assert response.status_code == 404

    async def test_user_entered_education_and_age_allow_create_when_profile_lacks_them(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        profile = _profile(education="", age=None)
        await _seed(db_session, profile)

        payload = _payload(profile)
        payload.pop("education")
        payload.pop("age")
        payload["education"] = "硕士"
        payload["age"] = 41
        response = await auth_client.post(LIST_URL, json=payload)

        assert response.status_code == 200
        assert response.json()["data"]["education"] == "硕士"
        assert response.json()["data"]["age"] == 41

    async def test_profile_education_and_age_are_used_when_payload_omits_them(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        profile = _profile()
        await _seed(db_session, profile)

        payload = _payload(profile)
        payload.pop("education")
        payload.pop("age")
        response = await auth_client.post(LIST_URL, json=payload)

        assert response.status_code == 200
        assert response.json()["data"]["education"] == "本科"
        assert response.json()["data"]["age"] == 33

    async def test_missing_education_and_age_everywhere_is_rejected(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        profile = _profile(education="", age=None)
        await _seed(db_session, profile)

        payload = _payload(profile)
        payload.pop("education")
        payload.pop("age")
        response = await auth_client.post(LIST_URL, json=payload)

        assert response.status_code == 422


class TestDepartureList:
    async def test_lists_seeded_records(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        first = _profile()
        second = _profile(name="李娜")
        await _seed(db_session, first, second)
        db_session.add_all([_record(first), _record(second, name="李娜")])
        await db_session.flush()

        response = await auth_client.get(LIST_URL)

        assert response.status_code == 200
        body = response.json()
        assert body["meta"]["total"] == 2
        assert {item["name"] for item in body["data"]} == {"张伟", "李娜"}

    async def test_keyword_filters_name_department_and_position(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        first = _profile()
        second = _profile(name="李娜", job_title_name="反应岗位")
        await _seed(db_session, first, second)
        db_session.add_all([_record(first), _record(second, name="李娜", position="反应岗位")])
        await db_session.flush()

        response = await auth_client.get(LIST_URL, params={"keyword": "反应岗位"})

        assert [item["name"] for item in response.json()["data"]] == ["李娜"]

    async def test_department_filter_matches_both_levels(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        first = _profile()
        second = _profile(name="李娜")
        await _seed(db_session, first, second)
        db_session.add_all(
            [
                _record(first),
                _record(
                    second,
                    name="李娜",
                    department_level1="质量保证部",
                    department_level2="质量研究室",
                ),
            ]
        )
        await db_session.flush()

        by_level1 = await auth_client.get(LIST_URL, params={"department": "质量保证部"})
        by_level2 = await auth_client.get(LIST_URL, params={"department": "201车间"})

        assert [item["name"] for item in by_level1.json()["data"]] == ["李娜"]
        assert [item["name"] for item in by_level2.json()["data"]] == ["张伟"]


class TestDepartureDetail:
    async def test_detail_returns_record(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        profile = _profile()
        await _seed(db_session, profile)
        record = _record(profile)
        db_session.add(record)
        await db_session.flush()

        response = await auth_client.get(f"{LIST_URL}/{record.id}")

        assert response.status_code == 200
        assert response.json()["data"]["name"] == "张伟"

    async def test_unknown_id_returns_404(self, auth_client: AsyncClient) -> None:
        response = await auth_client.get(f"{LIST_URL}/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 404


class TestDepartureUpdate:
    async def test_updates_mutable_fields_and_recomputes_tenure(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        profile = _profile()
        await _seed(db_session, profile)
        record = _record(profile)
        db_session.add(record)
        await db_session.flush()

        response = await auth_client.put(
            f"{LIST_URL}/{record.id}",
            json={
                "leave_date": "2020-01-01",
                "leave_category": "被动离职",
                "leave_reason": "组织调整",
            },
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["leave_date"] == "2020-01-01"
        assert data["leave_category"] == "被动离职"
        assert data["leave_reason"] == "组织调整"
        assert data["tenure_years"] == 0.8
        assert data["department_level1"] == "头孢合成制造部"

    async def test_rejects_snapshot_field_on_update(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        profile = _profile()
        await _seed(db_session, profile)
        record = _record(profile)
        db_session.add(record)
        await db_session.flush()

        response = await auth_client.put(f"{LIST_URL}/{record.id}", json={"department_level1": "伪造部门"})

        assert response.status_code == 422

    async def test_rejects_invalid_option_on_update(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        profile = _profile()
        await _seed(db_session, profile)
        record = _record(profile)
        db_session.add(record)
        await db_session.flush()

        response = await auth_client.put(f"{LIST_URL}/{record.id}", json={"leave_category": "辞职"})

        assert response.status_code == 422

    async def test_update_unknown_id_returns_404(self, auth_client: AsyncClient) -> None:
        response = await auth_client.put(
            f"{LIST_URL}/00000000-0000-0000-0000-000000000000",
            json={"leave_reason": "个人发展"},
        )

        assert response.status_code == 404


class TestDepartureDelete:
    async def test_soft_deletes_record(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        profile = _profile()
        await _seed(db_session, profile)
        record = _record(profile)
        db_session.add(record)
        await db_session.flush()

        response = await auth_client.delete(f"{LIST_URL}/{record.id}")

        assert response.status_code == 200
        stored = (await db_session.execute(select(DepartureRecord).where(DepartureRecord.id == record.id))).scalar_one()
        assert stored.is_deleted is True

    async def test_deleted_rows_disappear_from_list_and_detail(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        profile = _profile()
        await _seed(db_session, profile)
        created = (await auth_client.post(LIST_URL, json=_payload(profile))).json()["data"]

        await auth_client.delete(f"{LIST_URL}/{created['id']}")

        body = (await auth_client.get(LIST_URL)).json()
        assert body["meta"]["total"] == 0
        assert (await auth_client.get(f"{LIST_URL}/{created['id']}")).status_code == 404

    async def test_create_without_profile_uses_manual_snapshot(self, auth_client: AsyncClient) -> None:
        payload = {
            "department_level1": "质量保证部",
            "department_level2": "质量研究室",
            "name": "历史人员",
            "gender": "女",
            "position": "质量研究员",
            "hire_date": "2020-01-01",
            "position_level": "员工级",
            "personnel_identity": "正式工",
            "leave_date": "2026-06-30",
            "leave_category": "主动离职",
            "leave_reason": "个人发展",
            "education": "硕士",
            "age": 35,
            "group_classification": "研发一线",
        }

        response = await auth_client.post(LIST_URL, json=payload)

        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert data["person_id"] is None
        assert data["name"] == "历史人员"
        assert data["department_level1"] == "质量保证部"
        assert data["department_level2"] == "质量研究室"
        assert data["position"] == "质量研究员"
        assert data["hire_date"] == "2020-01-01"
        assert data["tenure_years"] == 6.5

    async def test_manual_record_allows_blank_second_level_department(self, auth_client: AsyncClient) -> None:
        payload = {
            "department_level1": "安全环保部",
            "name": "无二级人员",
            "gender": "男",
            "position": "安全专员",
            "hire_date": "2021-05-01",
            "position_level": "员工级",
            "personnel_identity": "正式工",
            "leave_date": "2026-06-30",
            "leave_category": "主动离职",
            "leave_reason": "个人发展",
            "education": "本科",
            "age": 32,
            "group_classification": "职能管理",
        }

        response = await auth_client.post(LIST_URL, json=payload)

        assert response.status_code == 200, response.text
        assert response.json()["data"]["department_level2"] == ""

    async def test_profile_without_second_level_department_snapshots_blank(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        profile = _profile(
            department_path=[
                {"id": "od-company", "name": "珠海保税区丽珠合成制药有限公司"},
                {"id": "od-level1", "name": "头孢合成制造部"},
            ],
            department_names=["头孢合成制造部"],
        )
        await _seed(db_session, profile)

        response = await auth_client.post(LIST_URL, json=_payload(profile))

        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert data["department_level1"] == "头孢合成制造部"
        assert data["department_level2"] == ""

    async def test_manual_record_requires_snapshot_fields(self, auth_client: AsyncClient) -> None:
        payload = {
            "department_level1": "质量保证部",
            "position_level": "员工级",
            "personnel_identity": "正式工",
            "leave_date": "2026-06-30",
            "leave_category": "主动离职",
            "leave_reason": "个人发展",
            "education": "硕士",
            "age": 35,
            "group_classification": "研发一线",
        }

        response = await auth_client.post(LIST_URL, json=payload)

        assert response.status_code == 422, response.text

    async def test_delete_unknown_id_returns_404(self, auth_client: AsyncClient) -> None:
        response = await auth_client.delete(f"{LIST_URL}/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 404


class TestFeishuSyncRemoval:
    async def test_sync_endpoints_are_gone(self, auth_client: AsyncClient) -> None:
        sync_from_feishu = await auth_client.post(f"{LIST_URL}/sync-from-feishu")
        sync_status = await auth_client.get(f"{LIST_URL}/sync-status")

        assert sync_from_feishu.status_code in (404, 405)
        assert sync_status.status_code in (404, 422)

    def test_departure_bitable_datasources_are_removed(self) -> None:
        assert importlib.util.find_spec("app.modules.hr.feishu.departure_datasource") is None
        assert importlib.util.find_spec("app.platform.integrations.feishu.departure_datasource") is None
