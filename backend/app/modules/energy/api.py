from __future__ import annotations

from datetime import date, datetime
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.core.exceptions import AppException
from app.core.response import error_response, paginated_response, success_response
from app.modules.energy import service
from app.modules.energy.adapters import ADAPTERS
from app.modules.energy.schemas import (
    AlertRecordProcessRequest,
    BitableCrossImportRequest,
    CollectLogResponse,
    CollectTriggerRequest,
    EnergyAlertRecordResponse,
    EnergyAlertRuleCreate,
    EnergyAlertRuleResponse,
    EnergyAlertRuleUpdate,
    EnergyDataResponse,
    EnergyDeviceConfigCreate,
    EnergyDeviceConfigResponse,
    EnergyDeviceConfigUpdate,
    EnergyMonthlyRecordBatchCreate,
    EnergyMonthlyRecordCreate,
    EnergyMonthlyRecordResponse,
    EnergyWorkshopCreate,
    EnergyWorkshopResponse,
    EnergyWorkshopUpdate,
    FeishuEnergyImportRequest,
    FeishuEnergyImportResponse,
)
from app.shared.module_api import create_module_router
from app.shared.module_registry import MODULES_BY_CODE

router = create_module_router(MODULES_BY_CODE["energy"])
device_router = APIRouter()
data_router = APIRouter()
collect_router = APIRouter()
alert_router = APIRouter()
alert_record_router = APIRouter()
workshop_router = APIRouter()
monthly_router = APIRouter()



def _require_user(current_user: CurrentUser) -> uuid.UUID:
    if not current_user:
        raise AppException(message="需要登录才能执行此操作", status_code=401)
    return current_user.id

# ── 平台信息 ──


@router.get("/platforms", summary="获取已登记的平台列表")
async def list_platforms() -> JSONResponse:
    data = [{"code": code, "name": adapter.platform_name} for code, adapter in ADAPTERS.items()]
    return success_response(data)


# ── 设备配置 ──


