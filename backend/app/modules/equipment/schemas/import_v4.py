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


# response_model 不能写 ApiResponse：其 data 为 Any，OpenAPI 生成不出字段，前端只能手写类型兜底。
# 以下两个 envelope 描述完整实际响应体，命名对齐 procurement 既有先例。
class ImportV4BatchApiResponse(BaseModel):
    code: int = Field(200, description="响应状态码")
    message: str = Field("success", description="响应消息")
    data: ImportV4BatchResponse
    meta: dict[str, Any] | None = None


class ImportV4PreviewApiResponse(BaseModel):
    code: int = Field(200, description="响应状态码")
    message: str = Field("success", description="响应消息")
    data: ImportV4PreviewResponse
    meta: dict[str, Any] | None = None
