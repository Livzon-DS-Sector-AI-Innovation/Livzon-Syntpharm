from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory, get_db
from app.core.deps import RequiredUser
from app.core.exceptions import NotFoundException
from app.core.jobs import spawn_task
from app.core.response import paginated_response, success_response
from app.modules.energy import service
from app.modules.energy.adapters import ADAPTERS
from app.modules.energy.job_store import sync_job_store
from app.modules.energy.models import EnergyUnitConsumptionTarget
from app.modules.energy.schemas import (
    AIAnalysisRequest,
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
    UnitConsumptionTargetCreate,
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


@router.get("/platforms", summary="获取已登记的平台列表")
async def list_platforms(current_user: RequiredUser) -> JSONResponse:
    data = [{"code": code, "name": adapter.platform_name} for code, adapter in ADAPTERS.items()]
    return success_response(data)


# ── 设备配置 ──


@device_router.post("", summary="新增设备配置")
async def create_device_config(
    data: EnergyDeviceConfigCreate,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    obj = await service.create_device_config(db, data)
    return success_response(EnergyDeviceConfigResponse.model_validate(obj).model_dump())


@device_router.get("", summary="查询设备配置列表")
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
) -> JSONResponse:
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
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    obj = await service.get_device_config(db, config_id)
    return success_response(EnergyDeviceConfigResponse.model_validate(obj).model_dump())


@device_router.put("/{config_id}", summary="修改设备配置")
async def update_device_config(
    config_id: UUID,
    data: EnergyDeviceConfigUpdate,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    obj = await service.update_device_config(db, config_id, data)
    return success_response(EnergyDeviceConfigResponse.model_validate(obj).model_dump())


@device_router.delete("/{config_id}", summary="删除设备配置")
async def delete_device_config(
    config_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    await service.delete_device_config(db, config_id)
    return success_response(None, message="删除成功")


# ── 能耗数据 ──


@data_router.get("", summary="查询能耗数据")
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
) -> JSONResponse:
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
    current_user: RequiredUser,
    group_by: str = Query(default="workshop", description="分组维度: workshop/production_line/device"),
    energy_type: str | None = Query(default=None, description="能源类型"),
    start_time: str = Query(..., description="开始时间(ISO格式)"),
    end_time: str = Query(..., description="结束时间(ISO格式)"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
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
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    result = await service.trigger_collection(db, request)
    return success_response(result, message="采集任务已执行")


@collect_router.get("/logs", summary="查询采集日志")
async def list_collect_logs(
    current_user: RequiredUser,
    platform_code: str | None = Query(default=None, description="平台标识"),
    status: str | None = Query(default=None, description="状态"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
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
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    result = await service.get_collect_log_detail(db, log_id)
    return success_response(result)


# ── 能源总览 ──


@router.get("/overview", summary="能源总览数据")
async def get_energy_overview(
    current_user: RequiredUser,
    energy_type: str | None = Query(default=None, description="能源类型筛选"),
    start_time: str = Query(..., description="开始时间(ISO格式)"),
    end_time: str = Query(..., description="结束时间(ISO格式)"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
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
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    obj = await service.create_alert_rule(db, data)
    return success_response(EnergyAlertRuleResponse.model_validate(obj).model_dump())


@alert_router.get("", summary="查询预警规则列表")
async def list_alert_rules(
    current_user: RequiredUser,
    energy_type: str | None = Query(default=None, description="能源类型"),
    alert_level: str | None = Query(default=None, description="预警等级"),
    is_enabled: bool | None = Query(default=None, description="是否启用"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
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
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    obj = await service.get_alert_rule(db, rule_id)
    return success_response(EnergyAlertRuleResponse.model_validate(obj).model_dump())


@alert_router.put("/{rule_id}", summary="修改预警规则")
async def update_alert_rule(
    rule_id: UUID,
    data: EnergyAlertRuleUpdate,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    obj = await service.update_alert_rule(db, rule_id, data)
    return success_response(EnergyAlertRuleResponse.model_validate(obj).model_dump())


@alert_router.delete("/{rule_id}", summary="删除预警规则")
async def delete_alert_rule(
    rule_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    await service.delete_alert_rule(db, rule_id)
    return success_response(None, message="删除成功")


# ── 预警记录 ──


@alert_record_router.get("", summary="查询预警记录列表")
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
) -> JSONResponse:
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
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
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
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    obj = await service.create_workshop(db, data)
    return success_response(EnergyWorkshopResponse.model_validate(obj).model_dump())


@workshop_router.get("", summary="查询车间列表")
async def list_workshops(
    current_user: RequiredUser,
    category: str | None = Query(default=None, description="分类"),
    is_active: bool | None = Query(default=None, description="是否启用"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=100, ge=1, le=500, description="每页条数"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
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
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    obj = await service.get_workshop(db, workshop_id)
    return success_response(EnergyWorkshopResponse.model_validate(obj).model_dump())


@workshop_router.put("/{workshop_id}", summary="修改车间")
async def update_workshop(
    workshop_id: UUID,
    data: EnergyWorkshopUpdate,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    obj = await service.update_workshop(db, workshop_id, data)
    return success_response(EnergyWorkshopResponse.model_validate(obj).model_dump())


@workshop_router.delete("/{workshop_id}", summary="删除车间")
async def delete_workshop(
    workshop_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    await service.delete_workshop(db, workshop_id)
    return success_response(None, message="删除成功")


# ── 月度记录 ──


@monthly_router.post("", summary="新增月度记录")
async def create_monthly_record(
    data: EnergyMonthlyRecordCreate,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    obj = await service.create_monthly_record(db, data)
    return success_response(EnergyMonthlyRecordResponse.model_validate(obj).model_dump())


@monthly_router.post("/batch", summary="批量新增月度记录")
async def batch_create_monthly_records(
    data: EnergyMonthlyRecordBatchCreate,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    objs = await service.batch_create_monthly_records(db, data.records)
    result = [EnergyMonthlyRecordResponse.model_validate(o).model_dump() for o in objs]
    return success_response(result)


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
) -> JSONResponse:
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
    current_user: RequiredUser,
    workshop_id: UUID | None = Query(default=None, description="车间ID"),
    energy_type: str | None = Query(default=None, description="能源类型"),
    start_date: str | None = Query(default=None, description="开始日期(YYYY-MM-DD)"),
    end_date: str | None = Query(default=None, description="结束日期(YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
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
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    obj = await service.get_monthly_record(db, record_id)
    return success_response(EnergyMonthlyRecordResponse.model_validate(obj).model_dump())


@monthly_router.delete("/{record_id}", summary="删除月度记录")
async def delete_monthly_record(
    record_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    await service.delete_monthly_record(db, record_id)
    return success_response(None, message="删除成功")


# 注册新的路由
router.include_router(workshop_router, prefix="/workshops", tags=["车间管理"])


# ── 飞书导入 ──


@monthly_router.post("/import/feishu", summary="从飞书表格导入能耗数据")
async def import_from_feishu(
    data: FeishuEnergyImportRequest,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
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
async def sync_from_bitable(current_user: RequiredUser) -> JSONResponse:
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
    return success_response({"job_id": job_id, "status": "running"})


@router.post("/sync/bitable/workshops", summary="从飞书多维表格同步车间数据")
async def sync_workshops_from_bitable(current_user: RequiredUser) -> JSONResponse:
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
    return success_response({"job_id": job_id, "status": "running"})


@router.post("/sync/bitable/monthly", summary="从飞书多维表格同步月度记录")
async def sync_monthly_from_bitable(current_user: RequiredUser) -> JSONResponse:
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
    return success_response({"job_id": job_id, "status": "running"})


@router.post("/sync/bitable/cross-import", summary="从飞书多维表格交叉表导入数据")
async def cross_import_from_bitable(body: BitableCrossImportRequest, current_user: RequiredUser) -> JSONResponse:
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
    return success_response({"job_id": job_id, "status": "running"})


@router.post("/sync/bitable/daily-import", summary="从飞书表格导入每日数据并检查预警")
async def daily_import_from_bitable(current_user: RequiredUser) -> JSONResponse:
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
    return success_response({"job_id": job_id, "status": "running"})


@router.get("/jobs/{job_id}", summary="查询异步任务状态")
async def get_job_status(job_id: str, current_user: RequiredUser) -> JSONResponse:
    job = sync_job_store.get(job_id)
    if not job:
        raise NotFoundException("job", job_id)
    return success_response(job)


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
) -> JSONResponse:

    target = await service.create_target(
        db,
        workshop_id=UUID(body.workshop_id),
        target_month=body.target_month,
        target_unit_consumption=body.target_unit_consumption,
    )
    return success_response(_target_to_response(target))


@router.get("/targets/{workshop_id}/{target_month}", summary="查询单耗目标")
async def get_target(
    workshop_id: UUID,
    target_month: str,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    target = await service.get_target(db, workshop_id, target_month)
    if not target:
        raise NotFoundException("单耗目标", f"{workshop_id}-{target_month}")
    return success_response(_target_to_response(target))


@router.put("/targets/{target_id}", summary="更新单耗目标")
async def update_target(
    target_id: UUID,
    body: UnitConsumptionTargetUpdate,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    target = await service.update_target(db, target_id, body.target_unit_consumption)
    return success_response(_target_to_response(target))


@router.post("/ai-analysis-v2", summary="AI 能耗分析 V2（支持多产品和单耗）")
async def ai_analysis_v2(
    body: AIAnalysisRequest,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """执行 AI 能耗分析，支持多产品产量输入和单耗计算"""
    from uuid import UUID

    from app.modules.energy.schemas import AIAnalysisResponse, ProductionItemDetail

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

    return success_response(response.model_dump())
