"""Schemas for Equipment Import v4."""
from typing import Any
from pydantic import BaseModel, Field


class WarningInfo(BaseModel):
    field: str
    level: str
    message: str


class ChangeRecord(BaseModel):
    old: Any = None
    new: Any = None


class ImportErrorItem(BaseModel):
    row: int
    error: str


class ImportV4PreviewResponse(BaseModel):
    """预览接口响应模型"""
    items: list[dict[str, Any]]
    total: int
    headers: list[dict[str, Any]]


class ImportV4BatchResponse(BaseModel):
    """批量导入接口响应模型"""
    batch_id: str
    created_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    unmapped_departments: dict[str, list[int]] = Field(default_factory=dict)
    errors: list[ImportErrorItem] = Field(default_factory=list)
