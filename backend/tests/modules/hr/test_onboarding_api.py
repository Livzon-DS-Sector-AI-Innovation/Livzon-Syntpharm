"""HTTP seam for the 2026 入职台账 (ticket #199).

Observes public API payloads against a transactional database: create,
update, soft delete, required-field validation, option validation, keyword
and department filters, and soft-delete visibility.
"""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hr.models import OnboardingRecord

LIST_URL = "/api/v1/hr/onboarding-records"


def _payload(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "serial_no": "260001",
        "department_level1": "头孢合成制造部",
        "department_level2": "201车间",
        "name": "张伟",
        "position": "车间班长",
        "position_level": "主管级",
        "personnel_identity": "正式工",
        "hire_date": "2026-10-08",
        "join_category": "校招",
        "education": "本科",
        "gender": "男",
        "age": 33,
        "mobile": "13800001024",
        "group_classification": "生产一线：管理",
    }
    data.update(overrides)
    return data


def _record(**overrides: Any) -> OnboardingRecord:
    from datetime import date

    values: dict[str, Any] = {
        "serial_no": "260002",
        "department_level1": "非头孢制造部",
        "department_level2": "102车间",
        "name": "李娜",
        "position": "反应岗位",
        "position_level": "员工级",
        "personnel_identity": "正式工",
        "hire_date": date(2026, 9, 22),
        "join_category": "社招",
        "education": "本科",
        "gender": "女",
        "age": 27,
        "mobile": "13900002048",
        "group_classification": "生产一线",
    }
    values.update(overrides)
    return OnboardingRecord(**values)


async def _seed(db_session: AsyncSession, *records: OnboardingRecord) -> None:
    db_session.add_all(records)
    await db_session.flush()


