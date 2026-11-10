"""风险分级管控台账 schema：作业活动危险源台账（LEC）。"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.modules.safety.risk_grading import (
    CONSEQUENCE_MAX,
    CONSEQUENCE_MIN,
    CONTROL_MEASURE_KEYS,
    EQUIPMENT_MEASURE_LABELS,
    EXECUTION_LEVEL_KEYS,
    EXPOSURE_MAX,
    EXPOSURE_MIN,
    LIKELIHOOD_MAX,
    LIKELIHOOD_MIN,
    RESIDUAL_RISK_KEYS,
    RISK_GRADING_DEPARTMENTS,
    SEVERITY_LEVELS,
    quantize_decimal,
)

RequiredShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
RequiredLongText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]


def _validate_control_measures_value(value: list[str]) -> list[str]:
    unknown = [key for key in value if key not in CONTROL_MEASURE_KEYS]
    if unknown:
        raise ValueError(f"控制措施包含未知选项: {', '.join(unknown)}")
    if not value:
        raise ValueError("控制措施至少选择一项")
    return value


def _validate_residual_risk_value(value: str) -> str:
    if value not in RESIDUAL_RISK_KEYS:
        raise ValueError(f"残余风险必须是以下之一: {', '.join(sorted(RESIDUAL_RISK_KEYS))}")
    return value


def _validate_control_level_value(value: str) -> str:
    if value not in RISK_GRADING_DEPARTMENTS:
        raise ValueError("管控层级不在允许的部门列表中")
    return value


def _validate_execution_level_value(value: str) -> str:
    if value not in EXECUTION_LEVEL_KEYS:
        raise ValueError(f"执行层级必须是以下之一: {', '.join(sorted(EXECUTION_LEVEL_KEYS))}")
    return value


class WorkActivityHazardCreate(BaseModel):
    """新建作业活动危险源。

    D、评价级别由服务端计算；即使客户端附带同名字段也会被忽略（默认 extra=ignore）。
    """

    position_location: RequiredShortText = Field(..., description="岗位/地点（一期自由文本）")
    area_activity: RequiredShortText = Field(..., description="区域/活动（一期自由文本）")
    hazard_name_or_event: RequiredLongText = Field(..., description="危险源名称或潜在事件")
    possible_harm: RequiredLongText = Field(..., description="可能导致的危害")
    hazard_type: RequiredLongText = Field(..., description="危险源类型")

    likelihood_l: Decimal = Field(..., ge=LIKELIHOOD_MIN, le=LIKELIHOOD_MAX, description="可能性 L（0.1–10）")
    exposure_e: Decimal = Field(..., ge=EXPOSURE_MIN, le=EXPOSURE_MAX, description="发生频次 E（0.5–10）")
    consequence_c: Decimal = Field(..., ge=CONSEQUENCE_MIN, le=CONSEQUENCE_MAX, description="后果 C（1–100）")

    control_measures: list[str] = Field(..., min_length=1, description="控制措施（有序的稳定 key 数组）")
    residual_risk: str = Field(..., description="残余风险 key")
    control_level: str = Field(..., description="管控层级（28 个部门之一）")
    execution_level: str = Field(..., description="执行层级 key（车间/班组长）")

    @field_validator("likelihood_l", "exposure_e", "consequence_c")
    @classmethod
    def _quantize_to_storage_scale(cls, value: Decimal) -> Decimal:
        """拒绝超过 6 位小数的输入，并量化为数据库存储精度。"""
        if value != quantize_decimal(value):
            raise ValueError(f"最多允许 6 位小数，收到: {value}")
        return quantize_decimal(value)

    @field_validator("control_measures")
    @classmethod
    def _validate_control_measures(cls, value: list[str]) -> list[str]:
        return _validate_control_measures_value(value)

    @field_validator("residual_risk")
    @classmethod
    def _validate_residual_risk(cls, value: str) -> str:
        return _validate_residual_risk_value(value)

    @field_validator("control_level")
    @classmethod
    def _validate_control_level(cls, value: str) -> str:
        return _validate_control_level_value(value)

    @field_validator("execution_level")
    @classmethod
    def _validate_execution_level(cls, value: str) -> str:
        return _validate_execution_level_value(value)


class WorkActivityHazardResponse(BaseModel):
    """作业活动危险源台账记录（含服务端计算字段）。"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    position_location: str
    area_activity: str
    hazard_name_or_event: str
    possible_harm: str
    hazard_type: str
    likelihood_l: Decimal
    exposure_e: Decimal
    consequence_c: Decimal
    risk_value_d: Decimal
    evaluation_grade: int
    evaluation_grade_label: str
    control_measures: list[str]
    residual_risk: str
    residual_risk_label: str
    control_level: str
    execution_level: str
    created_by: uuid.UUID | None = None
    updated_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class WorkActivityHazardApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: WorkActivityHazardResponse | None = None


class WorkActivityHazardListMeta(BaseModel):
    page: int
    page_size: int
    total: int


class WorkActivityHazardListApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: list[WorkActivityHazardResponse]
    meta: WorkActivityHazardListMeta


def _validate_equipment_measures_value(value: list[str]) -> list[str]:
    unknown = [key for key in value if key not in EQUIPMENT_MEASURE_LABELS]
    if unknown:
        raise ValueError(f"措施包含未知选项: {', '.join(unknown)}")
    if not value:
        raise ValueError("措施至少选择一项")
    return value


class EquipmentFacilityHazardCreate(BaseModel):
    """新建设备设施危险源。

    R 由服务端按 L/S 查安全风险矩阵得出；即使客户端附带 risk_evaluation_r
    也会被忽略（extra=ignore），读取时始终返回服务端计算值。
    """

    model_config = ConfigDict(extra="ignore")

    equipment_facility_tag: RequiredShortText = Field(..., description="设备设施/位号（一期自由文本）")
    inspection_item: RequiredLongText = Field(..., description="检查项目")
    inspection_standard: RequiredLongText = Field(..., description="检查标准")
    nonconformity_consequence: RequiredLongText = Field(..., description="不符合标准情况及后果")

    likelihood_l: int = Field(..., ge=1, le=5, description="可能性 L（1–5）")
    severity_s: str = Field(..., min_length=1, max_length=1, description="严重性 S（A–E）")

    current_control_measures: list[str] = Field(..., min_length=1, description="现有管控措施（有序 key 数组）")
    improvement_measures: list[str] = Field(..., min_length=1, description="建议改进（新增）措施（有序 key 数组）")
    residual_risk: str = Field(..., description="残余风险 key")
    control_level: str = Field(..., description="管控层级（28 个部门之一）")
    execution_level: str = Field(..., description="执行层级 key（车间/班组长）")
    remarks: RequiredLongText = Field(..., description="备注")

    @field_validator("severity_s")
    @classmethod
    def _validate_severity(cls, value: str) -> str:
        if value not in SEVERITY_LEVELS:
            raise ValueError(f"严重性 S 必须是以下之一: {', '.join(SEVERITY_LEVELS)}")
        return value

    @field_validator("current_control_measures", "improvement_measures")
    @classmethod
    def _validate_measures(cls, value: list[str]) -> list[str]:
        return _validate_equipment_measures_value(value)

    @field_validator("residual_risk")
    @classmethod
    def _validate_residual_risk(cls, value: str) -> str:
        return _validate_residual_risk_value(value)

    @field_validator("control_level")
    @classmethod
    def _validate_control_level(cls, value: str) -> str:
        return _validate_control_level_value(value)

    @field_validator("execution_level")
    @classmethod
    def _validate_execution_level(cls, value: str) -> str:
        return _validate_execution_level_value(value)


class EquipmentFacilityHazardResponse(BaseModel):
    """设备设施危险源台账记录（含服务端计算字段）。"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    equipment_facility_tag: str
    inspection_item: str
    inspection_standard: str
    nonconformity_consequence: str
    likelihood_l: int
    severity_s: str
    risk_evaluation_r: int
    current_control_measures: list[str]
    improvement_measures: list[str]
    residual_risk: str
    residual_risk_label: str
    control_level: str
    execution_level: str
    remarks: str
    created_by: uuid.UUID | None = None
    updated_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class EquipmentFacilityHazardApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: EquipmentFacilityHazardResponse | None = None


class EquipmentFacilityHazardListMeta(BaseModel):
    page: int
    page_size: int
    total: int


class EquipmentFacilityHazardListApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: list[EquipmentFacilityHazardResponse]
    meta: EquipmentFacilityHazardListMeta


# ============ 风险分级管控选项契约（只读，后端权威） ============


class RiskGradingValueLabel(BaseModel):
    """稳定的选项 key 与展示文本。"""

    value: str
    label: str


class LecRange(BaseModel):
    """LEC 某一项的合法闭区间。"""

    min: Decimal
    max: Decimal


class RiskGradeThreshold(BaseModel):
    """分级阈值：D > lower_bound_exclusive 时取该 grade（阈值从高到低排列）。"""

    grade: int
    lower_bound_exclusive: Decimal


class RiskGradingOptions(BaseModel):
    """两张危险源台账前端所需的权威选项、矩阵与阈值。"""

    departments: list[str]
    control_measures: list[RiskGradingValueLabel]
    equipment_measures: list[RiskGradingValueLabel]
    residual_risks: list[RiskGradingValueLabel]
    execution_levels: list[RiskGradingValueLabel]
    likelihood_levels: list[int]
    severity_levels: list[str]
    safety_risk_matrix: dict[str, list[int]]
    grade_thresholds: list[RiskGradeThreshold]
    likelihood_range: LecRange
    exposure_range: LecRange
    consequence_range: LecRange
    min_risk_value: Decimal


class RiskGradingOptionsApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: RiskGradingOptions
