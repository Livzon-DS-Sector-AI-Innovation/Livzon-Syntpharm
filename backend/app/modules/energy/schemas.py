"""Energy request and response schemas live here."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field

StrUUID = Annotated[str, BeforeValidator(str)]
EnergyType = Literal["electricity", "water", "steam", "natural_gas"]
MonitorLevel = Literal["normal", "important", "urgent"]
CollectStatus = Literal["success", "partial", "failed"]
WorkshopCategory = Literal["workshop", "position", "support", "utility"]


# ── 车间管理 ──


class EnergyWorkshopCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50, description="车间编码")
    name: str = Field(..., min_length=1, max_length=100, description="车间名称")
    category: WorkshopCategory = Field(..., description="分类")
    parent_id: StrUUID | None = Field(default=None, description="父级车间ID")
    sort_order: int = Field(default=0, description="排序")
    is_active: bool = Field(default=True, description="是否启用")


class EnergyWorkshopUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    category: WorkshopCategory | None = Field(default=None)
    parent_id: StrUUID | None = Field(default=None)
    sort_order: int | None = Field(default=None)
    is_active: bool | None = Field(default=None)


class EnergyWorkshopResponse(BaseModel):
    id: StrUUID
    code: str
    name: str
    category: str
    parent_id: StrUUID | None
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── 月度记录 ──


class EnergyMonthlyRecordCreate(BaseModel):
    workshop_id: StrUUID = Field(..., description="车间ID")
    energy_type: EnergyType = Field(..., description="能源类型")
    record_date: date = Field(..., description="记录日期")
    date_range_end: date | None = Field(default=None, description="日期范围结束")
    value: float = Field(..., ge=0, description="能耗值")
    unit: str = Field(..., min_length=1, max_length=20, description="计量单位")
    source: str = Field(default="feishu", max_length=50, description="数据来源")
    remark: str | None = Field(default=None, max_length=500, description="备注")


class EnergyMonthlyRecordResponse(BaseModel):
    id: StrUUID
    workshop_id: StrUUID
    energy_type: str
    record_date: date
    date_range_end: date | None
    value: float
    unit: str
    source: str
    remark: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EnergyMonthlyRecordBatchCreate(BaseModel):
    """批量创建月度记录"""

    records: list[EnergyMonthlyRecordCreate] = Field(..., description="记录列表")


# ── 设备配置 ──


class EnergyDeviceConfigCreate(BaseModel):
    platform_code: str = Field(..., min_length=1, max_length=50, description="平台标识")
    platform_device_code: str = Field(..., min_length=1, max_length=100, description="三方平台设备编码")
    device_name: str = Field(..., min_length=1, max_length=200, description="设备名称")
    energy_type: EnergyType = Field(..., description="能源类型")
    api_endpoint: str = Field(default="", max_length=500, description="API 路径")
    workshop: str = Field(..., min_length=1, max_length=100, description="所属车间")
    production_line: str | None = Field(default=None, max_length=100, description="所属产线")
    monitor_level: MonitorLevel = Field(default="normal", description="监控等级")
    unit: str = Field(..., min_length=1, max_length=20, description="计量单位")
    collection_interval: int = Field(default=60, ge=1, description="采集间隔(分钟)")
    is_enabled: bool = Field(default=True, description="是否启用采集")
    remark: str | None = Field(default=None, max_length=500, description="备注")


class EnergyDeviceConfigUpdate(BaseModel):
    platform_code: str | None = Field(default=None, min_length=1, max_length=50)
    platform_device_code: str | None = Field(default=None, min_length=1, max_length=100)
    device_name: str | None = Field(default=None, min_length=1, max_length=200)
    energy_type: EnergyType | None = Field(default=None)
    api_endpoint: str = Field(default="", max_length=500)
    workshop: str | None = Field(default=None, min_length=1, max_length=100)
    production_line: str | None = Field(default=None, max_length=100)
    monitor_level: MonitorLevel | None = Field(default=None)
    unit: str | None = Field(default=None, min_length=1, max_length=20)
    collection_interval: int | None = Field(default=None, ge=1)
    is_enabled: bool | None = Field(default=None)
    remark: str | None = Field(default=None, max_length=500)


class EnergyDeviceConfigResponse(BaseModel):
    id: StrUUID
    platform_code: str
    platform_device_code: str
    device_name: str
    energy_type: str
    api_endpoint: str
    workshop: str
    production_line: str | None
    monitor_level: str
    unit: str
    collection_interval: int
    is_enabled: bool
    remark: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EnergyDataResponse(BaseModel):
    id: StrUUID
    device_config_id: StrUUID
    timestamp: datetime
    value: float
    unit: str
    collected_at: datetime

    model_config = {"from_attributes": True}


class EnergyStatisticsResponse(BaseModel):
    group_key: str = Field(description="分组键(车间/产线/设备名)")
    total_value: float = Field(description="能耗合计")
    unit: str = Field(description="计量单位")
    data_count: int = Field(description="数据条数")


class CollectLogResponse(BaseModel):
    id: StrUUID
    platform_code: str
    collect_time: datetime
    status: str
    device_count: int
    success_count: int
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CollectLogDeviceDetail(BaseModel):
    """采集日志中单个设备的数据详情"""

    device_name: str = Field(description="设备名称")
    platform_device_code: str = Field(description="平台设备编码")
    energy_type: str = Field(description="能源类型")
    value: float = Field(description="采集值")
    unit: str = Field(description="计量单位")
    data_timestamp: datetime = Field(description="数据时间点")


class CollectLogDetailResponse(BaseModel):
    """采集日志详情响应"""

    id: StrUUID
    platform_code: str
    collect_time: datetime
    status: str
    device_count: int
    success_count: int
    error_message: str | None
    created_at: datetime
    devices: list[CollectLogDeviceDetail] = Field(default_factory=list, description="设备数据详情列表")
    time_range_start: datetime | None = Field(default=None, description="数据覆盖起始时间")
    time_range_end: datetime | None = Field(default=None, description="数据覆盖结束时间")


class CollectTriggerRequest(BaseModel):
    platform_code: str | None = Field(
        default=None,
        description="指定平台，为空则采集所有平台",
    )


# ── 预警系统 ──

AlertLevel = Literal["info", "warning", "critical", "emergency"]
MonitorMetric = Literal["instant", "daily_total", "monthly_total"]
ThresholdType = Literal["greater_than", "less_than", "equal"]
NotifyFrequency = Literal["first", "every", "daily_summary"]
EffectiveTime = Literal["all_day", "custom"]
AlertRecordStatus = Literal["pending", "processed", "ignored"]


class EnergyAlertRuleCreate(BaseModel):
    rule_name: str = Field(..., min_length=1, max_length=200, description="规则名称")
    rule_description: str | None = Field(default=None, max_length=500, description="规则描述")
    energy_type: EnergyType = Field(..., description="能源类型")
    monitor_metric: MonitorMetric = Field(..., description="监控指标")
    threshold_type: ThresholdType = Field(..., description="阈值类型")
    threshold_value: float = Field(..., gt=0, description="阈值")
    unit: str = Field(..., min_length=1, max_length=20, description="计量单位")
    alert_level: AlertLevel = Field(..., description="预警等级")
    notify_method: list[str] = Field(..., min_length=1, description="通知方式")
    notify_users: list[str] = Field(..., min_length=1, description="通知用户列表")
    notify_frequency: NotifyFrequency = Field(default="first", description="通知频率")
    effective_time: EffectiveTime = Field(default="all_day", description="生效时段类型")
    custom_time_start: str | None = Field(default=None, description="自定义开始时间")
    custom_time_end: str | None = Field(default=None, description="自定义结束时间")
    is_enabled: bool = Field(default=True, description="是否启用")


class EnergyAlertRuleUpdate(BaseModel):
    rule_name: str | None = Field(default=None, min_length=1, max_length=200)
    rule_description: str | None = Field(default=None, max_length=500)
    energy_type: EnergyType | None = Field(default=None)
    monitor_metric: MonitorMetric | None = Field(default=None)
    threshold_type: ThresholdType | None = Field(default=None)
    threshold_value: float | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, min_length=1, max_length=20)
    alert_level: AlertLevel | None = Field(default=None)
    notify_method: list[str] | None = Field(default=None, min_length=1)
    notify_users: list[str] | None = Field(default=None, min_length=1)
    notify_frequency: NotifyFrequency | None = Field(default=None)
    effective_time: EffectiveTime | None = Field(default=None)
    custom_time_start: str | None = Field(default=None)
    custom_time_end: str | None = Field(default=None)
    is_enabled: bool | None = Field(default=None)


class EnergyAlertRuleResponse(BaseModel):
    id: StrUUID
    rule_name: str
    rule_description: str | None
    energy_type: str
    monitor_metric: str
    threshold_type: str
    threshold_value: float
    unit: str
    alert_level: str
    notify_method: list[str]
    notify_users: list[str]
    notify_frequency: str
    effective_time: str
    custom_time_start: str | None
    custom_time_end: str | None
    is_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EnergyAlertRecordResponse(BaseModel):
    id: StrUUID
    rule_id: StrUUID
    device_config_id: StrUUID | None
    energy_type: str
    alert_level: str
    trigger_value: float
    threshold_value: float
    unit: str
    alert_time: datetime
    status: str
    processed_by: str | None
    processed_at: datetime | None
    process_note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertRecordProcessRequest(BaseModel):
    status: Literal["processed", "ignored"] = Field(..., description="处理结果")
    process_note: str | None = Field(default=None, max_length=500, description="处理备注")


# ── 飞书导入 ──


class BitableCrossImportRequest(BaseModel):
    """飞书多维表格交叉表导入请求"""

    year: int | None = Field(default=None, ge=2020, le=2030, description="年份，如 2026")
    month: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$", description="月份，如 2026-06")


class FeishuEnergyImportRequest(BaseModel):
    """飞书表格导入请求"""

    spreadsheet_token: str = Field(..., description="飞书电子表格 token")
    sheet_id: str | None = Field(default=None, description="工作表 ID，为空则取第一个")
    source: str = Field(default="feishu", max_length=50, description="数据来源标识")
    dry_run: bool = Field(default=False, description="试运行，只解析不写入")


class FeishuEnergyImportResponse(BaseModel):
    """飞书表格导入结果"""

    workshops_created: int = 0
    workshops_existing: int = 0
    records_created: int = 0
    records_skipped: int = 0
    errors: list[str] = Field(default_factory=list)


# ── 单耗目标管理 ──


class UnitConsumptionTargetCreate(BaseModel):
    """创建单耗目标请求"""

    workshop_id: str = Field(..., description="车间ID (UUID)")
    target_month: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="目标月份，格式 YYYY-MM")
    target_unit_consumption: float = Field(..., gt=0, le=100, description="目标单耗（kWh/件）")


class UnitConsumptionTargetUpdate(BaseModel):
    """更新单耗目标请求"""

    target_unit_consumption: float = Field(..., gt=0, le=100, description="目标单耗（kWh/件）")


class UnitConsumptionTargetResponse(BaseModel):
    """单耗目标响应"""

    id: int
    workshop_id: str
    workshop_name: str | None = None
    target_month: str
    target_unit_consumption: float
    created_at: datetime

    model_config = {"from_attributes": True}


class AISuggestion(BaseModel):
    """AI 建议对象"""

    status: str = Field(..., description="状态：normal/warning/critical/info/unknown")
    summary: str = Field(..., description="一句话总结")
    detailed_analysis: str = Field(..., description="详细分析")
    recommendations: list[str] = Field(..., description="建议列表")
    confidence_level: Literal["high", "medium", "low"] = Field(..., description="置信度")


class AIAnalysisRequest(BaseModel):
    """AI 能耗分析请求（V2 - 支持单耗分析）"""

    workshop_id: str = Field(..., description="车间ID (UUID)")
    analysis_month: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="分析月份，格式 YYYY-MM")
    manual_production: int = Field(..., gt=0, description="当月产量（件）")
    include_ai_suggestion: bool = Field(default=True, description="是否包含 AI 建议")


class AIAnalysisResponse(BaseModel):
    """AI 能耗分析响应"""

    workshop_id: str
    workshop_name: str
    analysis_month: str
    total_energy_kwh: float
    manual_production: int
    actual_unit_consumption: float
    target_unit_consumption: float | None = None
    deviation_rate: float | None = None
    deviation_status: Literal["normal", "warning", "critical", "unknown"]
    ai_suggestion: AISuggestion | None = None

    model_config = {"from_attributes": False}
