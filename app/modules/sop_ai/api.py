"""SOP AI 模块 API 路由

提供文件合规校验的 RESTful API 接口。
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.modules.sop_ai import schemas
from app.modules.sop_ai.service import SopAiCheckService

logger = logging.getLogger(__name__)

router = APIRouter()


# ============ 配置管理接口 ============


@router.get("/config", summary="获取配置列表")
async def list_config(
    db: AsyncSession = Depends(get_db),
):
    """获取所有配置"""
    service = SopAiCheckService(db)
    configs = await service.list_config()
    return {"code": 200, "message": "success", "data": configs}


@router.get("/config/{config_key}", summary="获取单个配置")
async def get_config(
    config_key: str,
    db: AsyncSession = Depends(get_db),
) -> dict():
    """获取指定配置"""
    service = SopAiCheckService(db)
    value = await service.get_config(config_key)
    return ApiResponse(data={"config_key": config_key, "config_value": value})


@router.put("/config/{config_key}", summary="更新配置")
async def update_config(
    config_key: str,
    request: schemas.SopAiConfigUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict():
    """更新配置"""
    service = SopAiCheckService(db)
    result = await service.set_config(
        config_key=config_key,
        config_value=request.config_value,
        description=request.description,
        operator=request.operator,
    )
    return ApiResponse(data=result)


# ============ 单文件预审接口 ============


@router.post("/check/single", summary="单文件预审")
async def single_check(
    request: schemas.SingleCheckRequest,
    db: AsyncSession = Depends(get_db),
) ->dict:
    """对单个文件进行预审校验"""
    service = SopAiCheckService(db)
    result = await service.single_check(
        file_path=request.file_path,
        file_name=request.file_name,
        check_type=request.check_type,
        operator=request.operator,
    )
    return ApiResponse(data=result)


# ============ 批量巡检接口 ============


@router.post("/check/batch", summary="批量巡检")
async def batch_check(
    request: schemas.BatchCheckRequest,
    db: AsyncSession = Depends(get_db),
) ->dict:
    """对多个文件进行批量巡检"""
    service = SopAiCheckService(db)
    result = await service.batch_check(
        file_paths=request.file_paths,
        check_type=request.check_type,
        operator=request.operator,
    )
    return ApiResponse(data=result)


# ============ 记录查询接口 ============


@router.get("/records", summary="获取校验记录列表")
async def list_records(
    status: Optional[str] = Query(None, description="状态过滤"),
    file_code: Optional[str] = Query(None, description="文件编号过滤"),
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
) ->dict:
    """获取校验记录列表"""
    service = SopAiCheckService(db)
    records, total = await service.list_records(
        status=status,
        file_code=file_code,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )

    items = [
        {
            "id": r.id,
            "file_code": r.file_code,
            "file_name": r.file_name,
            "file_type": r.file_type,
            "check_type": r.check_type,
            "status": r.status,
            "result_summary": r.result_summary,
            "total_problems": r.total_problems,
            "risk_high": r.risk_high,
            "risk_medium": r.risk_medium,
            "risk_low": r.risk_low,
            "operator": r.operator,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
        }
        for r in records
    ]

    return ApiResponse(
        data={
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.get("/records/{id}", summary="获取校验记录详情")
async def get_record(
    id: str,
    db: AsyncSession = Depends(get_db),
) -> dict():
    """获取校验记录详情"""
    service = SopAiCheckService(db)
    record = await service.get_record_detail(id)

    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    return ApiResponse(data=record)


# ============ 问题处理接口 ============


@router.put("/problems/{problem_id}", summary="处理问题")
async def handle_problem(
    problem_id: str,
    request: schemas.ProblemHandleRequest,
    db: AsyncSession = Depends(get_db),
) -> dict():
    """处理问题"""
    service = SopAiCheckService(db)
    problem = await service.handle_problem(
        problem_id=problem_id,
        handle_status=request.handle_status,
        ignore_reason=request.ignore_reason,
        operator=request.operator,
    )

    if not problem:
        raise HTTPException(status_code=404, detail="问题不存在")

    return ApiResponse(
        data={
            "id": problem.id,
            "handle_status": problem.handle_status,
            "ignore_reason": problem.ignore_reason,
        }
    )


# ============ 定时任务接口 ============


@router.get("/jobs", summary="获取定时任务列表")
async def list_jobs(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """获取定时任务列表"""
    from app.modules.sop_ai.scheduler import get_sop_ai_scheduler

    scheduler = get_sop_ai_scheduler()
    jobs = scheduler.list_jobs()

    return ApiResponse(
        data=[
            {
                "job_id": job.job_id,
                "job_name": job.job_name,
                "cron_expression": job.cron_expression,
                "file_pattern": job.file_pattern,
                "enabled": job.enabled,
            }
            for job in jobs
        ]
    )


@router.post("/jobs", summary="创建定时任务")
async def create_job(
    request: schemas.ScheduledJobCreate,
    db: AsyncSession = Depends(get_db),
) -> dict():
    """创建定时任务"""
    from app.modules.sop_ai.scheduler import get_sop_ai_scheduler

    scheduler = get_sop_ai_scheduler()

    # 创建回调函数（实际需��绑定文件检查逻辑）
    async def job_callback():
        logger.info(f"执行定时任务: {request.job_id}")

    job = scheduler.add_job(
        job_id=request.job_id,
        job_name=request.job_name,
        cron_expression=request.cron_expression,
        file_pattern=request.file_pattern,
        callback=job_callback,
        enabled=request.enabled,
    )

    if not job:
        raise HTTPException(status_code=400, detail="创建任务失败")

    return ApiResponse(data=job.to_dict())


@router.delete("/jobs/{job_id}", summary="删除定时任务")
async def delete_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict():
    """删除定时任务"""
    from app.modules.sop_ai.scheduler import get_sop_ai_scheduler

    scheduler = get_sop_ai_scheduler()
    success = scheduler.remove_job(job_id)

    if not success:
        raise HTTPException(status_code=404, detail="任务不存在")

    return ApiResponse(data={"job_id": job_id, "deleted": True})


# ============ 导出接口 ============


@router.get("/export/{id}", summary="导出报告")
async def export_report(
    id: str,
    format: str = Query("excel", description="导出格式: excel/pdf"),
    include_problems: bool = Query(True, description="是否包含问题明细"),
    db: AsyncSession = Depends(get_db),
) -> dict():
    """导出校验报告"""
    service = SopAiCheckService(db)
    record = await service.get_record_detail(id)

    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    # TODO: 实现实际的文件导出逻辑
    return ApiResponse(
        data={
            "id": id,
            "format": format,
            "download_url": f"/api/v1/sop-ai/download/{id}.{format}",
        }
    )