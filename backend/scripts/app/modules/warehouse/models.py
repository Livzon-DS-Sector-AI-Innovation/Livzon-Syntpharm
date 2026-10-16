"""Warehouse ORM models live here."""

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel


class RawMaterialInventory(BaseModel):
    __tablename__ = "raw_material_inventories"
    __table_args__ = (
        Index("ix_warehouse_raw_materials_code", "code"),
        Index("ix_warehouse_raw_materials_product_line", "product_line"),
        Index("ix_warehouse_raw_materials_import_key", "import_key", unique=True),
        {"schema": "warehouse"},
    )

    source_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="来源记录 ID")
    code: Mapped[str] = mapped_column(String(64), nullable=False, comment="物料编码")
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="物料名称")
    spec: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="规格")
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="单位")
    available: Mapped[float] = mapped_column(Float, nullable=False, default=0, comment="可用库存")
    safety: Mapped[float] = mapped_column(Float, nullable=False, default=0, comment="安全库存")
    last_month: Mapped[float] = mapped_column(Float, nullable=False, default=0, comment="上月库存/用量")
    two_months_ago: Mapped[float] = mapped_column(Float, nullable=False, default=0, comment="前月库存/用量")
    today_balance: Mapped[float] = mapped_column(Float, nullable=False, default=0, comment="今日结存")
    front_stock: Mapped[float] = mapped_column(Float, nullable=False, default=0, comment="前台库存")
    this_month_use: Mapped[float] = mapped_column(Float, nullable=False, default=0, comment="本月用量")
    warning: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="预警")
    product_line: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="使用产品/类别")
    erp_no: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="ERP 编号")
    delivery: Mapped[str | None] = mapped_column(Text, nullable=True, comment="到货时间")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    import_key: Mapped[str] = mapped_column(String(64), nullable=False, comment="导入唯一键")
    source: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="数据来源")
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        comment="最近同步时间",
    )


class PackagingMaterialInventory(BaseModel):
    __tablename__ = "packaging_material_inventories"
    __table_args__ = (
        Index("ix_warehouse_packaging_materials_code", "code"),
        Index("ix_warehouse_packaging_materials_product_line", "product_line"),
        Index(
            "ix_warehouse_packaging_materials_import_key",
            "import_key",
            unique=True,
        ),
        {"schema": "warehouse"},
    )

    source_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="来源记录 ID")
    code: Mapped[str] = mapped_column(String(64), nullable=False, comment="包材编码")
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="名称")
    spec: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="规格")
    batch: Mapped[str | None] = mapped_column(Text, nullable=True, comment="批次")
    available: Mapped[float] = mapped_column(Float, nullable=False, default=0, comment="可用库存")
    safety: Mapped[float] = mapped_column(Float, nullable=False, default=0, comment="安全库存")
    last_month: Mapped[float] = mapped_column(Float, nullable=False, default=0, comment="上月库存/用量")
    two_months_ago: Mapped[float] = mapped_column(Float, nullable=False, default=0, comment="前月库存/用量")
    today_balance: Mapped[float] = mapped_column(Float, nullable=False, default=0, comment="今日结存")
    front_stock: Mapped[float] = mapped_column(Float, nullable=False, default=0, comment="前台库存")
    this_month_use: Mapped[float] = mapped_column(Float, nullable=False, default=0, comment="本月用量")
    warning: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="预警")
    product_line: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="使用产品")
    erp_no: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="ERP 编号")
    delivery: Mapped[str | None] = mapped_column(Text, nullable=True, comment="到货时间")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    import_key: Mapped[str] = mapped_column(String(64), nullable=False, comment="导入唯一键")
    source: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="数据来源")
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        comment="最近同步时间",
    )


class ProductInventory(BaseModel):
    __tablename__ = "product_inventories"
    __table_args__ = (
        Index("ix_warehouse_products_name", "name"),
        Index("ix_warehouse_products_import_key", "import_key", unique=True),
        {"schema": "warehouse"},
    )

    source_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="来源记录 ID")
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="产品名称")
    spec: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="包装规格")
    order_quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0, comment="订单量")
    pending_quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0, comment="待检数量")
    qualified_quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0, comment="合格数量")
    subtotal_quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0, comment="小计")
    remaining_quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0, comment="剩余量")
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="单位")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    import_key: Mapped[str] = mapped_column(String(64), nullable=False, comment="导入唯一键")
    source: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="数据来源")
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        comment="最近同步时间",
    )


