"""作业活动危险源台账 — HTTP 契约测试（#179）。

测试只从 HTTP 边界观察行为：状态码、响应体、持久化后的读取结果。
LEC 规则、D≤20 闸门、等级边界与选项校验都在这里覆盖。
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient

BASE_URL = "/api/v1/safety/work-activity-hazards"

CONTROL_MEASURE_KEYS = ["engineering", "management", "education", "ppe", "emergency"]


def payload(**overrides: Any) -> dict[str, Any]:
    """构造一条合法的创建请求，D = 3×6×15 = 270 → 3 级。"""
    data: dict[str, Any] = {
        "position_location": "101车间反应岗",
        "area_activity": "反应釜投料",
        "hazard_name_or_event": "溶剂泄漏",
        "possible_harm": "火灾、爆炸",
        "hazard_type": "化学性危险和有害因素",
        "likelihood_l": "3",
        "exposure_e": "6",
        "consequence_c": "15",
        "control_measures": ["engineering", "management", "emergency"],
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


class TestWorkActivityHazardList:
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


class TestWorkActivityHazardCreate:
    async def test_create_returns_all_fields_and_computed_values(self, auth_client: AsyncClient) -> None:
        data = await create(auth_client)

        assert data["position_location"] == "101车间反应岗"
        assert data["area_activity"] == "反应釜投料"
        assert data["hazard_name_or_event"] == "溶剂泄漏"
        assert data["possible_harm"] == "火灾、爆炸"
        assert data["hazard_type"] == "化学性危险和有害因素"
        assert Decimal(data["likelihood_l"]) == Decimal("3")
        assert Decimal(data["exposure_e"]) == Decimal("6")
        assert Decimal(data["consequence_c"]) == Decimal("15")
        assert Decimal(data["risk_value_d"]) == Decimal("270")
        assert data["evaluation_grade"] == 3
        assert data["evaluation_grade_label"] == "3级"
        assert data["control_measures"] == ["engineering", "management", "emergency"]
        assert data["residual_risk"] == "level_2"
        assert data["residual_risk_label"] == "2级一般风险"
        assert data["control_level"] == "101车间"
        assert data["execution_level"] == "workshop"
        assert data["id"]

    async def test_created_record_appears_in_list(self, auth_client: AsyncClient) -> None:
        created = await create(auth_client)

        response = await auth_client.get(BASE_URL)

        assert response.status_code == 200
        body = response.json()
        assert body["meta"]["total"] == 1
        assert [row["id"] for row in body["data"]] == [created["id"]]

    async def test_client_supplied_d_and_grade_are_ignored(self, auth_client: AsyncClient) -> None:
        data = await create(
            auth_client,
            risk_value_d="1",
            evaluation_grade=1,
            evaluation_grade_label="1级",
        )

        assert Decimal(data["risk_value_d"]) == Decimal("270")
        assert data["evaluation_grade"] == 3
        assert data["evaluation_grade_label"] == "3级"

    async def test_d_is_exact_decimal_product_without_rounding(self, auth_client: AsyncClient) -> None:
        # 0.3 × 0.7 × 100 = 21 exactly；浮点运算可能得到 20.999999…，
        # 该值若被舍入会跌到 D≤20 的拒绝区。
        data = await create(
            auth_client,
            likelihood_l="0.3",
            exposure_e="0.7",
            consequence_c="100",
        )

        assert Decimal(data["risk_value_d"]) == Decimal("21")
        assert data["evaluation_grade"] == 1


REQUIRED_FIELDS = [
    "position_location",
    "area_activity",
    "hazard_name_or_event",
    "possible_harm",
    "hazard_type",
    "likelihood_l",
    "exposure_e",
    "consequence_c",
    "control_measures",
    "residual_risk",
    "control_level",
    "execution_level",
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
            "position_location",
            "area_activity",
            "hazard_name_or_event",
            "possible_harm",
            "hazard_type",
            "control_level",
        ],
    )
    async def test_blank_text_is_rejected(self, auth_client: AsyncClient, field: str) -> None:
        response = await auth_client.post(BASE_URL, json=payload(**{field: "   "}))

        assert response.status_code == 422, response.text

    async def test_empty_control_measures_is_rejected(self, auth_client: AsyncClient) -> None:
        response = await auth_client.post(BASE_URL, json=payload(control_measures=[]))

        assert response.status_code == 422, response.text


class TestRangeValidation:
    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("likelihood_l", "0.09"),
            ("likelihood_l", "10.01"),
            ("exposure_e", "0.49"),
            ("exposure_e", "10.01"),
            ("consequence_c", "0"),
            ("consequence_c", "101"),
        ],
    )
    async def test_out_of_range_values_are_rejected(self, auth_client: AsyncClient, field: str, value: str) -> None:
        response = await auth_client.post(BASE_URL, json=payload(**{field: value}))

        assert response.status_code == 422, response.text

    @pytest.mark.parametrize(
        "overrides",
        [
            {"likelihood_l": "0.1", "exposure_e": "10", "consequence_c": "100"},
            {"likelihood_l": "10", "exposure_e": "0.5", "consequence_c": "100"},
            {"likelihood_l": "10", "exposure_e": "10", "consequence_c": "1"},
            {"likelihood_l": "10", "exposure_e": "10", "consequence_c": "100"},
        ],
    )
    async def test_range_edges_are_accepted(self, auth_client: AsyncClient, overrides: dict[str, str]) -> None:
        response = await auth_client.post(BASE_URL, json=payload(**overrides))

        assert response.status_code == 200, response.text


class TestDGatesAndGrades:
    @pytest.mark.parametrize("c_value", ["19", "20"])
    async def test_d_at_or_below_20_is_rejected(self, auth_client: AsyncClient, c_value: str) -> None:
        response = await auth_client.post(
            BASE_URL,
            json=payload(likelihood_l="1", exposure_e="1", consequence_c=c_value),
        )

        assert response.status_code == 400, response.text
        assert c_value in response.text
        assert "20" in response.text

    async def test_d_above_20_is_accepted(self, auth_client: AsyncClient) -> None:
        response = await auth_client.post(
            BASE_URL,
            json=payload(likelihood_l="1", exposure_e="1", consequence_c="21"),
        )

        assert response.status_code == 200, response.text
        assert response.json()["data"]["evaluation_grade"] == 1

    @pytest.mark.parametrize(
        ("l_value", "e_value", "c_value", "expected_grade"),
        [
            ("0.7", "1", "100", 1),  # D = 70  → 1 级（边界归低档）
            ("0.71", "1", "100", 2),  # D = 71  → 2 级
            ("1.6", "1", "100", 2),  # D = 160 → 2 级（边界归低档）
            ("1.61", "1", "100", 3),  # D = 161 → 3 级
            ("3.2", "1", "100", 3),  # D = 320 → 3 级（边界归低档）
            ("3.21", "1", "100", 4),  # D = 321 → 4 级
        ],
    )
    async def test_grade_boundaries(
        self,
        auth_client: AsyncClient,
        l_value: str,
        e_value: str,
        c_value: str,
        expected_grade: int,
    ) -> None:
        data = await create(
            auth_client,
            likelihood_l=l_value,
            exposure_e=e_value,
            consequence_c=c_value,
        )

        assert data["evaluation_grade"] == expected_grade
        assert data["evaluation_grade_label"] == f"{expected_grade}级"


class TestOptionEnforcement:
    @pytest.mark.parametrize(
        "overrides",
        [
            {"control_measures": ["bogus"]},
            {"control_measures": ["engineering", "bogus"]},
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

    async def test_all_control_measure_keys_are_accepted_in_order(self, auth_client: AsyncClient) -> None:
        data = await create(auth_client, control_measures=CONTROL_MEASURE_KEYS)

        assert data["control_measures"] == CONTROL_MEASURE_KEYS

    async def test_all_28_departments_are_accepted(self, auth_client: AsyncClient) -> None:
        departments = [
            "106车间",
            "AI创新部",
            "人事行政部",
            "动力部",
            "201车间",
            "202车间",
            "头孢合成制造部公共岗",
            "溶剂回收车间",
            "301车间",
            "302车间",
            "303车间",
            "头孢无菌制造部公共岗",
            "安全中心",
            "环保中心",
            "技术研发部",
            "注册部",
            "仓库",
            "生产部办公室",
            "设备工程部",
            "财务部",
            "质量保证部",
            "质量控制部",
            "采购部",
            "101车间",
            "102车间",
            "103车间",
            "105车间",
            "非头孢制造部公共岗",
        ]
        assert len(departments) == 28

        for department in departments:
            response = await auth_client.post(BASE_URL, json=payload(control_level=department))
            assert response.status_code == 200, f"{department}: {response.text}"

    async def test_team_leader_execution_level_is_accepted(self, auth_client: AsyncClient) -> None:
        data = await create(auth_client, execution_level="team_leader")

        assert data["execution_level"] == "team_leader"

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
