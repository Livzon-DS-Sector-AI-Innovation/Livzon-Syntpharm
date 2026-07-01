"""Statistics Pydantic schemas."""

from typing import Any

from pydantic import BaseModel


class StepBreakdownItem(BaseModel):
    step: str
    label: str
    roleLabel: str
    count: int


class DeviationStatistics(BaseModel):
    total: int
    pending: int
    departmentDistribution: list[dict[str, Any]]
    statusDistribution: list[dict[str, Any]]
    stepBreakdown: list[StepBreakdownItem]


class CapaStatistics(BaseModel):
    total: int
    statusDistribution: list[dict[str, Any]]
    sourceDistribution: list[dict[str, Any]]
