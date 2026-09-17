from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory, get_db
from app.core.deps import RequiredUser
from app.core.exceptions import NotFoundException
from app.core.jobs import spawn_task
from app.core.response import ApiResponse
from app.modules.energy import service
from app.modules.energy.adapters import ADAPTERS
from app.modules.energy.job_store import sync_job_store
from app.modules.energy.models import EnergyUnitConsumptionTarget
from app.modules.energy.schemas import (
    AIAnalysisApiResponse,
    AIAnalysisRequest,
    AIAnalysisResponse,
    AlertRecordProcessRequest,
    BitableCrossImportRequest,
    CollectLogDetailApiResponse,
    CollectLogDetailResponse,
    CollectLogListApiResponse,
    CollectLogResponse,
    CollectTriggerApiResponse,
    CollectTriggerRequest,
    EnergyAlertRecordApiResponse,
    EnergyAlertRecordListApiResponse,
    EnergyAlertRecordResponse,
    EnergyAlertRuleApiResponse,
    EnergyAlertRuleCreate,
    EnergyAlertRuleListApiResponse,
    EnergyAlertRuleResponse,
    EnergyAlertRuleUpdate,
    EnergyDataListApiResponse,
    EnergyDataResponse,
    EnergyDeviceConfigApiResponse,
    EnergyDeviceConfigCreate,
    EnergyDeviceConfigListApiResponse,
    EnergyDeviceConfigResponse,
    EnergyDeviceConfigUpdate,
    EnergyMonthlyBatchCreateApiResponse,
    EnergyMonthlyRecordApiResponse,
    EnergyMonthlyRecordBatchCreate,
    EnergyMonthlyRecordCreate,
    EnergyMonthlyRecordListApiResponse,
    EnergyMonthlyRecordResponse,
    EnergyOverviewApiResponse,
    EnergyPlatformListApiResponse,
    EnergyPlatformResponse,
    EnergyStatisticsApiResponse,
    EnergyStatisticsResponse,
    EnergyWorkshopApiResponse,
    EnergyWorkshopCreate,
    EnergyWorkshopListApiResponse,
    EnergyWorkshopResponse,
    EnergyWorkshopUpdate,
    FeishuEnergyImportRequest,
    FeishuEnergyImportResponse,
    FeishuImportApiResponse,
    MonthlySummaryApiResponse,
    MonthlySummaryItem,
    SyncJobApiResponse,
    UnitConsumptionTargetApiResponse,
    UnitConsumptionTargetCreate,
    UnitConsumptionTargetResponse,
    UnitConsumptionTargetUpdate,
)
from app.shared.module_api import create_module_router
from app.shared.module_registry import MODULES_BY_CODE

logger = logging.getLogger(__name__)

router = create_module_router(MODULES_BY_CODE["energy"])
device_router = APIRouter()
data_router = APIRouter()
collect_router = APIRouter()
alert_router = APIRouter()
alert_record_router = APIRouter()
workshop_router = APIRouter()
monthly_router = APIRouter()
sync_router = APIRouter()


# ── 平台信息 ──


@router.get("/platforms", summary="获取已登记的平台列表", response_model=EnergyPlatformListApiResponse)
async def list_platforms(current_user: RequiredUser) -> EnergyPlatformListApiResponse:
    data = [EnergyPlatformResponse(code=code, name=adapter.platform_name) for code, adapter in ADAPTERS.items()]
    return EnergyPlatformListApiResponse(data=data)


# ── 设备配置 ──


