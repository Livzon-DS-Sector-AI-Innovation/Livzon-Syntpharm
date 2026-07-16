"""Warehouse request and response schemas live here."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.platform.integrations.feishu.utils import (
    normalize_app_token,
)


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _strip_text(value: str | None) -> str | None:
    if isinstance(value, str):
        return value.strip()
    return value


class RawMaterialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: str | None = None
    code: str
    name: str
    spec: str | None = None
    unit: str | None = None
    available: float
    safety: float
    last_month: float
    two_months_ago: float
    today_balance: float
    front_stock: float
    this_month_use: float
    warning: str | None = None
    product_line: str | None = None
    erp_no: str | None = None
    delivery: str | None = None
    remark: str | None = None
    source: str | None = None
    import_key: str
    last_synced_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PackagingMaterialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: str | None = None
    code: str
    name: str
    spec: str | None = None
    batch: str | None = None
    available: float
    safety: float
    last_month: float
    two_months_ago: float
    today_balance: float
    front_stock: float
    this_month_use: float
    warning: str | None = None
    product_line: str | None = None
    erp_no: str | None = None
    delivery: str | None = None
    remark: str | None = None
    source: str | None = None
    import_key: str
    last_synced_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProductInventoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: str | None = None
    name: str
    spec: str | None = None
    order_quantity: float
    pending_quantity: float
    qualified_quantity: float
    subtotal_quantity: float
    remaining_quantity: float
    unit: str | None = None
    remark: str | None = None
    source: str | None = None
    import_key: str
    last_synced_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RawMaterialListResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: list[RawMaterialResponse]
    meta: dict[str, int] | None = None


class PackagingMaterialListResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: list[PackagingMaterialResponse]
    meta: dict[str, int] | None = None


class ProductInventoryListResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: list[ProductInventoryResponse]
    meta: dict[str, int] | None = None


WarehouseFeishuBusinessDomain = Literal["finished_product", "materials_packaging", "hardware"]


WAREHOUSE_FEISHU_DOMAIN_LABELS: dict[str, str] = {
    "finished_product": "成品",
    "materials_packaging": "原辅料及包材",
    "hardware": "五金",
}


class WarehouseFeishuConfigBase(BaseModel):
    config_name: str = Field(default="仓储飞书配置", max_length=128)
    app_id: str = Field(..., max_length=128)
    finished_product_app_token: str | None = Field(default=None, max_length=128)
    materials_packaging_app_token: str | None = Field(default=None, max_length=128)
    hardware_app_token: str | None = Field(default=None, max_length=128)
    is_active: bool = True
    remark: str | None = None

    @field_validator("config_name", "app_id", mode="before")
    @classmethod
    def normalize_required_text(cls, value: str | None) -> str | None:
        return _strip_text(value)

    @field_validator(
        "finished_product_app_token",
        "materials_packaging_app_token",
        "hardware_app_token",
        mode="before",
    )
    @classmethod
    def normalize_bitable_app_token(cls, value: str | None) -> str | None:
        return normalize_app_token(value)


class WarehouseFeishuConfigUpsert(WarehouseFeishuConfigBase):
    app_secret: str | None = Field(default=None, max_length=500)

    @field_validator("app_secret", mode="before")
    @classmethod
    def normalize_app_secret(cls, value: str | None) -> str | None:
        return _clean_text(value)


class WarehouseFeishuConfigResponse(WarehouseFeishuConfigBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    app_secret_configured: bool = False
    app_secret_masked: str = ""
    bitable_app_token: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class WarehouseFeishuConfigApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: WarehouseFeishuConfigResponse
    meta: dict[str, int] | None = None


class WarehouseFeishuTableResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    business_domain: str
    app_token: str
    table_id: str
    name: str
    revision: int | None = None
    last_discovered_at: datetime | None = None
    last_event_at: datetime | None = None
    is_enabled: bool = False
    field_count: int = 0
    record_count: int = 0
    last_synced_at: datetime | None = None
    sync_status: str | None = None
    sync_error: str | None = None


class WarehouseFeishuTableListApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: list[WarehouseFeishuTableResponse]
    meta: dict[str, int] | None = None


class WarehouseFeishuFieldResponse(BaseModel):
    field_id: str
    field_name: str
    type: int | None = None
    property: dict[str, Any] | None = None


class WarehouseFeishuRawRecordResponse(BaseModel):
    record_id: str
    fields: dict[str, Any]
    created_time: int | None = None
    last_modified_time: int | None = None


class WarehouseFeishuRawRecordData(BaseModel):
    table: WarehouseFeishuTableResponse | None = None
    fields: list[WarehouseFeishuFieldResponse]
    records: list[WarehouseFeishuRawRecordResponse]
    page: int = 1
    page_size: int = 50
    total: int | None = None


class WarehouseFeishuRawRecordApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: WarehouseFeishuRawRecordData
    meta: dict[str, int] | None = None


class WarehouseFeishuWsStatus(BaseModel):
    enabled: bool
    connected: bool
    app_id: str | None = None
    app_tokens: dict[str, str] = Field(default_factory=dict)
    last_started_at: datetime | None = None
    last_error: str | None = None


class WarehouseFeishuTableEnablePayload(BaseModel):
    is_enabled: bool


class WarehouseFeishuTableBatchEnablePayload(BaseModel):
    table_ids: list[UUID]
    is_enabled: bool


class WarehouseFeishuTableEnableApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: WarehouseFeishuTableResponse
    meta: dict[str, int] | None = None


class WarehouseFeishuTableBatchEnableApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: list[WarehouseFeishuTableResponse]
    meta: dict[str, int] | None = None


class WarehouseFeishuTableSyncResult(BaseModel):
    table: WarehouseFeishuTableResponse
    field_count: int
    record_count: int


class WarehouseFeishuTableSyncApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: WarehouseFeishuTableSyncResult
    meta: dict[str, int] | None = None


class WarehouseFeishuWsStatusApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: WarehouseFeishuWsStatus
    meta: dict[str, int] | None = None


class WarehouseFeishuConnectivityStep(BaseModel):
    name: str
    status: str
    message: str


class WarehouseFeishuConnectivityResult(BaseModel):
    ok: bool
    steps: list[WarehouseFeishuConnectivityStep]


class WarehouseFeishuConnectivityApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: WarehouseFeishuConnectivityResult
    meta: dict[str, int] | None = None
