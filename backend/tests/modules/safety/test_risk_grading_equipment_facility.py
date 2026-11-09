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


# ── #182：编辑 / 软删除 / 筛选 / .xlsx 导出 ─────────────────────────────

from io import BytesIO  # noqa: E402

import openpyxl  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.modules.safety.api.permission_map import SAFETY_RESOURCE_CODES, resolve_code  # noqa: E402
from app.modules.safety.models import EquipmentFacilityHazard  # noqa: E402

EXPORT_URL = f"{BASE_URL}/export"

EXPORT_HEADERS = [
    "序号",
    "设备设施/位号",
    "检查项目",
    "检查标准",
    "不符合标准情况及后果",
    "可能性L",
    "严重性S",
    "危险评价R",
    "现有管控措施",
    "建议改进（新增）措施",
    "残余风险",
    "管控层级",
    "执行层级",
    "备注",
]


async def create_variant(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    """创建一条记录，用于筛选/导出用例。"""
    return await create(client, **overrides)


class TestEquipmentFacilityHazardDetail:
    async def test_get_detail_returns_record(self, auth_client: AsyncClient) -> None:
        created = await create(auth_client)

        response = await auth_client.get(f"{BASE_URL}/{created['id']}")

        assert response.status_code == 200, response.text
        assert response.json()["data"]["id"] == created["id"]
        assert response.json()["data"]["risk_evaluation_r"] == 11

    async def test_get_missing_detail_returns_404(self, auth_client: AsyncClient) -> None:
        response = await auth_client.get(f"{BASE_URL}/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 404, response.text


class TestEquipmentFacilityHazardUpdate:
    async def test_put_recomputes_r_and_ignores_client_value(self, auth_client: AsyncClient) -> None:
        created = await create(auth_client)

        response = await auth_client.put(
            f"{BASE_URL}/{created['id']}",
            json=payload(likelihood_l=5, severity_s="E", risk_evaluation_r=999),
        )

        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert data["likelihood_l"] == 5
        assert data["severity_s"] == "E"
        assert data["risk_evaluation_r"] == 100
        assert data["equipment_facility_tag"] == created["equipment_facility_tag"]

    async def test_put_reapplies_all_create_rules(self, auth_client: AsyncClient) -> None:
        created = await create(auth_client)

        blank = await auth_client.put(f"{BASE_URL}/{created['id']}", json=payload(remarks="   "))
        assert blank.status_code == 422, blank.text

        bad_option = await auth_client.put(f"{BASE_URL}/{created['id']}", json=payload(residual_risk="level_4"))
        assert bad_option.status_code == 422, bad_option.text

        empty_measures = await auth_client.put(f"{BASE_URL}/{created['id']}", json=payload(current_control_measures=[]))
        assert empty_measures.status_code == 422, empty_measures.text

    async def test_patch_partial_update_recomputes_from_merged_values(self, auth_client: AsyncClient) -> None:
        created = await create(auth_client)

        response = await auth_client.patch(f"{BASE_URL}/{created['id']}", json={"severity_s": "E"})

        assert response.status_code == 200, response.text
        data = response.json()["data"]
        # L 仍为 2，S 改为 E → R = 32
        assert data["likelihood_l"] == 2
        assert data["severity_s"] == "E"
        assert data["risk_evaluation_r"] == 32
        assert data["inspection_item"] == created["inspection_item"]

    async def test_patch_ignores_client_supplied_r(self, auth_client: AsyncClient) -> None:
        created = await create(auth_client)

        response = await auth_client.patch(
            f"{BASE_URL}/{created['id']}", json={"likelihood_l": 4, "risk_evaluation_r": 1}
        )

        assert response.status_code == 200, response.text
        # L=4、S=C → R = 23，客户端传入的 R 被忽略
        assert response.json()["data"]["risk_evaluation_r"] == 23

    async def test_update_missing_record_returns_404(self, auth_client: AsyncClient) -> None:
        missing = "00000000-0000-0000-0000-000000000000"

        response = await auth_client.put(f"{BASE_URL}/{missing}", json=payload())
        assert response.status_code == 404, response.text

        response = await auth_client.patch(f"{BASE_URL}/{missing}", json={"severity_s": "A"})
        assert response.status_code == 404, response.text


class TestEquipmentFacilityHazardSoftDelete:
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

        row = await db_session.scalar(
            select(EquipmentFacilityHazard).where(EquipmentFacilityHazard.id == created["id"])
        )
        assert row is not None
        assert row.is_deleted is True

    async def test_delete_missing_record_returns_404(self, auth_client: AsyncClient) -> None:
        response = await auth_client.delete(f"{BASE_URL}/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 404, response.text

    async def test_delete_anonymous_is_rejected(self, anonymous_client: AsyncClient) -> None:
        response = await anonymous_client.delete(f"{BASE_URL}/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 401


class TestEquipmentFacilityHazardFilters:
    async def test_each_filter_works_alone_and_combined(self, auth_client: AsyncClient) -> None:
        await create_variant(
            auth_client, equipment_facility_tag="101-EQ", control_level="101车间", residual_risk="level_1"
        )
        await create_variant(
            auth_client,
            equipment_facility_tag="201-EQ",
            control_level="201车间",
            residual_risk="level_2",
            likelihood_l=5,
            severity_s="E",
        )
        await create_variant(
            auth_client,
            equipment_facility_tag="301-EQ",
            control_level="301车间",
            residual_risk="level_3",
        )

        by_level = await auth_client.get(BASE_URL, params={"control_level": "201车间"})
        assert by_level.status_code == 200
        assert by_level.json()["meta"]["total"] == 1
        assert by_level.json()["data"][0]["equipment_facility_tag"] == "201-EQ"

        by_residual = await auth_client.get(BASE_URL, params={"residual_risk": "level_3"})
        assert by_residual.status_code == 200
        assert by_residual.json()["meta"]["total"] == 1
        assert by_residual.json()["data"][0]["equipment_facility_tag"] == "301-EQ"

        combined = await auth_client.get(BASE_URL, params={"control_level": "201车间", "residual_risk": "level_2"})
        assert combined.status_code == 200
        assert combined.json()["meta"]["total"] == 1
        assert combined.json()["data"][0]["equipment_facility_tag"] == "201-EQ"

        excluded = await auth_client.get(BASE_URL, params={"control_level": "201车间", "residual_risk": "level_3"})
        assert excluded.status_code == 200
        assert excluded.json()["meta"]["total"] == 0

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
    async def test_keyword_searches_every_text_field(self, auth_client: AsyncClient, field: str) -> None:
        marker = f"KEYWORD-{field}"
        await create_variant(auth_client, **{field: f"{marker} 文本"})
        await create_variant(auth_client, equipment_facility_tag="无关键字设备")

        response = await auth_client.get(BASE_URL, params={"keyword": marker})

        assert response.status_code == 200
        assert response.json()["meta"]["total"] == 1
        assert response.json()["data"][0][field] == f"{marker} 文本"

    async def test_keyword_combines_with_other_filters(self, auth_client: AsyncClient) -> None:
        await create_variant(auth_client, equipment_facility_tag="MATCH-EQ", control_level="101车间")
        await create_variant(auth_client, equipment_facility_tag="MATCH-EQ", control_level="201车间")

        response = await auth_client.get(BASE_URL, params={"keyword": "MATCH-EQ", "control_level": "201车间"})

        assert response.status_code == 200
        assert response.json()["meta"]["total"] == 1
        assert response.json()["data"][0]["control_level"] == "201车间"


class TestEquipmentFacilityHazardExport:
    async def test_export_returns_xlsx_with_chinese_headers_and_filtered_rows(self, auth_client: AsyncClient) -> None:
        await create_variant(auth_client, equipment_facility_tag="导出命中设备", control_level="201车间")
        await create_variant(auth_client, equipment_facility_tag="导出排除设备", control_level="101车间")

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
        assert sheet.cell(row=2, column=2).value == "导出命中设备"
        assert str(sheet.cell(row=2, column=8).value) == "11"

    async def test_export_honors_keyword_and_combined_filters(self, auth_client: AsyncClient) -> None:
        await create_variant(
            auth_client,
            equipment_facility_tag="组合命中设备",
            inspection_item="组合关键字",
            control_level="201车间",
            residual_risk="level_2",
        )
        await create_variant(
            auth_client,
            equipment_facility_tag="组合排除设备",
            inspection_item="组合关键字",
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
        assert sheet.cell(row=2, column=2).value == "组合命中设备"

    async def test_export_route_is_authorized_as_read_only(self) -> None:
        read_code, _write_code = SAFETY_RESOURCE_CODES["equipment-facility-hazards"]

        assert resolve_code("GET", "/api/v1/safety/equipment-facility-hazards/export") == read_code
        assert resolve_code("GET", "/api/v1/safety/equipment-facility-hazards/export/") == read_code
