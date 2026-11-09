"""风险分级管控台账 schema：作业活动危险源台账（LEC）。"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from app.modules.safety.risk_grading import (
    CONSEQUENCE_MAX,
    CONSEQUENCE_MIN,
    CONTROL_MEASURE_KEYS,
    EXECUTION_LEVEL_KEYS,
    EXPOSURE_MAX,
    EXPOSURE_MIN,
    LIKELIHOOD_MAX,
    LIKELIHOOD_MIN,
    RESIDUAL_RISK_KEYS,
    RISK_GRADING_DEPARTMENTS,
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


class WorkActivityHazardUpdate(BaseModel):
    """部分更新作业活动危险源（PATCH）。

    只提交需要修改的字段；服务端会把未提交字段与数据库现值合并后，再按
    `WorkActivityHazardCreate` 的完整规则重新校验并重算 D / 评价级别。
    客户端附带 D、评价级别等同名字段会被忽略。
    """

    position_location: RequiredShortText | None = None
    area_activity: RequiredShortText | None = None
    hazard_name_or_event: RequiredLongText | None = None
    possible_harm: RequiredLongText | None = None
    hazard_type: RequiredLongText | None = None

    likelihood_l: Decimal | None = Field(None, ge=LIKELIHOOD_MIN, le=LIKELIHOOD_MAX)
    exposure_e: Decimal | None = Field(None, ge=EXPOSURE_MIN, le=EXPOSURE_MAX)
    consequence_c: Decimal | None = Field(None, ge=CONSEQUENCE_MIN, le=CONSEQUENCE_MAX)

    control_measures: list[str] | None = None
    residual_risk: str | None = None
    control_level: str | None = None
    execution_level: str | None = None

    @field_validator("control_measures")
    @classmethod
    def _validate_control_measures(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return _validate_control_measures_value(value)

    @field_validator("residual_risk")
    @classmethod
    def _validate_residual_risk(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_residual_risk_value(value)

    @field_validator("control_level")
    @classmethod
    def _validate_control_level(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_control_level_value(value)

    @field_validator("execution_level")
    @classmethod
    def _validate_execution_level(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_execution_level_value(value)

    @model_validator(mode="after")
    def _reject_explicit_nulls(self) -> WorkActivityHazardUpdate:
        null_fields = [name for name in self.model_fields_set if getattr(self, name) is None]
        if null_fields:
            raise ValueError(f"以下字段不能为 null: {', '.join(sorted(null_fields))}")
        return self


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
