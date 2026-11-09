"""风险分级管控台账 service：作业活动危险源（LEC）。"""

from __future__ import annotations

import uuid
from decimal import Decimal
from io import BytesIO
from typing import Any

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.modules.safety.models import EquipmentFacilityHazard, WorkActivityHazard
from app.modules.safety.repository import SafetyRepository
from app.modules.safety.risk_grading import (
    CONTROL_MEASURE_OPTIONS,
    EQUIPMENT_MEASURE_LABELS,
    MIN_RISK_VALUE,
    RESIDUAL_RISK_LABELS,
    compute_risk_value,
    derive_evaluation_grade,
    lookup_risk_evaluation,
    quantize_decimal,
)
from app.modules.safety.schemas.risk_grading import (
    EquipmentFacilityHazardCreate,
    WorkActivityHazardCreate,
)
from app.modules.safety.service._helpers import audit_log

CONTROL_MEASURE_LABELS: dict[str, str] = {item["key"]: item["label"] for item in CONTROL_MEASURE_OPTIONS}

EXPORT_HEADERS: tuple[str, ...] = (
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
)


class WorkActivityHazardService:
    """作业活动危险源台账业务逻辑。"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = SafetyRepository(session)

    async def list_hazards(
        self,
        skip: int,
        limit: int | None,
        control_level: str | None = None,
        evaluation_grade: int | None = None,
        residual_risk: str | None = None,
        keyword: str | None = None,
    ) -> tuple[list[WorkActivityHazard], int]:
        return await self.repo.get_work_activity_hazards(
            skip,
            limit,
            control_level=control_level,
            evaluation_grade=evaluation_grade,
            residual_risk=residual_risk,
            keyword=keyword,
        )

    async def get_hazard(self, hazard_id: uuid.UUID) -> WorkActivityHazard:
        item = await self.repo.get_work_activity_hazard_by_id(hazard_id)
        if item is None:
            raise NotFoundException(resource="作业活动危险源记录", resource_id=str(hazard_id))
        return item

    def _compute_payload(self, values: WorkActivityHazardCreate) -> dict[str, Any]:
        """按 create 规则校验后的完整字段重算 D / 评价级别 / 标签。"""
        likelihood_l = quantize_decimal(values.likelihood_l)
        exposure_e = quantize_decimal(values.exposure_e)
        consequence_c = quantize_decimal(values.consequence_c)
        risk_value = compute_risk_value(likelihood_l, exposure_e, consequence_c)
        if risk_value <= MIN_RISK_VALUE:
            raise BadRequestException(f"风险值 D={risk_value} 必须大于 20，不允许提交")
        grade, grade_label = derive_evaluation_grade(risk_value)

        payload: dict[str, Any] = values.model_dump()
        payload.update(
            likelihood_l=likelihood_l,
            exposure_e=exposure_e,
            consequence_c=consequence_c,
            risk_value_d=risk_value,
            evaluation_grade=grade,
            evaluation_grade_label=grade_label,
            residual_risk_label=RESIDUAL_RISK_LABELS[values.residual_risk],
        )
        return payload

    async def create_hazard(self, data: WorkActivityHazardCreate) -> WorkActivityHazard:
        payload = self._compute_payload(data)
        item = await self.repo.create_work_activity_hazard(payload)
        await audit_log(self.session, "create", "work_activity_hazard", resource_id=item.id)
        return item

    async def update_hazard(self, hazard_id: uuid.UUID, data: WorkActivityHazardCreate) -> WorkActivityHazard:
        """完整更新（PUT）：重新套用全部创建规则并重算 D / 评价级别。"""
        payload = self._compute_payload(data)

        item = await self.repo.update_work_activity_hazard(hazard_id, payload)
        if item is None:
            raise NotFoundException(resource="作业活动危险源记录", resource_id=str(hazard_id))
        await audit_log(self.session, "update", "work_activity_hazard", resource_id=item.id)
        return item

    async def delete_hazard(self, hazard_id: uuid.UUID) -> None:
        deleted = await self.repo.delete_work_activity_hazard(hazard_id)
        if not deleted:
            raise NotFoundException(resource="作业活动危险源记录", resource_id=str(hazard_id))
        await audit_log(self.session, "delete", "work_activity_hazard", resource_id=hazard_id)

    async def export_hazards(
        self,
        control_level: str | None = None,
        evaluation_grade: int | None = None,
        residual_risk: str | None = None,
        keyword: str | None = None,
    ) -> bytes:
        """按与列表相同的筛选条件生成 .xlsx 文件内容。"""
        items, _ = await self.list_hazards(
            skip=0,
            limit=None,
            control_level=control_level,
            evaluation_grade=evaluation_grade,
            residual_risk=residual_risk,
            keyword=keyword,
        )
        return build_work_activity_hazard_workbook(items)


def _format_decimal(value: Decimal) -> str:
    """去掉 Numeric 定标带来的尾随零，输出精确十进制文本。"""
    return format(value.normalize(), "f")


def _build_hazard_workbook(sheet_title: str, headers: tuple[str, ...], rows: list[list[Any]]) -> bytes:
    """把两张台账共用的表头样式、边框、列宽与写盘集中到一处。"""
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = sheet_title

    header_font = Font(name="微软雅黑", bold=True, size=11, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell_font = Font(name="微软雅黑", size=10)
    cell_alignment = Alignment(vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9"),
    )

    for col_idx, header in enumerate(headers, 1):
        cell = sheet.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    for row_idx, values in enumerate(rows, 2):
        for col_idx, value in enumerate(values, 1):
            cell = sheet.cell(row=row_idx, column=col_idx, value=value)
            cell.font = cell_font
            cell.alignment = cell_alignment
            cell.border = thin_border

    for col_idx in range(1, len(headers) + 1):
        sheet.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = 22

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def build_work_activity_hazard_workbook(items: list[WorkActivityHazard]) -> bytes:
    """生成作业活动危险源台账 Excel（中文表头 + 计算列）。"""
    rows: list[list[Any]] = []
    for row_no, item in enumerate(items, 1):
        measure_labels = "；".join(CONTROL_MEASURE_LABELS.get(key, key) for key in item.control_measures)
        rows.append(
            [
                row_no,
                item.position_location,
                item.area_activity,
                item.hazard_name_or_event,
                item.possible_harm,
                item.hazard_type,
                _format_decimal(item.likelihood_l),
                _format_decimal(item.exposure_e),
                _format_decimal(item.consequence_c),
                _format_decimal(item.risk_value_d),
                item.evaluation_grade_label,
                measure_labels,
                item.residual_risk_label,
                item.control_level,
                item.execution_level,
            ]
        )
    return _build_hazard_workbook("作业活动危险源台账", EXPORT_HEADERS, rows)


class EquipmentFacilityHazardService:
    """设备设施危险源台账业务逻辑（安全风险矩阵）。"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = SafetyRepository(session)

    async def list_hazards(
        self,
        skip: int,
        limit: int | None,
        control_level: str | None = None,
        residual_risk: str | None = None,
        keyword: str | None = None,
    ) -> tuple[list[EquipmentFacilityHazard], int]:
        return await self.repo.get_equipment_facility_hazards(
            skip,
            limit,
            control_level=control_level,
            residual_risk=residual_risk,
            keyword=keyword,
        )

    async def get_hazard(self, hazard_id: uuid.UUID) -> EquipmentFacilityHazard:
        item = await self.repo.get_equipment_facility_hazard_by_id(hazard_id)
        if item is None:
            raise NotFoundException(resource="设备设施危险源记录", resource_id=str(hazard_id))
        return item

    @staticmethod
    def _compute_payload(values: EquipmentFacilityHazardCreate) -> dict[str, Any]:
        """按完整字段重新查矩阵得出 R，并派生残余风险标签。"""
        payload = values.model_dump()
        payload.update(
            risk_evaluation_r=lookup_risk_evaluation(values.likelihood_l, values.severity_s),
            residual_risk_label=RESIDUAL_RISK_LABELS[values.residual_risk],
        )
        return payload

    async def create_hazard(self, data: EquipmentFacilityHazardCreate) -> EquipmentFacilityHazard:
        payload = self._compute_payload(data)
        item = await self.repo.create_equipment_facility_hazard(payload)
        await audit_log(self.session, "create", "equipment_facility_hazard", resource_id=item.id)
        return item

    async def update_hazard(self, hazard_id: uuid.UUID, data: EquipmentFacilityHazardCreate) -> EquipmentFacilityHazard:
        """完整更新（PUT）：重新套用全部创建规则并按 L/S 重算 R。"""
        payload = self._compute_payload(data)

        item = await self.repo.update_equipment_facility_hazard(hazard_id, payload)
        if item is None:
            raise NotFoundException(resource="设备设施危险源记录", resource_id=str(hazard_id))
        await audit_log(self.session, "update", "equipment_facility_hazard", resource_id=item.id)
        return item

    async def delete_hazard(self, hazard_id: uuid.UUID) -> None:
        deleted = await self.repo.delete_equipment_facility_hazard(hazard_id)
        if not deleted:
            raise NotFoundException(resource="设备设施危险源记录", resource_id=str(hazard_id))
        await audit_log(self.session, "delete", "equipment_facility_hazard", resource_id=hazard_id)

    async def export_hazards(
        self,
        control_level: str | None = None,
        residual_risk: str | None = None,
        keyword: str | None = None,
    ) -> bytes:
        """按与列表相同的筛选条件生成 .xlsx 文件内容。"""
        items, _ = await self.list_hazards(
            skip=0,
            limit=None,
            control_level=control_level,
            residual_risk=residual_risk,
            keyword=keyword,
        )
        return build_equipment_facility_hazard_workbook(items)


EQUIPMENT_EXPORT_HEADERS: tuple[str, ...] = (
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
)


def build_equipment_facility_hazard_workbook(items: list[EquipmentFacilityHazard]) -> bytes:
    """生成设备设施危险源台账 Excel（中文表头 + 查表计算的危险评价 R）。"""
    rows: list[list[Any]] = []
    for row_no, item in enumerate(items, 1):
        current_measures = "；".join(EQUIPMENT_MEASURE_LABELS.get(key, key) for key in item.current_control_measures)
        improvement_measures = "；".join(EQUIPMENT_MEASURE_LABELS.get(key, key) for key in item.improvement_measures)
        rows.append(
            [
                row_no,
                item.equipment_facility_tag,
                item.inspection_item,
                item.inspection_standard,
                item.nonconformity_consequence,
                item.likelihood_l,
                item.severity_s,
                item.risk_evaluation_r,
                current_measures,
                improvement_measures,
                item.residual_risk_label,
                item.control_level,
                item.execution_level,
                item.remarks,
            ]
        )
    return _build_hazard_workbook("设备设施危险源台账", EQUIPMENT_EXPORT_HEADERS, rows)
