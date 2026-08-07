"""Energy ORM models: device config, data collection, and collect logs."""

from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID as UUIDType

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel


class EnergyType(enum.StrEnum):
    ELECTRICITY = "electricity"
    WATER = "water"
    STEAM = "steam"


class MonitorLevel(enum.StrEnum):
    NORMAL = "normal"
    IMPORTANT = "important"
    URGENT = "urgent"


class CollectStatus(enum.StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class WorkshopCategory(enum.StrEnum):
    WORKSHOP = "workshop"  # 生产车间
    POSITION = "position"  # 岗位
    SUPPORT = "support"  # 辅助部门
    UTILITY = "utility"  # 动力设施


class EnergyWorkshop(BaseModel):
    """车间/部门配置表"""

    __tablename__ = "energy_workshops"
    __table_args__ = (
        UniqueConstraint("code", name="uq_energy_workshop_code"),
        {"schema": "energy"},
    )

    code: Mapped[str] = mapped_column(String(50), nullable=False, comment="车间编码")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="车间名称")
    category: Mapped[str] = mapped_column(String(20), nullable=False, comment="分类: workshop/position/support/utility")
    parent_id: Mapped[UUIDType | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("energy.energy_workshops.id"),
        nullable=True,
        comment="父级车间ID",
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="排序")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否启用")


class EnergyDeviceConfig(BaseModel):
    """三方平台设备配置表"""

    __tablename__ = "energy_device_configs"
    __table_args__ = (
        UniqueConstraint(
            "platform_code",
            "platform_device_code",
            "is_deleted",
            name="uq_energy_device_config_platform_device",
        ),
        CheckConstraint(
            "energy_type IN ('electricity', 'water', 'steam', 'natural_gas')",
            name="ck_energy_device_config_energy_type",
        ),
        CheckConstraint(
            "monitor_level IN ('normal', 'important', 'urgent')",
            name="ck_energy_device_config_monitor_level",
        ),
        CheckConstraint(
            "collection_interval > 0",
            name="ck_energy_device_config_interval_positive",
        ),
        {"schema": "energy"},
    )

    platform_code: Mapped[str] = mapped_column(String(50), nullable=False, comment="平台标识")
    platform_device_code: Mapped[str] = mapped_column(String(100), nullable=False, comment="三方平台设备/采集点编码")
    device_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="设备名称")
    energy_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="能源类型: electricity/water/steam")
    api_endpoint: Mapped[str] = mapped_column(String(500), nullable=False, comment="API 路径")
    workshop: Mapped[str] = mapped_column(String(100), nullable=False, comment="所属车间")
    production_line: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="所属产线")
    monitor_level: Mapped[str] = mapped_column(String(20), nullable=False, default="normal", comment="监控等级")
    unit: Mapped[str] = mapped_column(String(20), nullable=False, comment="计量单位")
    collection_interval: Mapped[int] = mapped_column(Integer, nullable=False, default=60, comment="采集间隔(分钟)")
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否启用采集")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")


class EnergyData(BaseModel):
    """能耗数据采集表"""

    __tablename__ = "energy_data"
    __table_args__ = (
        UniqueConstraint(
            "device_config_id",
            "timestamp",
            name="uq_energy_data_device_timestamp",
        ),
        {"schema": "energy"},
    )

    device_config_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="设备配置ID",
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="数据时间点(小时粒度)",
    )
    value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, comment="能耗累计值")
    unit: Mapped[str] = mapped_column(String(20), nullable=False, comment="计量单位")
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="实际采集时间",
    )
    platform_raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True, comment="原始返回数据")


class EnergyMonthlyRecord(BaseModel):
    """月度能耗记录表（用于存储飞书导入的数据）"""

    __tablename__ = "energy_monthly_records"
    __table_args__ = (
        UniqueConstraint(
            "workshop_id",
            "energy_type",
            "record_date",
            name="uq_energy_monthly_record",
        ),
        CheckConstraint(
            "energy_type IN ('electricity', 'water', 'steam', 'natural_gas')",
            name="ck_energy_monthly_record_energy_type",
        ),
        {"schema": "energy"},
    )

    workshop_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("energy.energy_workshops.id"),
        nullable=False,
        comment="车间ID",
    )
    energy_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="能源类型")
    record_date: Mapped[date] = mapped_column(Date, nullable=False, comment="记录日期")
    date_range_end: Mapped[date | None] = mapped_column(Date, nullable=True, comment="日期范围结束（多日汇总时使用）")
    value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, comment="能耗值")
    unit: Mapped[str] = mapped_column(String(20), nullable=False, comment="计量单位")
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="feishu", comment="数据来源")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")


class EnergyCollectLog(BaseModel):
    """采集日志表"""

    __tablename__ = "energy_collect_logs"
    __table_args__ = ({"schema": "energy"},)

    platform_code: Mapped[str] = mapped_column(String(50), nullable=False, comment="采集的平台")
    collect_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="采集触发时间",
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, comment="状态: success/partial/failed")
    device_count: Mapped[int] = mapped_column(Integer, nullable=False, comment="应采集设备数")
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, comment="成功采集数")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")