@device_router.post("", summary="新增设备配置")
async def create_device_config(
    data: EnergyDeviceConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
    obj = await service.create_device_config(db, data)
    return success_response(EnergyDeviceConfigResponse.model_validate(obj).model_dump())


@device_router.get("", summary="查询设备配置列表")
async def list_device_configs(
    platform_code: str | None = Query(default=None, description="平台标识"),
    energy_type: str | None = Query(default=None, description="能源类型"),
    workshop: str | None = Query(default=None, description="车间"),
    is_enabled: bool | None = Query(default=None, description="是否启用"),
    keyword: str | None = Query(default=None, description="设备名称关键词搜索"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
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
    data = [EnergyDeviceConfigResponse.model_validate(i).model_dump() for i in items]
    return paginated_response(data, page, page_size, total)


@device_router.get("/{config_id}", summary="查询单个设备配置")
async def get_device_config(
    config_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
    obj = await service.get_device_config(db, config_id)
    return success_response(EnergyDeviceConfigResponse.model_validate(obj).model_dump())


@device_router.put("/{config_id}", summary="修改设备配置")
async def update_device_config(
    config_id: UUID,
    data: EnergyDeviceConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
    obj = await service.update_device_config(db, config_id, data)
    return success_response(EnergyDeviceConfigResponse.model_validate(obj).model_dump())


@device_router.delete("/{config_id}", summary="删除设备配置")
async def delete_device_config(
    config_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
    await service.delete_device_config(db, config_id)
    return success_response(None, message="删除成功")


# ── 能耗数据 ──


@data_router.get("", summary="查询能耗数据")
async def list_energy_data(
    device_config_id: UUID | None = Query(default=None, description="设备配置ID"),
    energy_type: str | None = Query(default=None, description="能源类型"),
    workshop: str | None = Query(default=None, description="车间"),
    start_time: str = Query(..., description="开始时间(ISO格式)"),
    end_time: str = Query(..., description="结束时间(ISO格式)"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
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
    data = [EnergyDataResponse.model_validate(i).model_dump() for i in items]
    return paginated_response(data, page, page_size, total)


@data_router.get("/statistics", summary="能耗统计")
async def get_energy_statistics(
    group_by: str = Query(default="workshop", description="分组维度: workshop/production_line/device"),
    energy_type: str | None = Query(default=None, description="能源类型"),
    start_time: str = Query(..., description="开始时间(ISO格式)"),
    end_time: str = Query(..., description="结束时间(ISO格式)"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
    result = await service.get_energy_statistics(
        db,
        group_by=group_by,
        energy_type=energy_type,
        start_time=datetime.fromisoformat(start_time),
        end_time=datetime.fromisoformat(end_time),
    )
    return success_response(result)


# ── 采集管理 ──


@collect_router.post("/trigger", summary="手动触发采集")
async def trigger_collection(
    request: CollectTriggerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
    result = await service.trigger_collection(db, request)
    return success_response(result, message="采集任务已执行")


@collect_router.get("/logs", summary="查询采集日志")
async def list_collect_logs(
    platform_code: str | None = Query(default=None, description="平台标识"),
    status: str | None = Query(default=None, description="状态"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
    items, total = await service.list_collect_logs(
        db,
        platform_code=platform_code,
        status=status,
        page=page,
        page_size=page_size,
    )
    data = [CollectLogResponse.model_validate(i).model_dump() for i in items]
    return paginated_response(data, page, page_size, total)


@collect_router.get("/logs/{log_id}/detail", summary="查询采集日志详情")
async def get_collect_log_detail(
    log_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
    result = await service.get_collect_log_detail(db, log_id)
    return success_response(result)


# ── 能源总览 ──


@router.get("/overview", summary="能源总览数据")
async def get_energy_overview(
    energy_type: str | None = Query(default=None, description="能源类型筛选"),
    start_time: str = Query(..., description="开始时间(ISO格式)"),
    end_time: str = Query(..., description="结束时间(ISO格式)"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
    result = await service.get_overview(
        db,
        start_time=datetime.fromisoformat(start_time),
        end_time=datetime.fromisoformat(end_time),
        energy_type=energy_type,
    )
    return success_response(result)


# ── 预警规则 ──


@alert_router.post("", summary="新增预警规则")
async def create_alert_rule(
    data: EnergyAlertRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
    obj = await service.create_alert_rule(db, data)
    return success_response(EnergyAlertRuleResponse.model_validate(obj).model_dump())


@alert_router.get("", summary="查询预警规则列表")
async def list_alert_rules(
    energy_type: str | None = Query(default=None, description="能源类型"),
    alert_level: str | None = Query(default=None, description="预警等级"),
    is_enabled: bool | None = Query(default=None, description="是否启用"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
    items, total = await service.list_alert_rules(
        db,
        energy_type=energy_type,
        alert_level=alert_level,
        is_enabled=is_enabled,
        page=page,
        page_size=page_size,
    )
    data = [EnergyAlertRuleResponse.model_validate(i).model_dump() for i in items]
    return paginated_response(data, page, page_size, total)


@alert_router.get("/{rule_id}", summary="查询单个预警规则")
async def get_alert_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
    obj = await service.get_alert_rule(db, rule_id)
    return success_response(EnergyAlertRuleResponse.model_validate(obj).model_dump())


@alert_router.put("/{rule_id}", summary="修改预警规则")
async def update_alert_rule(
    rule_id: UUID,
    data: EnergyAlertRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
    obj = await service.update_alert_rule(db, rule_id, data)
    return success_response(EnergyAlertRuleResponse.model_validate(obj).model_dump())


@alert_router.delete("/{rule_id}", summary="删除预警规则")
async def delete_alert_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
    await service.delete_alert_rule(db, rule_id)
    return success_response(None, message="删除成功")


# ── 预警记录 ──


@alert_record_router.get("", summary="查询预警记录列表")
async def list_alert_records(
    energy_type: str | None = Query(default=None, description="能源类型"),
    alert_level: str | None = Query(default=None, description="预警等级"),
    status: str | None = Query(default=None, description="处理状态"),
    start_time: str | None = Query(default=None, description="开始时间(ISO格式)"),
    end_time: str | None = Query(default=None, description="结束时间(ISO格式)"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
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
    data = [EnergyAlertRecordResponse.model_validate(i).model_dump() for i in items]
    return paginated_response(data, page, page_size, total)


@alert_record_router.put("/{record_id}/process", summary="处理预警记录")
async def process_alert_record(
    record_id: UUID,
    request: AlertRecordProcessRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
    obj = await service.process_alert_record(db, record_id, request)
    return success_response(
        EnergyAlertRecordResponse.model_validate(obj).model_dump(),
        message="处理完成",
    )


router.include_router(device_router, prefix="/devices")
router.include_router(data_router, prefix="/data")
router.include_router(collect_router, prefix="/collect")
router.include_router(alert_router, prefix="/alerts/rules")
router.include_router(alert_record_router, prefix="/alerts/records")

# ── 车间管理 ──


@workshop_router.post("", summary="新增车间")
async def create_workshop(
    data: EnergyWorkshopCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
    obj = await service.create_workshop(db, data)
    return success_response(EnergyWorkshopResponse.model_validate(obj).model_dump())


@workshop_router.get("", summary="查询车间列表")
async def list_workshops(
    category: str | None = Query(default=None, description="分类"),
    is_active: bool | None = Query(default=None, description="是否启用"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=100, ge=1, le=500, description="每页条数"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
    items, total = await service.list_workshops(
        db,
        category=category,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )
    data = [EnergyWorkshopResponse.model_validate(i).model_dump() for i in items]
    return paginated_response(data, page, page_size, total)


@workshop_router.get("/{workshop_id}", summary="查询单个车间")
async def get_workshop(
    workshop_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
    obj = await service.get_workshop(db, workshop_id)
    return success_response(EnergyWorkshopResponse.model_validate(obj).model_dump())


@workshop_router.put("/{workshop_id}", summary="修改车间")
async def update_workshop(
    workshop_id: UUID,
    data: EnergyWorkshopUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
    obj = await service.update_workshop(db, workshop_id, data)
    return success_response(EnergyWorkshopResponse.model_validate(obj).model_dump())


@workshop_router.delete("/{workshop_id}", summary="删除车间")
async def delete_workshop(
    workshop_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
    await service.delete_workshop(db, workshop_id)
    return success_response(None, message="删除成功")


# ── 月度记录 ──


@monthly_router.post("", summary="新增月度记录")
async def create_monthly_record(
    data: EnergyMonthlyRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
    obj = await service.create_monthly_record(db, data)
    return success_response(EnergyMonthlyRecordResponse.model_validate(obj).model_dump())


@monthly_router.post("/batch", summary="批量新增月度记录")
async def batch_create_monthly_records(
    data: EnergyMonthlyRecordBatchCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
    objs = await service.batch_create_monthly_records(db, data.records)
    result = [EnergyMonthlyRecordResponse.model_validate(o).model_dump() for o in objs]
    return success_response(result)


@monthly_router.get("", summary="查询月度记录列表")
async def list_monthly_records(
    workshop_id: UUID | None = Query(default=None, description="车间ID"),
    energy_type: str | None = Query(default=None, description="能源类型"),
    start_date: str | None = Query(default=None, description="开始日期(YYYY-MM-DD)"),
    end_date: str | None = Query(default=None, description="结束日期(YYYY-MM-DD)"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=100, ge=1, le=500, description="每页条数"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
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
    data = [EnergyMonthlyRecordResponse.model_validate(i).model_dump() for i in items]
    return paginated_response(data, page, page_size, total)


@monthly_router.get("/summary", summary="月度记录汇总")
async def get_monthly_summary(
    workshop_id: UUID | None = Query(default=None, description="车间ID"),
    energy_type: str | None = Query(default=None, description="能源类型"),
    start_date: str | None = Query(default=None, description="开始日期(YYYY-MM-DD)"),
    end_date: str | None = Query(default=None, description="结束日期(YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
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
    return success_response(summary)


@monthly_router.get("/{record_id}", summary="查询单个月度记录")
async def get_monthly_record(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
    obj = await service.get_monthly_record(db, record_id)
    return success_response(EnergyMonthlyRecordResponse.model_validate(obj).model_dump())


@monthly_router.delete("/{record_id}", summary="删除月度记录")
async def delete_monthly_record(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
    await service.delete_monthly_record(db, record_id)
    return success_response(None, message="删除成功")


# 注册新的路由
router.include_router(workshop_router, prefix="/workshops", tags=["车间管理"])


# ── 飞书导入 ──


@monthly_router.post("/import/feishu", summary="从飞书表格导入能耗数据")
async def import_from_feishu(
    data: FeishuEnergyImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
    from app.modules.energy.feishu_import import FeishuEnergyImporter

    importer = FeishuEnergyImporter()
    result = await importer.import_from_spreadsheet(
        db,
        spreadsheet_token=data.spreadsheet_token,
        sheet_id=data.sheet_id,
        source=data.source,
        dry_run=data.dry_run,
    )
    return success_response(
        FeishuEnergyImportResponse(
            workshops_created=result.workshops_created,
            workshops_existing=result.workshops_existing,
            records_created=result.records_created,
            records_skipped=result.records_skipped,
            errors=result.errors,
        ).model_dump()
    )


router.include_router(monthly_router, prefix="/monthly", tags=["月度记录"])


# ── 飞书多维表格同步 ──


@router.post("/sync/bitable", summary="从飞书多维表格同步数据")
async def sync_from_bitable(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
    """从飞书多维表格同步车间和月度记录数据。"""
    from app.modules.energy.bitable_sync import EnergyBitableSync

    sync_service = EnergyBitableSync()
    result = await sync_service.sync_all(db)
    return success_response(result)


@router.post("/sync/bitable/workshops", summary="从飞书多维表格同步车间数据")
async def sync_workshops_from_bitable(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
    """从飞书多维表格同步车间数据。"""
    from app.modules.energy.bitable_sync import EnergyBitableSync

    sync_service = EnergyBitableSync()
    result = await sync_service.sync_workshops(db)
    return success_response(result)


@router.post("/sync/bitable/monthly", summary="从飞书多维表格同步月度记录")
async def sync_monthly_from_bitable(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
    """从飞书多维表格同步月度能耗记录。"""
    from app.modules.energy.bitable_sync import EnergyBitableSync

    sync_service = EnergyBitableSync()
    result = await sync_service.sync_monthly_records(db)
    return success_response(result)


@router.post("/sync/bitable/cross-import", summary="从飞书多维表格交叉表导入数据")
async def cross_import_from_bitable(
    body: BitableCrossImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
    """从飞书多维表格交叉表导入能源数据。

    请求体:
    - year: 年份（如 2026）
    - 或 month: 月份表名（如 "2026-06"）
    """
    from app.modules.energy.bitable_cross_import import EnergyBitableCrossImport

    importer = EnergyBitableCrossImport()

    if body.year:
        result = await importer.import_year(db, body.year)
    elif body.month:
        result = await importer.import_month(db, body.month)
    else:
        return error_response("请提供 year 或 month 参数", 400)

    return success_response(result)


@router.post("/sync/bitable/daily-import", summary="从飞书表格导入每日数据并检查预警")
async def daily_import_from_bitable(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> JSONResponse:
    _require_user(current_user)
    """手动触发从飞书表格导入每日数据，导入后自动检查预警"""
    from app.modules.energy.bitable_daily_import import EnergyBitableDailyImport

    importer = EnergyBitableDailyImport()
    result = await importer.import_all_tables(db)

    # 导入后自动检查所有有预警数据的日期
    from sqlalchemy import distinct, select

    from app.modules.energy.models import EnergyDailyData

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

    return success_response(result)