@device_router.post("", summary="新增设备配置", response_model=EnergyDeviceConfigApiResponse)
async def create_device_config(
    data: EnergyDeviceConfigCreate,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> EnergyDeviceConfigApiResponse:
    obj = await service.create_device_config(db, data)
    await db.commit()
    return EnergyDeviceConfigApiResponse(
        data=EnergyDeviceConfigResponse(
            id=str(obj.id),
            platform_code=obj.platform_code,
            platform_device_code=obj.platform_device_code,
            device_name=obj.device_name,
            energy_type=obj.energy_type,
            api_endpoint=obj.api_endpoint,
            workshop=obj.workshop,
            production_line=obj.production_line,
            monitor_level=obj.monitor_level,
            unit=obj.unit,
            collection_interval=obj.collection_interval,
            is_enabled=obj.is_enabled,
            remark=obj.remark,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )
    )


@device_router.get("", summary="查询设备配置列表", response_model=EnergyDeviceConfigListApiResponse)
async def list_device_configs(
    current_user: RequiredUser,
    platform_code: str | None = Query(default=None, description="平台标识"),
    energy_type: str | None = Query(default=None, description="能源类型"),
    workshop: str | None = Query(default=None, description="车间"),
    is_enabled: bool | None = Query(default=None, description="是否启用"),
    keyword: str | None = Query(default=None, description="设备名称关键词搜索"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    db: AsyncSession = Depends(get_db),
) -> EnergyDeviceConfigListApiResponse:
    items, total = await service.list_device_configs(
        db,
        platform_code=platform_code,
        energy_type=energy_type,
        workshop=workshop,
        is_enabled=is_enabled,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    data = [EnergyDeviceConfigResponse.model_validate(i) for i in items]
    return EnergyDeviceConfigListApiResponse(
        data=[
            EnergyDeviceConfigResponse(
                id=str(i.id),
                platform_code=i.platform_code,
                platform_device_code=i.platform_device_code,
                device_name=i.device_name,
                energy_type=i.energy_type,
                api_endpoint=i.api_endpoint,
                workshop=i.workshop,
                production_line=i.production_line,
                monitor_level=i.monitor_level,
                unit=i.unit,
                collection_interval=i.collection_interval,
                is_enabled=i.is_enabled,
                remark=i.remark,
                created_at=i.created_at,
                updated_at=i.updated_at,
            )
            for i in data
        ],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@device_router.get("/{config_id}", summary="查询单个设备配置", response_model=EnergyDeviceConfigApiResponse)
async def get_device_config(
    config_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> EnergyDeviceConfigApiResponse:
    obj = await service.get_device_config(db, config_id)
    return EnergyDeviceConfigApiResponse(
        data=EnergyDeviceConfigResponse(
            id=str(obj.id),
            platform_code=obj.platform_code,
            platform_device_code=obj.platform_device_code,
            device_name=obj.device_name,
            energy_type=obj.energy_type,
            api_endpoint=obj.api_endpoint,
            workshop=obj.workshop,
            production_line=obj.production_line,
            monitor_level=obj.monitor_level,
            unit=obj.unit,
            collection_interval=obj.collection_interval,
            is_enabled=obj.is_enabled,
            remark=obj.remark,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )
    )


@device_router.put("/{config_id}", summary="修改设备配置", response_model=EnergyDeviceConfigApiResponse)
async def update_device_config(
    config_id: UUID,
    data: EnergyDeviceConfigUpdate,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> EnergyDeviceConfigApiResponse:
    obj = await service.update_device_config(db, config_id, data)
    await db.commit()
    return EnergyDeviceConfigApiResponse(
        data=EnergyDeviceConfigResponse(
            id=str(obj.id),
            platform_code=obj.platform_code,
            platform_device_code=obj.platform_device_code,
            device_name=obj.device_name,
            energy_type=obj.energy_type,
            api_endpoint=obj.api_endpoint,
            workshop=obj.workshop,
            production_line=obj.production_line,
            monitor_level=obj.monitor_level,
            unit=obj.unit,
            collection_interval=obj.collection_interval,
            is_enabled=obj.is_enabled,
            remark=obj.remark,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )
    )


@device_router.delete("/{config_id}", summary="删除设备配置")
async def delete_device_config(
    config_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    await service.delete_device_config(db, config_id)
    await db.commit()
    return ApiResponse(code=200, message="删除成功", data=None)


# ── 能耗数据 ──


@data_router.get("", summary="查询能耗数据", response_model=EnergyDataListApiResponse)
async def list_energy_data(
    current_user: RequiredUser,
    device_config_id: UUID | None = Query(default=None, description="设备配置ID"),
    energy_type: str | None = Query(default=None, description="能源类型"),
    workshop: str | None = Query(default=None, description="车间"),
    start_time: str = Query(..., description="开始时间(ISO格式)"),
    end_time: str = Query(..., description="结束时间(ISO格式)"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> EnergyDataListApiResponse:
    items, total = await service.list_energy_data(
        db,
        device_config_id=device_config_id,
        energy_type=energy_type,
        workshop=workshop,
        start_time=datetime.fromisoformat(start_time),
        end_time=datetime.fromisoformat(end_time),
        page=page,
        page_size=page_size,
    )
    return EnergyDataListApiResponse(
        data=[
            EnergyDataResponse(
                id=str(i.id),
                device_config_id=str(i.device_config_id),
                timestamp=i.timestamp,
                value=float(i.value),
                unit=i.unit,
                collected_at=i.collected_at,
            )
            for i in items
        ],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@data_router.get("/statistics", summary="能耗统计", response_model=EnergyStatisticsApiResponse)
async def get_energy_statistics(
    current_user: RequiredUser,
    group_by: str = Query(default="workshop", description="分组维度: workshop/production_line/device"),
    energy_type: str | None = Query(default=None, description="能源类型"),
    start_time: str = Query(..., description="开始时间(ISO格式)"),
    end_time: str = Query(..., description="结束时间(ISO格式)"),
    db: AsyncSession = Depends(get_db),
) -> EnergyStatisticsApiResponse:
    result = await service.get_energy_statistics(
        db,
        group_by=group_by,
        energy_type=energy_type,
        start_time=datetime.fromisoformat(start_time),
        end_time=datetime.fromisoformat(end_time),
    )
    return EnergyStatisticsApiResponse(
        data=[
            EnergyStatisticsResponse(
                group_key=row["group_key"],
                total_value=row["total_value"],
                unit=row["unit"],
                data_count=row["data_count"],
            )
            for row in result
        ]
    )


# ── 采集管理 ──


@collect_router.post("/trigger", summary="手动触发采集", response_model=CollectTriggerApiResponse)
async def trigger_collection(
    request: CollectTriggerRequest,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> CollectTriggerApiResponse:
    result = await service.trigger_collection(db, request)
    return CollectTriggerApiResponse(data=result, message="采集任务已执行")


@collect_router.get("/logs", summary="查询采集日志")
async def list_collect_logs(
    current_user: RequiredUser,
    platform_code: str | None = Query(default=None, description="平台标识"),
    status: str | None = Query(default=None, description="状态"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> CollectLogListApiResponse:
    items, total = await service.list_collect_logs(
        db,
        platform_code=platform_code,
        status=status,
        page=page,
        page_size=page_size,
    )
    return CollectLogListApiResponse(
        data=[
            CollectLogResponse(
                id=str(i.id),
                platform_code=i.platform_code,
                collect_time=i.collect_time,
                status=i.status,
                device_count=i.device_count,
                success_count=i.success_count,
                error_message=i.error_message,
                created_at=i.created_at,
            )
            for i in items
        ],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@collect_router.get("/logs/{log_id}/detail", summary="查询采集日志详情", response_model=CollectLogDetailApiResponse)
async def get_collect_log_detail(
    log_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> CollectLogDetailApiResponse:
    result = await service.get_collect_log_detail(db, log_id)
    return CollectLogDetailApiResponse(
        data=CollectLogDetailResponse(
            id=result["id"],
            platform_code=result["platform_code"],
            collect_time=result["collect_time"],
            status=result["status"],
            device_count=result["device_count"],
            success_count=result["success_count"],
            error_message=result["error_message"],
            created_at=result["created_at"],
            devices=result["devices"],
            time_range_start=result["time_range_start"],
            time_range_end=result["time_range_end"],
        )
    )


# ── 能源总览 ──


@router.get("/overview", summary="能源总览数据")
async def get_energy_overview(
    current_user: RequiredUser,
    energy_type: str | None = Query(default=None, description="能源类型筛选"),
    start_time: str = Query(..., description="开始时间(ISO格式)"),
    end_time: str = Query(..., description="结束时间(ISO格式)"),
    db: AsyncSession = Depends(get_db),
) -> EnergyOverviewApiResponse:
    result = await service.get_overview(
        db,
        start_time=datetime.fromisoformat(start_time),
        end_time=datetime.fromisoformat(end_time),
        energy_type=energy_type,
    )
    return EnergyOverviewApiResponse(data=result)


# ── 预警规则 ──


@alert_router.post("", summary="新增预警规则", response_model=EnergyAlertRuleApiResponse)
async def create_alert_rule(
    data: EnergyAlertRuleCreate,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> EnergyAlertRuleApiResponse:
    obj = await service.create_alert_rule(db, data)
    await db.commit()
    return EnergyAlertRuleApiResponse(
        data=EnergyAlertRuleResponse(
            id=str(obj.id),
            rule_name=obj.rule_name,
            rule_description=obj.rule_description,
            energy_type=obj.energy_type,
            monitor_metric=obj.monitor_metric,
            threshold_type=obj.threshold_type,
            threshold_value=float(obj.threshold_value),
            unit=obj.unit,
            alert_level=obj.alert_level,
            notify_method=obj.notify_method,
            notify_users=obj.notify_users,
            notify_frequency=obj.notify_frequency,
            effective_time=obj.effective_time,
            custom_time_start=obj.custom_time_start,
            custom_time_end=obj.custom_time_end,
            is_enabled=obj.is_enabled,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )
    )


@alert_router.get("", summary="查询预警规则列表", response_model=EnergyAlertRuleListApiResponse)
async def list_alert_rules(
    current_user: RequiredUser,
    energy_type: str | None = Query(default=None, description="能源类型"),
    alert_level: str | None = Query(default=None, description="预警等级"),
    is_enabled: bool | None = Query(default=None, description="是否启用"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    db: AsyncSession = Depends(get_db),
) -> EnergyAlertRuleListApiResponse:
    items, total = await service.list_alert_rules(
        db,
        energy_type=energy_type,
        alert_level=alert_level,
        is_enabled=is_enabled,
        page=page,
        page_size=page_size,
    )
    return EnergyAlertRuleListApiResponse(
        data=[
            EnergyAlertRuleResponse(
                id=str(i.id),
                rule_name=i.rule_name,
                rule_description=i.rule_description,
                energy_type=i.energy_type,
                monitor_metric=i.monitor_metric,
                threshold_type=i.threshold_type,
                threshold_value=float(i.threshold_value),
                unit=i.unit,
                alert_level=i.alert_level,
                notify_method=i.notify_method,
                notify_users=i.notify_users,
                notify_frequency=i.notify_frequency,
                effective_time=i.effective_time,
                custom_time_start=i.custom_time_start,
                custom_time_end=i.custom_time_end,
                is_enabled=i.is_enabled,
                created_at=i.created_at,
                updated_at=i.updated_at,
            )
            for i in items
        ],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@alert_router.get("/{rule_id}", summary="查询单个预警规则", response_model=EnergyAlertRuleApiResponse)
async def get_alert_rule(
    rule_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> EnergyAlertRuleApiResponse:
    obj = await service.get_alert_rule(db, rule_id)
    return EnergyAlertRuleApiResponse(
        data=EnergyAlertRuleResponse(
            id=str(obj.id),
            rule_name=obj.rule_name,
            rule_description=obj.rule_description,
            energy_type=obj.energy_type,
            monitor_metric=obj.monitor_metric,
            threshold_type=obj.threshold_type,
            threshold_value=float(obj.threshold_value),
            unit=obj.unit,
            alert_level=obj.alert_level,
            notify_method=obj.notify_method,
            notify_users=obj.notify_users,
            notify_frequency=obj.notify_frequency,
            effective_time=obj.effective_time,
            custom_time_start=obj.custom_time_start,
            custom_time_end=obj.custom_time_end,
            is_enabled=obj.is_enabled,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )
    )


@alert_router.put("/{rule_id}", summary="修改预警规则", response_model=EnergyAlertRuleApiResponse)
async def update_alert_rule(
    rule_id: UUID,
    data: EnergyAlertRuleUpdate,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> EnergyAlertRuleApiResponse:
    obj = await service.update_alert_rule(db, rule_id, data)
    await db.commit()
    return EnergyAlertRuleApiResponse(
        data=EnergyAlertRuleResponse(
            id=str(obj.id),
            rule_name=obj.rule_name,
            rule_description=obj.rule_description,
            energy_type=obj.energy_type,
            monitor_metric=obj.monitor_metric,
            threshold_type=obj.threshold_type,
            threshold_value=float(obj.threshold_value),
            unit=obj.unit,
            alert_level=obj.alert_level,
            notify_method=obj.notify_method,
            notify_users=obj.notify_users,
            notify_frequency=obj.notify_frequency,
            effective_time=obj.effective_time,
            custom_time_start=obj.custom_time_start,
            custom_time_end=obj.custom_time_end,
            is_enabled=obj.is_enabled,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )
    )


@alert_router.delete("/{rule_id}", summary="删除预警规则")
async def delete_alert_rule(
    rule_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    await service.delete_alert_rule(db, rule_id)
    await db.commit()
    return ApiResponse(code=200, message="删除成功", data=None)


# ── 预警记录 ──


@alert_record_router.get("", summary="查询预警记录列表", response_model=EnergyAlertRecordListApiResponse)
async def list_alert_records(
    current_user: RequiredUser,
    energy_type: str | None = Query(default=None, description="能源类型"),
    alert_level: str | None = Query(default=None, description="预警等级"),
    status: str | None = Query(default=None, description="处理状态"),
    start_time: str | None = Query(default=None, description="开始时间(ISO格式)"),
    end_time: str | None = Query(default=None, description="结束时间(ISO格式)"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    db: AsyncSession = Depends(get_db),
) -> EnergyAlertRecordListApiResponse:
    items, total = await service.list_alert_records(
        db,
        energy_type=energy_type,
        alert_level=alert_level,
        status=status,
        start_time=datetime.fromisoformat(start_time) if start_time else None,
        end_time=datetime.fromisoformat(end_time) if end_time else None,
        page=page,
        page_size=page_size,
    )
    return EnergyAlertRecordListApiResponse(
        data=[
            EnergyAlertRecordResponse(
                id=str(i.id),
                rule_id=str(i.rule_id) if i.rule_id else "",
                device_config_id=str(i.device_config_id) if i.device_config_id else None,
                energy_type=i.energy_type,
                alert_level=i.alert_level,
                trigger_value=float(i.trigger_value),
                threshold_value=float(i.threshold_value),
                unit=i.unit,
                alert_time=i.alert_time,
                status=i.status,
                processed_by=i.processed_by,
                processed_at=i.processed_at,
                process_note=i.process_note,
                created_at=i.created_at,
            )
            for i in items
        ],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@alert_record_router.put("/{record_id}/process", summary="处理预警记录", response_model=EnergyAlertRecordApiResponse)
async def process_alert_record(
    record_id: UUID,
    request: AlertRecordProcessRequest,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> EnergyAlertRecordApiResponse:
    obj = await service.process_alert_record(db, record_id, request)
    await db.commit()
    return EnergyAlertRecordApiResponse(
        data=EnergyAlertRecordResponse(
            id=str(obj.id),
            rule_id=str(obj.rule_id) if obj.rule_id else "",
            device_config_id=str(obj.device_config_id) if obj.device_config_id else None,
            energy_type=obj.energy_type,
            alert_level=obj.alert_level,
            trigger_value=float(obj.trigger_value),
            threshold_value=float(obj.threshold_value),
            unit=obj.unit,
            alert_time=obj.alert_time,
            status=obj.status,
            processed_by=obj.processed_by,
            processed_at=obj.processed_at,
            process_note=obj.process_note,
            created_at=obj.created_at,
        ),
        message="处理完成",
    )


router.include_router(device_router, prefix="/devices")
router.include_router(data_router, prefix="/data")
router.include_router(collect_router, prefix="/collect")
router.include_router(alert_router, prefix="/alerts/rules")
router.include_router(alert_record_router, prefix="/alerts/records")

# ── 车间管理 ──


@workshop_router.post("", summary="新增车间", response_model=EnergyWorkshopApiResponse)
async def create_workshop(
    data: EnergyWorkshopCreate,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> EnergyWorkshopApiResponse:
    obj = await service.create_workshop(db, data)
    await db.commit()
    return EnergyWorkshopApiResponse(
        data=EnergyWorkshopResponse(
            id=str(obj.id),
            code=obj.code,
            name=obj.name,
            category=obj.category,
            parent_id=str(obj.parent_id) if obj.parent_id else None,
            sort_order=obj.sort_order,
            is_active=obj.is_active,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )
    )


@workshop_router.get("", summary="查询车间列表", response_model=EnergyWorkshopListApiResponse)
async def list_workshops(
    current_user: RequiredUser,
    category: str | None = Query(default=None, description="分类"),
    is_active: bool | None = Query(default=None, description="是否启用"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=100, ge=1, le=500, description="每页条数"),
    db: AsyncSession = Depends(get_db),
) -> EnergyWorkshopListApiResponse:
    items, total = await service.list_workshops(
        db,
        category=category,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )
    return EnergyWorkshopListApiResponse(
        data=[
            EnergyWorkshopResponse(
                id=str(i.id),
                code=i.code,
                name=i.name,
                category=i.category,
                parent_id=str(i.parent_id) if i.parent_id else None,
                sort_order=i.sort_order,
                is_active=i.is_active,
                created_at=i.created_at,
                updated_at=i.updated_at,
            )
            for i in items
        ],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@workshop_router.get("/{workshop_id}", summary="查询单个车间", response_model=EnergyWorkshopApiResponse)
async def get_workshop(
    workshop_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> EnergyWorkshopApiResponse:
    obj = await service.get_workshop(db, workshop_id)
    return EnergyWorkshopApiResponse(
        data=EnergyWorkshopResponse(
            id=str(obj.id),
            code=obj.code,
            name=obj.name,
            category=obj.category,
            parent_id=str(obj.parent_id) if obj.parent_id else None,
            sort_order=obj.sort_order,
            is_active=obj.is_active,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )
    )


@workshop_router.put("/{workshop_id}", summary="修改车间", response_model=EnergyWorkshopApiResponse)
async def update_workshop(
    workshop_id: UUID,
    data: EnergyWorkshopUpdate,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> EnergyWorkshopApiResponse:
    obj = await service.update_workshop(db, workshop_id, data)
    await db.commit()
    return EnergyWorkshopApiResponse(
        data=EnergyWorkshopResponse(
            id=str(obj.id),
            code=obj.code,
            name=obj.name,
            category=obj.category,
            parent_id=str(obj.parent_id) if obj.parent_id else None,
            sort_order=obj.sort_order,
            is_active=obj.is_active,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )
    )


@workshop_router.delete("/{workshop_id}", summary="删除车间")
async def delete_workshop(
    workshop_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    await service.delete_workshop(db, workshop_id)
    await db.commit()
    return ApiResponse(code=200, message="删除成功", data=None)


# ── 月度记录 ──


@monthly_router.post("", summary="新增月度记录")
async def create_monthly_record(
    data: EnergyMonthlyRecordCreate,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> EnergyMonthlyRecordApiResponse:
    obj = await service.create_monthly_record(db, data)
    await db.commit()
    return EnergyMonthlyRecordApiResponse(
        data=EnergyMonthlyRecordResponse(
            id=str(obj.id),
            workshop_id=str(obj.workshop_id),
            energy_type=obj.energy_type,
            record_date=obj.record_date,
            date_range_end=obj.date_range_end,
            value=obj.value,
            unit=obj.unit,
            source=obj.source,
            remark=obj.remark,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )
    )


@monthly_router.post("/batch", summary="批量新增月度记录")
async def batch_create_monthly_records(
    data: EnergyMonthlyRecordBatchCreate,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> EnergyMonthlyBatchCreateApiResponse:
    objs = await service.batch_create_monthly_records(db, data.records)
    await db.commit()
    result = [
        EnergyMonthlyRecordResponse(
            id=str(o.id),
            workshop_id=str(o.workshop_id),
            energy_type=o.energy_type,
            record_date=o.record_date,
            date_range_end=o.date_range_end,
            value=o.value,
            unit=o.unit,
            source=o.source,
            remark=o.remark,
            created_at=o.created_at,
            updated_at=o.updated_at,
        )
        for o in objs
    ]
    return EnergyMonthlyBatchCreateApiResponse(data={"created": len(result), "records": result})


@monthly_router.get("", summary="查询月度记录列表")
async def list_monthly_records(
    current_user: RequiredUser,
    workshop_id: UUID | None = Query(default=None, description="车间ID"),
    energy_type: str | None = Query(default=None, description="能源类型"),
    start_date: str | None = Query(default=None, description="开始日期(YYYY-MM-DD)"),
    end_date: str | None = Query(default=None, description="结束日期(YYYY-MM-DD)"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=100, ge=1, le=500, description="每页条数"),
    db: AsyncSession = Depends(get_db),
) -> EnergyMonthlyRecordListApiResponse:
    from datetime import date as date_type

    start = date_type.fromisoformat(start_date) if start_date else None
    end = date_type.fromisoformat(end_date) if end_date else None

    items, total = await service.list_monthly_records(
        db,
        workshop_id=workshop_id,
        energy_type=energy_type,
        start_date=start,
        end_date=end,
        page=page,
        page_size=page_size,
    )
    return EnergyMonthlyRecordListApiResponse(
        data=[
            EnergyMonthlyRecordResponse(
                id=str(i.id),
                workshop_id=str(i.workshop_id),
                energy_type=i.energy_type,
                record_date=i.record_date,
                date_range_end=i.date_range_end,
                value=i.value,
                unit=i.unit,
                source=i.source,
                remark=i.remark,
                created_at=i.created_at,
                updated_at=i.updated_at,
            )
            for i in items
        ],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@monthly_router.get("/summary", summary="月度记录汇总", response_model=MonthlySummaryApiResponse)
async def get_monthly_summary(
    current_user: RequiredUser,
    workshop_id: UUID | None = Query(default=None, description="车间ID"),
    energy_type: str | None = Query(default=None, description="能源类型"),
    start_date: str | None = Query(default=None, description="开始日期(YYYY-MM-DD)"),
    end_date: str | None = Query(default=None, description="结束日期(YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
) -> MonthlySummaryApiResponse:
    from datetime import date as date_type

    start = date_type.fromisoformat(start_date) if start_date else None
    end = date_type.fromisoformat(end_date) if end_date else None

    summary = await service.get_monthly_summary(
        db,
        workshop_id=workshop_id,
        energy_type=energy_type,
        start_date=start,
        end_date=end,
    )
    summary_data = {k: MonthlySummaryItem(**v) if isinstance(v, dict) else v for k, v in summary.items()}
    return MonthlySummaryApiResponse(data={k: v.model_dump() for k, v in summary_data.items()})


@monthly_router.get("/{record_id}", summary="查询单个月度记录", response_model=EnergyMonthlyRecordApiResponse)
async def get_monthly_record(
    record_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> EnergyMonthlyRecordApiResponse:
    obj = await service.get_monthly_record(db, record_id)
    return EnergyMonthlyRecordApiResponse(
        data=EnergyMonthlyRecordResponse(
            id=str(obj.id),
            workshop_id=str(obj.workshop_id),
            energy_type=obj.energy_type,
            record_date=obj.record_date,
            date_range_end=obj.date_range_end,
            value=obj.value,
            unit=obj.unit,
            source=obj.source,
            remark=obj.remark,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )
    )


@monthly_router.delete("/{record_id}", summary="删除月度记录")
async def delete_monthly_record(
    record_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    await service.delete_monthly_record(db, record_id)
    return ApiResponse(code=200, message="删除成功", data=None)


# 注册新的路由
router.include_router(workshop_router, prefix="/workshops", tags=["车间管理"])


# ── 飞书导入 ──


@monthly_router.post("/import/feishu", summary="从飞书表格导入能耗数据")
async def import_from_feishu(
    data: FeishuEnergyImportRequest,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> FeishuImportApiResponse:
    from app.modules.energy.feishu_import import FeishuEnergyImporter

    importer = FeishuEnergyImporter()
    result = await importer.import_from_spreadsheet(
        db,
        spreadsheet_token=data.spreadsheet_token,
        sheet_id=data.sheet_id,
        source=data.source,
        dry_run=data.dry_run,
    )
    return FeishuImportApiResponse(
        data=FeishuEnergyImportResponse(
            workshops_created=result.workshops_created,
            workshops_existing=result.workshops_existing,
            records_created=result.records_created,
            records_skipped=result.records_skipped,
            errors=result.errors,
        )
    )


router.include_router(monthly_router, prefix="/monthly", tags=["月度记录"])


# ── 飞书多维表格同步 ──


@router.post("/sync/bitable", summary="从飞书多维表格同步数据")
async def sync_from_bitable(current_user: RequiredUser) -> SyncJobApiResponse:
    job_id = sync_job_store.create()

    async def _run() -> None:
        from app.modules.energy.bitable_sync import EnergyBitableSync

        async with async_session_factory() as db:
            try:
                sync_service = EnergyBitableSync()
                result = await sync_service.sync_all(db)
                sync_job_store.complete(job_id, result)
            except Exception as e:
                logger.exception("sync_from_bitable failed")
                sync_job_store.fail(job_id, str(e))

    spawn_task(_run(), name=f"energy-sync-bitable-{job_id[:8]}")
    return SyncJobApiResponse(data={"job_id": job_id, "status": "running"})


@router.post("/sync/bitable/workshops", summary="从飞书多维表格同步车间数据")
async def sync_workshops_from_bitable(current_user: RequiredUser) -> SyncJobApiResponse:
    job_id = sync_job_store.create()

    async def _run() -> None:
        from app.modules.energy.bitable_sync import EnergyBitableSync

        async with async_session_factory() as db:
            try:
                sync_service = EnergyBitableSync()
                result = await sync_service.sync_workshops(db)
                sync_job_store.complete(job_id, result)
            except Exception as e:
                logger.exception("sync_workshops_from_bitable failed")
                sync_job_store.fail(job_id, str(e))

    spawn_task(_run(), name=f"energy-sync-workshops-{job_id[:8]}")
    return SyncJobApiResponse(data={"job_id": job_id, "status": "running"})


@router.post("/sync/bitable/monthly", summary="从飞书多维表格同步月度记录")
async def sync_monthly_from_bitable(current_user: RequiredUser) -> SyncJobApiResponse:
    job_id = sync_job_store.create()

    async def _run() -> None:
        from app.modules.energy.bitable_sync import EnergyBitableSync

        async with async_session_factory() as db:
            try:
                sync_service = EnergyBitableSync()
                result = await sync_service.sync_monthly_records(db)
                sync_job_store.complete(job_id, result)
            except Exception as e:
                logger.exception("sync_monthly_from_bitable failed")
                sync_job_store.fail(job_id, str(e))

    spawn_task(_run(), name=f"energy-sync-monthly-{job_id[:8]}")
    return SyncJobApiResponse(data={"job_id": job_id, "status": "running"})


@router.post("/sync/bitable/cross-import", summary="从飞书多维表格交叉表导入数据")
async def cross_import_from_bitable(body: BitableCrossImportRequest, current_user: RequiredUser) -> SyncJobApiResponse:
    job_id = sync_job_store.create()

    async def _run() -> None:
        from app.modules.energy.bitable_cross_import import EnergyBitableCrossImport

        async with async_session_factory() as db:
            try:
                importer = EnergyBitableCrossImport()
                if body.year:
                    result = await importer.import_year(db, body.year)
                elif body.month:
                    result = await importer.import_month(db, body.month)
                else:
                    sync_job_store.fail(job_id, "请提供 year 或 month 参数")
                    return
                sync_job_store.complete(job_id, result)
            except Exception as e:
                logger.exception("cross_import_from_bitable failed")
                sync_job_store.fail(job_id, str(e))

    spawn_task(_run(), name=f"energy-cross-import-{job_id[:8]}")
    return SyncJobApiResponse(data={"job_id": job_id, "status": "running"})


@router.post("/sync/bitable/daily-import", summary="从飞书表格导入每日数据并检查预警")
async def daily_import_from_bitable(current_user: RequiredUser) -> SyncJobApiResponse:
    job_id = sync_job_store.create()

    async def _run() -> None:
        from sqlalchemy import distinct, select

        from app.modules.energy.bitable_daily_import import EnergyBitableDailyImport
        from app.modules.energy.models import EnergyDailyData

        async with async_session_factory() as db:
            try:
                importer = EnergyBitableDailyImport()
                result = await importer.import_all_tables(db)

                dates_result = await db.execute(
                    select(distinct(EnergyDailyData.date))
                    .where(EnergyDailyData.is_alert, EnergyDailyData.alert_record_id.is_(None))
                    .order_by(EnergyDailyData.date.desc())
                )
                dates_to_check = [str(d) for d in dates_result.scalars().all()]

                total_alerts = 0
                for date_str in dates_to_check:
                    check_date = date.fromisoformat(date_str)
                    alert_records = await importer.check_alerts(db, check_date)
                    total_alerts += len(alert_records)

                result["auto_check_alerts"] = total_alerts
                sync_job_store.complete(job_id, result)
            except Exception as e:
                logger.exception("daily_import_from_bitable failed")
                sync_job_store.fail(job_id, str(e))

    spawn_task(_run(), name=f"energy-daily-import-{job_id[:8]}")
    return SyncJobApiResponse(data={"job_id": job_id, "status": "running"})


@router.get("/jobs/{job_id}", summary="查询异步任务状态")
async def get_job_status(job_id: str, current_user: RequiredUser) -> SyncJobApiResponse:
    job = sync_job_store.get(job_id)
    if not job:
        raise NotFoundException("job", job_id)
    return SyncJobApiResponse(data=job)


# ── 单耗目标 ──────────────────────────────────────────────────────────────


def _target_to_response(target: EnergyUnitConsumptionTarget) -> dict[str, Any]:
    """将 ORM 对象转换为响应格式"""
    return {
        "id": str(target.id),
        "workshop_id": str(target.workshop_id),
        "target_month": target.target_month.strftime("%Y-%m"),
        "target_unit_consumption": float(target.target_unit_consumption),
        "created_at": target.created_at.isoformat() if target.created_at else None,
    }


@router.post("/targets", summary="创建单耗目标")
async def create_target(
    body: UnitConsumptionTargetCreate,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> UnitConsumptionTargetApiResponse:
    target = await service.create_target(
        db,
        workshop_id=UUID(body.workshop_id),
        target_month=body.target_month,
        target_unit_consumption=body.target_unit_consumption,
    )
    return UnitConsumptionTargetApiResponse(
        data=UnitConsumptionTargetResponse(
            id=str(target.id),
            workshop_id=str(target.workshop_id),
            target_month=target.target_month.strftime("%Y-%m"),
            target_unit_consumption=float(target.target_unit_consumption),
            created_at=target.created_at,
        )
    )


@router.get("/targets/{workshop_id}/{target_month}", summary="查询单耗目标")
async def get_target(
    workshop_id: UUID,
    target_month: str,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> UnitConsumptionTargetApiResponse:
    target = await service.get_target(db, workshop_id, target_month)
    if not target:
        raise NotFoundException("单耗目标", f"{workshop_id}-{target_month}")
    return UnitConsumptionTargetApiResponse(
        data=UnitConsumptionTargetResponse(
            id=str(target.id),
            workshop_id=str(target.workshop_id),
            target_month=target.target_month.strftime("%Y-%m"),
            target_unit_consumption=float(target.target_unit_consumption),
            created_at=target.created_at,
        )
    )


@router.put("/targets/{target_id}", summary="更新单耗目标")
async def update_target(
    target_id: UUID,
    body: UnitConsumptionTargetUpdate,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> UnitConsumptionTargetApiResponse:
    target = await service.update_target(db, target_id, body.target_unit_consumption)
    return UnitConsumptionTargetApiResponse(
        data=UnitConsumptionTargetResponse(
            id=str(target.id),
            workshop_id=str(target.workshop_id),
            target_month=target.target_month.strftime("%Y-%m"),
            target_unit_consumption=float(target.target_unit_consumption),
            created_at=target.created_at,
        )
    )


@router.post("/ai-analysis-v2", summary="AI 能耗分析 V2（支持多产品和单耗）")
async def ai_analysis_v2(
    body: AIAnalysisRequest,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> AIAnalysisApiResponse:
    """执行 AI 能耗分析，支持多产品产量输入和单耗计算"""
    from uuid import UUID

    from app.modules.energy.schemas import ProductionItemDetail

    result = await service.analyze_energy_v2(
        db,
        workshop_id=UUID(body.workshop_id),
        analysis_month=body.analysis_month,
        production_items=body.production_items,
        include_ai_suggestion=body.include_ai_suggestion,
    )

    # 构造产品明细
    production_items_detail = [
        ProductionItemDetail(
            product_name=item["product_name"],
            quantity=item["quantity"],
            conversion_factor=item["conversion_factor"],
            converted_quantity=item["converted_quantity"],
        )
        for item in result["production_items"]
    ]

    response = AIAnalysisResponse(
        workshop_id=result["workshop_id"],
        workshop_name=result["workshop_name"],
        analysis_month=result["analysis_month"],
        total_energy_kwh=result["total_energy_kwh"],
        production_items=production_items_detail,
        converted_production=result["converted_production"],
        actual_unit_consumption=result["actual_unit_consumption"],
        target_unit_consumption=result["target_unit_consumption"],
        deviation_rate=result["deviation_rate"],
        deviation_status=result["deviation_status"],
        ai_suggestion=result["ai_suggestion"],
    )

    return AIAnalysisApiResponse(data=response)
