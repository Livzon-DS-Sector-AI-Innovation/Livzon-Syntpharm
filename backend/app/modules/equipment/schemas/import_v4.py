"""Schemas for Equipment Import v4."""
from typing import Any, TypedDict


class WarningInfo(TypedDict):
    field: str
    level: str
    message: str


class ChangeRecord(TypedDict):
    old: Any
    new: Any


class EquipmentImportRow(TypedDict, total=False):
    """定义 Excel 导入行的标准结构"""
    asset_no: str | None
    equipment_tag: str | None
    name: str | None
    department_id: str | None
    department_name: str | None
    department: str | None
    location_text: str | None
    current_cost: float | str | None
    book_value: float | str | None
    responsible_person_name: str | None


class ImportBatchResponse(TypedDict):
    batch_id: str
    created_count: int
    updated_count: int
    skipped_count: int
    error_count: int
    warnings_count: int
    errors: list[dict[str, Any]]