class WarehouseFeishuConfig(BaseModel):
    __tablename__ = "feishu_configs"
    __table_args__ = (
        Index("ix_warehouse_feishu_configs_is_active", "is_active"),
        {"schema": "warehouse"},
    )

    config_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default="仓储飞书配置",
        comment="配置名称",
    )
    app_id: Mapped[str] = mapped_column(String(128), nullable=False, comment="飞书应用 App ID")
    encrypted_app_secret: Mapped[str] = mapped_column(
        String(1024), nullable=False, comment="加密后的飞书应用 App Secret"
    )
    bitable_app_token: Mapped[str] = mapped_column(String(128), nullable=False, comment="飞书多维表格 app_token")
    finished_product_app_token: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="成品多维表格 app_token"
    )
    materials_packaging_app_token: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="原辅料及包材多维表格 app_token"
    )
    hardware_app_token: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="五金多维表格 app_token")
    raw_material_table_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="原辅料库存表 table_id"
    )
    packaging_table_id: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="包材库存表 table_id")
    product_table_id: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="成品库存表 table_id")
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="是否启用",
    )
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")


class WarehouseFeishuTable(BaseModel):
    __tablename__ = "feishu_tables"
    __table_args__ = (
        Index(
            "uq_warehouse_feishu_tables_domain_app_token_table_id",
            "business_domain",
            "app_token",
            "table_id",
            unique=True,
        ),
        Index(
            "ix_warehouse_feishu_tables_domain_enabled",
            "business_domain",
            "is_enabled",
        ),
        Index("ix_warehouse_feishu_tables_app_token", "app_token"),
        {"schema": "warehouse"},
    )

    business_domain: Mapped[str] = mapped_column(String(64), nullable=False, comment="仓储业务域")
    app_token: Mapped[str] = mapped_column(String(128), nullable=False, comment="飞书多维表格 app_token")
    table_id: Mapped[str] = mapped_column(String(128), nullable=False, comment="飞书多维表格 table_id")
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="数据表名称")
    revision: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="飞书表 revision")
    last_discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        comment="最近发现时间",
    )
    last_event_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="最近事件时间"
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="是否启用同步与监测",
    )
    field_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0", comment="字段数量")
    record_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="记录数量"
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="最近同步时间"
    )
    sync_status: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="同步状态")
    sync_error: Mapped[str | None] = mapped_column(Text, nullable=True, comment="最近同步错误")


class WarehouseFeishuField(BaseModel):
    __tablename__ = "feishu_fields"
    __table_args__ = (
        Index(
            "uq_warehouse_feishu_fields_domain_table_field",
            "business_domain",
            "app_token",
            "table_id",
            "field_id",
            unique=True,
        ),
        Index(
            "ix_warehouse_feishu_fields_table",
            "business_domain",
            "app_token",
            "table_id",
        ),
        {"schema": "warehouse"},
    )

    business_domain: Mapped[str] = mapped_column(String(64), nullable=False, comment="仓储业务域")
    app_token: Mapped[str] = mapped_column(String(128), nullable=False, comment="飞书多维表格 app_token")
    table_id: Mapped[str] = mapped_column(String(128), nullable=False, comment="飞书多维表格 table_id")
    field_id: Mapped[str] = mapped_column(String(128), nullable=False, comment="飞书字段 ID")
    field_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="飞书字段名称")
    field_type: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="飞书字段类型")
    property: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True, comment="飞书字段属性")
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        comment="最近同步时间",
    )


class WarehouseFeishuRecord(BaseModel):
    __tablename__ = "feishu_records"
    __table_args__ = (
        Index(
            "uq_warehouse_feishu_records_domain_table_record",
            "business_domain",
            "app_token",
            "table_id",
            "record_id",
            unique=True,
        ),
        Index(
            "ix_warehouse_feishu_records_table",
            "business_domain",
            "app_token",
            "table_id",
        ),
        Index("ix_warehouse_feishu_records_search_text", "search_text"),
        {"schema": "warehouse"},
    )

    business_domain: Mapped[str] = mapped_column(String(64), nullable=False, comment="仓储业务域")
    app_token: Mapped[str] = mapped_column(String(128), nullable=False, comment="飞书多维表格 app_token")
    table_id: Mapped[str] = mapped_column(String(128), nullable=False, comment="飞书多维表格 table_id")
    record_id: Mapped[str] = mapped_column(String(128), nullable=False, comment="飞书记录 ID")
    fields: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict, comment="飞书原始字段 JSON")
    search_text: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="", comment="检索文本")
    feishu_created_time: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="飞书创建时间")
    feishu_last_modified_time: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="飞书最近修改时间")
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        comment="最近同步时间",
    )