class EnergyAlertRule(BaseModel):
    """预警规则表"""

    __tablename__ = "energy_alert_rules"
    __table_args__ = (
        CheckConstraint(
            "energy_type IN ('electricity', 'water', 'steam', 'natural_gas')",
            name="ck_energy_alert_rule_energy_type",
        ),
        CheckConstraint(
            "alert_level IN ('info', 'warning', 'critical', 'emergency')",
            name="ck_energy_alert_rule_alert_level",
        ),
        CheckConstraint(
            "monitor_metric IN ('instant', 'daily_total', 'monthly_total')",
            name="ck_energy_alert_rule_monitor_metric",
        ),
        CheckConstraint(
            "threshold_type IN ('greater_than', 'less_than', 'equal')",
            name="ck_energy_alert_rule_threshold_type",
        ),
        CheckConstraint(
            "notify_frequency IN ('first', 'every', 'daily_summary')",
            name="ck_energy_alert_rule_notify_frequency",
        ),
        CheckConstraint(
            "effective_time IN ('all_day', 'custom')",
            name="ck_energy_alert_rule_effective_time",
        ),
        {"schema": "energy"},
    )

    rule_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="规则名称")
    rule_description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="规则描述")
    energy_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="能源类型")
    monitor_metric: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="监控指标: instant/daily_total/monthly_total"
    )
    threshold_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="阈值类型")
    threshold_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, comment="阈值")
    unit: Mapped[str] = mapped_column(String(20), nullable=False, comment="计量单位")
    alert_level: Mapped[str] = mapped_column(String(20), nullable=False, comment="预警等级")
    notify_method: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, comment="通知方式: email/sms/feishu"
    )
    notify_users: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, comment="通知用户列表")
    notify_frequency: Mapped[str] = mapped_column(String(20), nullable=False, default="first", comment="通知频率")
    effective_time: Mapped[str] = mapped_column(String(20), nullable=False, default="all_day", comment="生效时段类型")
    custom_time_start: Mapped[str | None] = mapped_column(String(8), nullable=True, comment="自定义开始时间(HH:MM:SS)")
    custom_time_end: Mapped[str | None] = mapped_column(String(8), nullable=True, comment="自定义结束时间(HH:MM:SS)")
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否启用")


class EnergyAlertRecord(BaseModel):
    """预警记录表"""

    __tablename__ = "energy_alert_records"
    __table_args__ = (
        CheckConstraint(
            "alert_level IN ('info', 'warning', 'critical', 'emergency')",
            name="ck_energy_alert_record_alert_level",
        ),
        CheckConstraint(
            "status IN ('pending', 'processed', 'ignored')",
            name="ck_energy_alert_record_status",
        ),
        {"schema": "energy"},
    )

    rule_id: Mapped[UUIDType | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("energy.energy_alert_rules.id", ondelete="CASCADE"),
        nullable=True,
        comment="预警规则ID",
    )
    device_config_id: Mapped[UUIDType | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="关联设备配置ID",
    )
    energy_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="能源类型")
    alert_level: Mapped[str] = mapped_column(String(20), nullable=False, comment="预警等级")
    trigger_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, comment="触发值")
    threshold_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, comment="阈值")
    unit: Mapped[str] = mapped_column(String(20), nullable=False, comment="计量单位")
    alert_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, comment="预警触发时间")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", comment="处理状态")
    processed_by: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="处理人")
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="处理时间")
    process_note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="处理备注")


class EnergyDailyData(BaseModel):
    """每日能耗数据表（用于预警）"""

    __tablename__ = "energy_daily_data"
    __table_args__ = (
        UniqueConstraint(
            "date",
            "energy_type",
            "category",
            name="uq_energy_daily_data_date_type_category",
        ),
        {"schema": "energy"},
    )

    date: Mapped[date] = mapped_column(Date, nullable=False, comment="数据日期")
    energy_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="能源类型: water/electricity/steam/natural_gas"
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False, comment="类别（如'水（吨）'）")
    total_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, comment="总数（实际用量）")
    alert_threshold: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, comment="警戒线（预警阈值）")
    cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True, comment="费用")
    municipal_meter: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True, comment="市政总表")
    error_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True, comment="误差")
    source_table: Mapped[str] = mapped_column(String(50), nullable=False, comment="来源表（水表/电表等）")
    is_alert: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否触发预警")
    alert_record_id: Mapped[UUIDType | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="关联预警记录ID",
    )


class EnergyUnitConsumptionTarget(BaseModel):
    """车间单耗目标表"""

    __tablename__ = "energy_unit_consumption_targets"
    __table_args__ = (
        UniqueConstraint("workshop_id", "target_month", name="uk_workshop_month"),
        {"schema": "energy"},
    )

    # BaseModel 已提供: id (UUID), created_at, updated_at, created_by, updated_by, is_deleted

    workshop_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("energy.energy_workshops.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联车间ID",
    )
    target_month: Mapped[date] = mapped_column(Date, nullable=False, comment="目标月份")
    target_unit_consumption: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, comment="目标单耗(kWh/件)"
    )