class TestOnboardingCreate:
    async def test_anonymous_is_rejected(self, anonymous_client: AsyncClient) -> None:
        response = await anonymous_client.post(LIST_URL, json=_payload())

        assert response.status_code == 401

    async def test_creates_record_and_returns_every_field(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        response = await auth_client.post(LIST_URL, json=_payload())

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"]
        assert data["serial_no"] == "260001"
        assert data["department_level1"] == "头孢合成制造部"
        assert data["department_level2"] == "201车间"
        assert data["name"] == "张伟"
        assert data["position"] == "车间班长"
        assert data["position_level"] == "主管级"
        assert data["personnel_identity"] == "正式工"
        assert data["hire_date"] == "2026-10-08"
        assert data["join_category"] == "校招"
        assert data["education"] == "本科"
        assert data["gender"] == "男"
        assert data["age"] == 33
        assert data["mobile"] == "13800001024"
        assert data["group_classification"] == "生产一线：管理"

    async def test_accepts_free_text_for_identity_fields(
        self,
        auth_client: AsyncClient,
    ) -> None:
        response = await auth_client.post(
            LIST_URL,
            json=_payload(
                serial_no="A-2026-0007",
                department_level1="自定义一级部门",
                department_level2="自定义二级部门",
                name="欧阳娜娜",
                position="新型合成岗",
            ),
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["serial_no"] == "A-2026-0007"
        assert data["department_level1"] == "自定义一级部门"
        assert data["department_level2"] == "自定义二级部门"
        assert data["position"] == "新型合成岗"

    async def test_rejects_missing_required_field(
        self,
        auth_client: AsyncClient,
    ) -> None:
        payload = _payload()
        payload.pop("mobile")

        response = await auth_client.post(LIST_URL, json=payload)

        assert response.status_code == 422

    async def test_rejects_blank_required_field(
        self,
        auth_client: AsyncClient,
    ) -> None:
        response = await auth_client.post(LIST_URL, json=_payload(name="   "))

        assert response.status_code == 422

    async def test_rejects_unknown_option(
        self,
        auth_client: AsyncClient,
    ) -> None:
        response = await auth_client.post(LIST_URL, json=_payload(position_level="专家级"))

        assert response.status_code == 422


class TestOnboardingList:
    async def test_lists_seeded_records(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        await _seed(db_session, _record(), _record(name="王强", serial_no="260003"))

        response = await auth_client.get(LIST_URL)

        assert response.status_code == 200
        body = response.json()
        assert body["meta"]["total"] == 2
        assert {item["name"] for item in body["data"]} == {"李娜", "王强"}

    async def test_keyword_filters_name_serial_and_position(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        await _seed(db_session, _record(), _record(name="王强", serial_no="260003", position="精制岗位"))

        response = await auth_client.get(LIST_URL, params={"keyword": "260003"})

        assert [item["name"] for item in response.json()["data"]] == ["王强"]

    async def test_department_filter_matches_both_levels(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        await _seed(
            db_session,
            _record(),
            _record(
                name="王强",
                serial_no="260003",
                department_level1="质量保证部",
                department_level2="质量研究室",
            ),
        )

        by_level1 = await auth_client.get(LIST_URL, params={"department": "质量保证部"})
        by_level2 = await auth_client.get(LIST_URL, params={"department": "102车间"})

        assert [item["name"] for item in by_level1.json()["data"]] == ["王强"]
        assert [item["name"] for item in by_level2.json()["data"]] == ["李娜"]

    async def test_soft_deleted_records_disappear_from_list(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        await _seed(db_session, _record())
        created = (await auth_client.post(LIST_URL, json=_payload())).json()["data"]

        await auth_client.delete(f"{LIST_URL}/{created['id']}")

        body = (await auth_client.get(LIST_URL)).json()
        assert body["meta"]["total"] == 1
        assert [item["name"] for item in body["data"]] == ["李娜"]


class TestOnboardingDetail:
    async def test_detail_returns_record(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        record = _record()
        await _seed(db_session, record)

        response = await auth_client.get(f"{LIST_URL}/{record.id}")

        assert response.status_code == 200
        assert response.json()["data"]["name"] == "李娜"

    async def test_unknown_id_returns_404(self, auth_client: AsyncClient) -> None:
        response = await auth_client.get(f"{LIST_URL}/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 404


class TestOnboardingUpdate:
    async def test_updates_record(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        record = _record()
        await _seed(db_session, record)

        response = await auth_client.put(
            f"{LIST_URL}/{record.id}",
            json={"position": "工艺员", "join_category": "内部推荐", "age": 28},
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["position"] == "工艺员"
        assert data["join_category"] == "内部推荐"
        assert data["age"] == 28

        refreshed = (await auth_client.get(f"{LIST_URL}/{record.id}")).json()["data"]
        assert refreshed["position"] == "工艺员"

    async def test_rejects_invalid_option_on_update(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        record = _record()
        await _seed(db_session, record)

        response = await auth_client.put(f"{LIST_URL}/{record.id}", json={"education": "中专"})

        assert response.status_code == 422

    async def test_rejects_blank_required_field_on_update(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        record = _record()
        await _seed(db_session, record)

        response = await auth_client.put(f"{LIST_URL}/{record.id}", json={"name": "  "})

        assert response.status_code == 422

    async def test_update_unknown_id_returns_404(self, auth_client: AsyncClient) -> None:
        response = await auth_client.put(
            f"{LIST_URL}/00000000-0000-0000-0000-000000000000",
            json={"position": "工艺员"},
        )

        assert response.status_code == 404


class TestOnboardingDelete:
    async def test_soft_deletes_record(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        record = _record()
        await _seed(db_session, record)

        response = await auth_client.delete(f"{LIST_URL}/{record.id}")

        assert response.status_code == 200
        stored = (
            await db_session.execute(select(OnboardingRecord).where(OnboardingRecord.id == record.id))
        ).scalar_one()
        assert stored.is_deleted is True

    async def test_deleted_record_detail_returns_404(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        record = _record()
        await _seed(db_session, record)

        await auth_client.delete(f"{LIST_URL}/{record.id}")

        response = await auth_client.get(f"{LIST_URL}/{record.id}")
        assert response.status_code == 404

    async def test_delete_unknown_id_returns_404(self, auth_client: AsyncClient) -> None:
        response = await auth_client.delete(f"{LIST_URL}/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 404
