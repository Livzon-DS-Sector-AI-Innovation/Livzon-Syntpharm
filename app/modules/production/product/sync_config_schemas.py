"""Product sync config request and response schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProductSyncConfigCreate(BaseModel):
    """创建同步配置"""

    product_id: uuid.UUID = Field(..., description="产品ID")
    app_token: str = Field(..., max_length=128, description="飞书多维表格 app_token")
    table_id: str = Field(..., max_length=128, description="飞书表格 table_id")
    field_mapping: dict[str, Any] | None = Field(None, description="字段映射配置")
    auto_sync: bool = Field(False, description="是否自动同步")
    sync_direction: str = Field("bidirectional", description="同步方向: push/pull/bidirectional")


class ProductSyncConfigUpdate(BaseModel):
    """更新同步配置"""

    app_token: str | None = Field(None, max_length=128, description="飞书多维表格 app_token")
    table_id: str | None = Field(None, max_length=128, description="飞书表格 table_id")
    field_mapping: dict[str, Any] | None = Field(None, description="字段映射配置")
    auto_sync: bool | None = Field(None, description="是否自动同步")
    sync_direction: str | None = Field(None, description="同步方向: push/pull/bidirectional")


class ProductSyncConfigResponse(BaseModel):
    """同步配置响应"""

    id: uuid.UUID
    product_id: uuid.UUID
    app_token: str
    table_id: str
    field_mapping: dict[str, Any] | None = None
    auto_sync: bool
    sync_direction: str
    last_sync_at: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SyncResult(BaseModel):
    """同步结果"""

    imported: int = Field(0, description="导入/推送数量")
    updated: int = Field(0, description="更新数量")
    skipped: int = Field(0, description="跳过数量（重复）")
    errors: list[str] = Field(default_factory=list, description="错误信息")
    message: str = Field("", description="结果描述")
