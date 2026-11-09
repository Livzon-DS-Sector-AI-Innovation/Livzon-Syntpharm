"""设备设施危险源台账 — HTTP 契约测试（#181）。

测试只从 HTTP 边界观察行为：状态码、响应体、持久化后的读取结果。
安全风险矩阵 5×5 全量取值、必填、L/S 取值、R 只读以及两张台账隔离都在这里覆盖。
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

BASE_URL = "/api/v1/safety/equipment-facility-hazards"
WORK_ACTIVITY_URL = "/api/v1/safety/work-activity-hazards"


def payload(**overrides: Any) -> dict[str, Any]:
    """构造一条合法的设备设施台账创建请求；L=2、S=C → R=11。"""
    data: dict[str, Any] = {
        "equipment_facility_tag": "R-101 反应釜",
        "inspection_item": "反应釜本体及附件",
        "inspection_standard": "无腐蚀、无泄漏，安全阀校验有效",
        "nonconformity_consequence": "物料泄漏，可能引发火灾或人员灼伤",
        "likelihood_l": 2,
        "severity_s": "C",
        "current_control_measures": ["engineering", "management"],
        "residual_risk": "level_2",
        "control_level": "101车间",
        "execution_level": "workshop",
        "improvement_measures": ["emergency"],
        "remarks": "季度检查重点设备",
    }
    data.update(overrides)
    return data


def work_activity_payload(**overrides: Any) -> dict[str, Any]:
    """构造一条合法的作业活动台账创建请求，用于隔离测试。"""
    data: dict[str, Any] = {
        "position_location": "101车间反应岗",
        "area_activity": "反应釜投料",
        "hazard_name_or_event": "溶剂泄漏",
        "possible_harm": "火灾、爆炸",
        "hazard_type": "化学性危险和有害因素",
        "likelihood_l": "3",
        "exposure_e": "6",
        "consequence_c": "15",
        "control_measures": ["engineering"],
        "residual_risk": "level_2",
        "control_level": "101车间",
        "execution_level": "workshop",
    }
    data.update(overrides)
    return data


async def create(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    response = await client.post(BASE_URL, json=payload(**overrides))
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert isinstance(data, dict)
    return data


class TestEquipmentFacilityHazardList:
    async def test_list_empty(self, auth_client: AsyncClient) -> None:
        response = await auth_client.get(BASE_URL)

        assert response.status_code == 200
        body = response.json()
        assert body["code"] == 200
        assert body["data"] == []
        assert body["meta"]["total"] == 0

    async def test_anonymous_is_rejected(self, anonymous_client: AsyncClient) -> None:
        response = await anonymous_client.get(BASE_URL)

        assert response.status_code == 401


class TestEquipmentFacilityHazardCreate:
    async def test_create_returns_all_fields_and_computed_r(self, auth_client: AsyncClient) -> None:
        data = await create(auth_client)

        assert data["equipment_facility_tag"] == "R-101 反应釜"
        assert data["inspection_item"] == "反应釜本体及附件"
        assert data["inspection_standard"] == "无腐蚀、无泄漏，安全阀校验有效"
        assert data["nonconformity_consequence"] == "物料泄漏，可能引发火灾或人员灼伤"
        assert data["likelihood_l"] == 2
        assert data["severity_s"] == "C"
        assert data["risk_evaluation_r"] == 11
        assert data["current_control_measures"] == ["engineering", "management"]
        assert data["residual_risk"] == "level_2"
        assert data["residual_risk_label"] == "2级一般风险"
        assert data["control_level"] == "101车间"
        assert data["execution_level"] == "workshop"
        assert data["improvement_measures"] == ["emergency"]
        assert data["remarks"] == "季度检查重点设备"
        assert data["id"]

    async def test_created_record_appears_in_list(self, auth_client: AsyncClient) -> None:
        created = await create(auth_client)

        response = await auth_client.get(BASE_URL)

        assert response.status_code == 200
        body = response.json()
        assert body["meta"]["total"] == 1
        assert [row["id"] for row in body["data"]] == [created["id"]]

    async def test_client_supplied_r_is_ignored(self, auth_client: AsyncClient) -> None:
        data = await create(auth_client, risk_evaluation_r=999)

        assert data["risk_evaluation_r"] == 11

        response = await auth_client.get(BASE_URL)
        assert response.status_code == 200
        assert response.json()["data"][0]["risk_evaluation_r"] == 11


MATRIX_CELLS = [
    (1, "A", 3),
    (2, "A", 5),
    (3, "A", 7),
    (4, "A", 10),
    (5, "A", 15),
    (1, "B", 5),
    (2, "B", 7),
    (3, "B", 10),
    (4, "B", 15),
    (5, "B", 23),
    (1, "C", 7),
    (2, "C", 11),
    (3, "C", 16),
    (4, "C", 23),
    (5, "C", 35),
    (1, "D", 17),
    (2, "D", 25),
    (3, "D", 37),
    (4, "D", 55),
    (5, "D", 81),
    (1, "E", 22),
    (2, "E", 32),
    (3, "E", 46),
    (4, "E", 68),
    (5, "E", 100),
]


class TestRiskEvaluationMatrix:
    @pytest.mark.parametrize(("likelihood", "severity", "expected"), MATRIX_CELLS)
    async def test_all_25_matrix_cells(
        self,
        auth_client: AsyncClient,
        likelihood: int,
        severity: str,
        expected: int,
    ) -> None:
        data = await create(auth_client, likelihood_l=likelihood, severity_s=severity)

        assert data["risk_evaluation_r"] == expected


REQUIRED_FIELDS = [
    "equipment_facility_tag",
    "inspection_item",
    "inspection_standard",
    "nonconformity_consequence",
    "likelihood_l",
    "severity_s",
    "current_control_measures",
    "residual_risk",
    "control_level",
    "execution_level",
    "improvement_measures",
    "remarks",
]


class TestRequiredFields:
    @pytest.mark.parametrize("field", REQUIRED_FIELDS)
    async def test_each_required_field_is_enforced(self, auth_client: AsyncClient, field: str) -> None:
        body = payload()
        body.pop(field)

        response = await auth_client.post(BASE_URL, json=body)

        assert response.status_code == 422, response.text
        assert field in response.text

    @pytest.mark.parametrize(
        "field",
        [
            "equipment_facility_tag",
            "inspection_item",
            "inspection_standard",
            "nonconformity_consequence",
            "remarks",
        ],
    )
    async def test_blank_text_is_rejected(self, auth_client: AsyncClient, field: str) -> None:
        response = await auth_client.post(BASE_URL, json=payload(**{field: "   "}))

        assert response.status_code == 422, response.text

    @pytest.mark.parametrize("field", ["current_control_measures", "improvement_measures"])
    async def test_empty_multi_select_is_rejected(self, auth_client: AsyncClient, field: str) -> None:
        response = await auth_client.post(BASE_URL, json=payload(**{field: []}))

        assert response.status_code == 422, response.text


class TestLikelihoodAndSeverityValidation:
    @pytest.mark.parametrize("value", [0, 6, -1, 2.5])
    async def test_invalid_likelihood_is_rejected(self, auth_client: AsyncClient, value: Any) -> None:
        response = await auth_client.post(BASE_URL, json=payload(likelihood_l=value))

        assert response.status_code == 422, response.text

    @pytest.mark.parametrize("value", ["F", "a", "Z", "", "AB"])
    async def test_invalid_severity_is_rejected(self, auth_client: AsyncClient, value: str) -> None:
        response = await auth_client.post(BASE_URL, json=payload(severity_s=value))

        assert response.status_code == 422, response.text

    @pytest.mark.parametrize("value", [1, 2, 3, 4, 5])
    async def test_likelihood_edges_are_accepted(self, auth_client: AsyncClient, value: int) -> None:
        data = await create(auth_client, likelihood_l=value)

        assert data["likelihood_l"] == value

    @pytest.mark.parametrize("value", ["A", "B", "C", "D", "E"])
    async def test_severity_edges_are_accepted(self, auth_client: AsyncClient, value: str) -> None:
        data = await create(auth_client, severity_s=value)

        assert data["severity_s"] == value


class TestOptionEnforcement:
    @pytest.mark.parametrize(
        "overrides",
        [
            {"current_control_measures": ["bogus"]},
            {"improvement_measures": ["engineering", "bogus"]},
            {"residual_risk": "level_4"},
            {"residual_risk": "4级重大风险"},
            {"control_level": "不存在的部门"},
            {"execution_level": "department"},
        ],
    )
    async def test_unknown_option_values_are_rejected(
        self, auth_client: AsyncClient, overrides: dict[str, Any]
    ) -> None:
        response = await auth_client.post(BASE_URL, json=payload(**overrides))

        assert response.status_code == 422, response.text

    async def test_all_measure_keys_are_accepted_in_order(self, auth_client: AsyncClient) -> None:
        keys = ["engineering", "management", "education", "ppe", "emergency"]

        data = await create(auth_client, current_control_measures=keys, improvement_measures=keys)

        assert data["current_control_measures"] == keys
        assert data["improvement_measures"] == keys

    @pytest.mark.parametrize(
        ("key", "label"),
        [
            ("level_1", "1级低风险"),
            ("level_2", "2级一般风险"),
            ("level_3", "3级较大风险"),
        ],
    )
    async def test_residual_risk_label_is_derived(self, auth_client: AsyncClient, key: str, label: str) -> None:
        data = await create(auth_client, residual_risk=key)

        assert data["residual_risk"] == key
        assert data["residual_risk_label"] == label


class TestLedgerIsolation:
    async def test_equipment_endpoint_does_not_expose_work_activity_fields(self, auth_client: AsyncClient) -> None:
        data = await create(
            auth_client,
            position_location="不应出现",
            area_activity="不应出现",
            hazard_name_or_event="不应出现",
            possible_harm="不应出现",
            hazard_type="不应出现",
            exposure_e="6",
            consequence_c="15",
            risk_value_d="270",
            evaluation_grade=3,
            control_measures=["engineering"],
        )

        for field in (
            "position_location",
            "area_activity",
            "hazard_name_or_event",
            "possible_harm",
            "hazard_type",
            "exposure_e",
            "consequence_c",
            "risk_value_d",
            "evaluation_grade",
            "control_measures",
        ):
            assert field not in data

    async def test_work_activity_endpoint_does_not_expose_equipment_fields(self, auth_client: AsyncClient) -> None:
        response = await auth_client.post(
            WORK_ACTIVITY_URL,
            json=work_activity_payload(
                equipment_facility_tag="不应出现",
                inspection_item="不应出现",
                inspection_standard="不应出现",
                nonconformity_consequence="不应出现",
                severity_s="C",
                risk_evaluation_r=11,
                current_control_measures=["engineering"],
                improvement_measures=["engineering"],
                remarks="不应出现",
            ),
        )

        assert response.status_code == 200, response.text
        data = response.json()["data"]
        for field in (
            "equipment_facility_tag",
            "inspection_item",
            "inspection_standard",
            "nonconformity_consequence",
            "severity_s",
            "risk_evaluation_r",
            "current_control_measures",
            "improvement_measures",
            "remarks",
        ):
            assert field not in data

    async def test_cross_ledger_payloads_are_rejected(self, auth_client: AsyncClient) -> None:
        equipment_into_work = await auth_client.post(WORK_ACTIVITY_URL, json=payload())
        work_into_equipment = await auth_client.post(BASE_URL, json=work_activity_payload())

        assert equipment_into_work.status_code == 422, equipment_into_work.text
        assert work_into_equipment.status_code == 422, work_into_equipment.text

    async def test_rows_stay_in_their_own_ledger(self, auth_client: AsyncClient) -> None:
        equipment = await create(auth_client)
        work = await auth_client.post(WORK_ACTIVITY_URL, json=work_activity_payload())
        assert work.status_code == 200, work.text
        work_id = work.json()["data"]["id"]

        equipment_list = await auth_client.get(BASE_URL)
        work_list = await auth_client.get(WORK_ACTIVITY_URL)

        assert equipment_list.status_code == 200
        assert work_list.status_code == 200
        assert [row["id"] for row in equipment_list.json()["data"]] == [equipment["id"]]
        assert [row["id"] for row in work_list.json()["data"]] == [work_id]
        assert equipment["id"] != work_id
