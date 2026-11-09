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


# ── #180：编辑 / 软删除 / 筛选 / .xlsx 导出 ─────────────────────────────

from io import BytesIO  # noqa: E402

import openpyxl  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.modules.safety.api.permission_map import SAFETY_RESOURCE_CODES, resolve_code  # noqa: E402
from app.modules.safety.models import WorkActivityHazard  # noqa: E402

EXPORT_URL = f"{BASE_URL}/export"

EXPORT_HEADERS = [
    "序号",
    "岗位/地点",
    "区域/活动",
    "危险源名称或潜在事件",
    "可能导致的危害",
    "危险源类型",
    "可能性L",
    "发生频次E",
    "后果C",
    "风险值D",
    "评价级别",
    "控制措施",
    "残余风险",
    "管控层级",
    "执行层级",
]


async def create_variant(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    """创建一条记录，用于筛选/导出用例。"""
    return await create(client, **overrides)


class TestWorkActivityHazardUpdate:
    async def test_put_recomputes_d_and_grade_and_ignores_client_values(self, auth_client: AsyncClient) -> None:
        created = await create(auth_client)

        body = payload(
            likelihood_l="4",
            exposure_e="7",
            consequence_c="20",
            risk_value_d="1",
            evaluation_grade=1,
            evaluation_grade_label="1级",
        )
        response = await auth_client.put(f"{BASE_URL}/{created['id']}", json=body)

        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert Decimal(data["risk_value_d"]) == Decimal("560")
        assert data["evaluation_grade"] == 4
        assert data["evaluation_grade_label"] == "4级"
        assert Decimal(data["likelihood_l"]) == Decimal("4")
        assert Decimal(data["consequence_c"]) == Decimal("20")

    async def test_patch_partial_update_recomputes_from_merged_values(self, auth_client: AsyncClient) -> None:
        created = await create(auth_client)

        response = await auth_client.patch(f"{BASE_URL}/{created['id']}", json={"consequence_c": "100"})

        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert Decimal(data["risk_value_d"]) == Decimal("1800")
        assert data["evaluation_grade"] == 4
        assert data["position_location"] == created["position_location"]
        assert data["area_activity"] == created["area_activity"]

    async def test_update_reapplies_d_gate(self, auth_client: AsyncClient) -> None:
        created = await create(auth_client)

        response = await auth_client.put(
            f"{BASE_URL}/{created['id']}",
            json=payload(likelihood_l="1", exposure_e="1", consequence_c="20"),
        )

        assert response.status_code == 400, response.text
        assert "20" in response.text

    async def test_update_reapplies_option_validation(self, auth_client: AsyncClient) -> None:
        created = await create(auth_client)

        response = await auth_client.put(
            f"{BASE_URL}/{created['id']}",
            json=payload(residual_risk="level_4"),
        )

        assert response.status_code == 422, response.text

    async def test_update_missing_record_returns_404(self, auth_client: AsyncClient) -> None:
        missing = "00000000-0000-0000-0000-000000000000"

        response = await auth_client.put(f"{BASE_URL}/{missing}", json=payload())

        assert response.status_code == 404, response.text


class TestWorkActivityHazardSoftDelete:
    async def test_deleted_record_leaves_list_and_detail_but_stays_in_table(
        self,
        auth_client: AsyncClient,
        db_session: Any,
    ) -> None:
        created = await create(auth_client)

        response = await auth_client.delete(f"{BASE_URL}/{created['id']}")
        assert response.status_code == 200, response.text
        assert response.json()["message"] == "删除成功"

        list_response = await auth_client.get(BASE_URL)
        assert list_response.status_code == 200
        assert list_response.json()["meta"]["total"] == 0
        assert list_response.json()["data"] == []

        detail_response = await auth_client.get(f"{BASE_URL}/{created['id']}")
        assert detail_response.status_code == 404

        row = await db_session.scalar(select(WorkActivityHazard).where(WorkActivityHazard.id == created["id"]))
        assert row is not None
        assert row.is_deleted is True

    async def test_delete_missing_record_returns_404(self, auth_client: AsyncClient) -> None:
        missing = "00000000-0000-0000-0000-000000000000"

        response = await auth_client.delete(f"{BASE_URL}/{missing}")

        assert response.status_code == 404, response.text

    async def test_delete_anonymous_is_rejected(self, anonymous_client: AsyncClient) -> None:
        response = await anonymous_client.delete(f"{BASE_URL}/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 401


class TestWorkActivityHazardFilters:
    async def test_each_filter_works_alone_and_combined(self, auth_client: AsyncClient) -> None:
        await create_variant(
            auth_client, position_location="101车间A岗", control_level="101车间", residual_risk="level_1"
        )
        await create_variant(
            auth_client,
            position_location="201车间B岗",
            control_level="201车间",
            residual_risk="level_2",
            likelihood_l="4",
            exposure_e="7",
            consequence_c="20",
        )
        await create_variant(
            auth_client,
            position_location="301车间C岗",
            control_level="301车间",
            residual_risk="level_3",
            likelihood_l="1",
            exposure_e="1",
            consequence_c="21",
        )

        by_level = await auth_client.get(BASE_URL, params={"control_level": "201车间"})
        assert by_level.status_code == 200
        assert by_level.json()["meta"]["total"] == 1
        assert by_level.json()["data"][0]["position_location"] == "201车间B岗"

        by_grade = await auth_client.get(BASE_URL, params={"evaluation_grade": 4})
        assert by_grade.status_code == 200
        assert by_grade.json()["meta"]["total"] == 1
        assert by_grade.json()["data"][0]["position_location"] == "201车间B岗"

        by_residual = await auth_client.get(BASE_URL, params={"residual_risk": "level_3"})
        assert by_residual.status_code == 200
        assert by_residual.json()["meta"]["total"] == 1
        assert by_residual.json()["data"][0]["position_location"] == "301车间C岗"

        combined = await auth_client.get(
            BASE_URL,
            params={"control_level": "201车间", "residual_risk": "level_2", "evaluation_grade": 4},
        )
        assert combined.status_code == 200
        assert combined.json()["meta"]["total"] == 1
        assert combined.json()["data"][0]["position_location"] == "201车间B岗"

        excluded = await auth_client.get(BASE_URL, params={"control_level": "201车间", "residual_risk": "level_3"})
        assert excluded.status_code == 200
        assert excluded.json()["meta"]["total"] == 0

    @pytest.mark.parametrize(
        "field",
        [
            "position_location",
            "area_activity",
            "hazard_name_or_event",
            "possible_harm",
            "hazard_type",
        ],
    )
    async def test_keyword_searches_every_text_field(self, auth_client: AsyncClient, field: str) -> None:
        marker = f"KEYWORD-{field}"
        await create_variant(auth_client, **{field: f"{marker} 文本"})
        await create_variant(auth_client, position_location="无关键字岗位")

        response = await auth_client.get(BASE_URL, params={"keyword": marker})

        assert response.status_code == 200
        assert response.json()["meta"]["total"] == 1
        assert response.json()["data"][0][field] == f"{marker} 文本"

    async def test_keyword_combines_with_other_filters(self, auth_client: AsyncClient) -> None:
        await create_variant(auth_client, position_location="MATCH岗位", control_level="101车间")
        await create_variant(auth_client, position_location="MATCH岗位", control_level="201车间")

        response = await auth_client.get(
            BASE_URL,
            params={"keyword": "MATCH", "control_level": "201车间"},
        )

        assert response.status_code == 200
        assert response.json()["meta"]["total"] == 1
        assert response.json()["data"][0]["control_level"] == "201车间"


class TestWorkActivityHazardExport:
    async def test_export_returns_xlsx_with_chinese_headers_and_filtered_rows(self, auth_client: AsyncClient) -> None:
        await create_variant(auth_client, position_location="导出命中岗", control_level="201车间")
        await create_variant(auth_client, position_location="导出排除岗", control_level="101车间")

        response = await auth_client.get(EXPORT_URL, params={"control_level": "201车间"})

        assert response.status_code == 200, response.text
        assert response.headers["content-type"].startswith(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        disposition = response.headers["content-disposition"]
        assert "attachment" in disposition.lower()
        assert ".xlsx" in disposition

        workbook = openpyxl.load_workbook(BytesIO(response.content))
        sheet = workbook.active
        headers = [cell.value for cell in sheet[1]]
        assert headers == EXPORT_HEADERS
        assert sheet.max_row == 2
        assert sheet.cell(row=2, column=2).value == "导出命中岗"
        assert str(sheet.cell(row=2, column=10).value) == "270"
        assert sheet.cell(row=2, column=11).value == "3级"

    async def test_export_honors_keyword_and_combined_filters(self, auth_client: AsyncClient) -> None:
        await create_variant(
            auth_client,
            position_location="组合命中岗",
            hazard_name_or_event="组合关键字",
            control_level="201车间",
            residual_risk="level_2",
        )
        await create_variant(
            auth_client,
            position_location="组合排除岗",
            hazard_name_or_event="组合关键字",
            control_level="201车间",
            residual_risk="level_3",
        )

        response = await auth_client.get(
            EXPORT_URL,
            params={"keyword": "组合关键字", "control_level": "201车间", "residual_risk": "level_2"},
        )

        assert response.status_code == 200, response.text
        sheet = openpyxl.load_workbook(BytesIO(response.content)).active
        assert sheet.max_row == 2
        assert sheet.cell(row=2, column=2).value == "组合命中岗"

    async def test_export_route_is_authorized_as_read_only(self) -> None:
        read_code, _write_code = SAFETY_RESOURCE_CODES["work-activity-hazards"]

        assert resolve_code("GET", "/api/v1/safety/work-activity-hazards/export") == read_code
        assert resolve_code("GET", "/api/v1/safety/work-activity-hazards/export/") == read_code


class TestWorkActivityHazardDetail:
    async def test_get_detail_returns_record(self, auth_client: AsyncClient) -> None:
        created = await create(auth_client)

        response = await auth_client.get(f"{BASE_URL}/{created['id']}")

        assert response.status_code == 200, response.text
        assert response.json()["data"]["id"] == created["id"]

    async def test_get_missing_detail_returns_404(self, auth_client: AsyncClient) -> None:
        response = await auth_client.get(f"{BASE_URL}/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 404, response.text

    async def test_put_blank_text_is_rejected(self, auth_client: AsyncClient) -> None:
        created = await create(auth_client)

        response = await auth_client.put(f"{BASE_URL}/{created['id']}", json=payload(area_activity="   "))

        assert response.status_code == 422, response.text
