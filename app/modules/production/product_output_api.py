"""Product output API routes."""

import csv
import io
import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.core.response import ApiResponse
from app.modules.production.product_output_models import WORKSHOP_CHOICES
from app.modules.production.product_output_schemas import (
    ProductOutputCreate,
    ProductOutputResponse,
    ProductOutputUpdate,
)
from app.modules.production.product_output_service import ProductOutputService

router = APIRouter()


@router.get("/product-output/workshops", summary="获取车间列表")
async def get_workshops():
    """获取所有车间列表"""
    return ApiResponse(data=WORKSHOP_CHOICES)


@router.get("/product-output", summary="获取产量记录列表")
async def get_product_outputs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    workshop: str | None = None,
    product_id: uuid.UUID | None = None,
    product_name: str | None = None,
    batch_no: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取产量记录列表"""
    service = ProductOutputService(db)
    skip = (page - 1) * page_size
    records, total = await service.get_list(
        skip=skip,
        limit=page_size,
        workshop=workshop,
        product_id=product_id,
        product_name=product_name,
        batch_no=batch_no,
        start_date=start_date,
        end_date=end_date,
    )
    return ApiResponse(
        data=[ProductOutputResponse.model_validate(r) for r in records],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/product-output/summary", summary="获取汇总统计")
async def get_summary(
    target_date: date | None = Query(None, description="查询日期"),
    month: str | None = Query(None, description="查询月份 YYYY-MM"),
    year: int | None = Query(None, description="查询年份"),
    product_id: uuid.UUID | None = Query(None, description="产品ID"),
    start_date: date | None = Query(None, description="开始日期"),
    end_date: date | None = Query(None, description="结束日期"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取每日/月/年汇总统计"""
    service = ProductOutputService(db)
    summary = await service.get_summary(
        target_date=target_date, month=month, year=year, product_id=product_id,
        start_date=start_date, end_date=end_date
    )
    return ApiResponse(data=summary)


@router.get("/product-output/batch-count", summary="获取批次统计")
async def get_batch_count(
    target_date: date | None = Query(None, description="查询日期"),
    month: str | None = Query(None, description="查询月份 YYYY-MM"),
    year: int | None = Query(None, description="查询年份"),
    product_id: uuid.UUID | None = Query(None, description="产品ID"),
    start_date: date | None = Query(None, description="开始日期"),
    end_date: date | None = Query(None, description="结束日期"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取批次统计"""
    service = ProductOutputService(db)
    batch_counts = await service.get_batch_count(
        target_date=target_date, month=month, year=year, product_id=product_id,
        start_date=start_date, end_date=end_date
    )
    return ApiResponse(data=batch_counts)


@router.get("/product-output/export", summary="导出产量记录")
async def export_product_outputs(
    workshop: str | None = None,
    product_id: uuid.UUID | None = None,
    product_name: str | None = None,
    batch_no: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """导出产量记录为 CSV"""
    service = ProductOutputService(db)
    records, _ = await service.get_list(
        skip=0,
        limit=10000,
        workshop=workshop,
        product_id=product_id,
        product_name=product_name,
        batch_no=batch_no,
        start_date=start_date,
        end_date=end_date,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
            "车间", "产品名称", "批号", "生产日期",
            "结束日期", "重量", "单位", "备注",
        ])

    for r in records:
        writer.writerow([
            r.workshop,
            r.product_name,
            r.batch_no,
            r.production_date.isoformat(),
            r.end_date.isoformat() if r.end_date else "",
            r.weight,
            r.unit,
            r.notes or "",
        ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=product_outputs.csv"},
    )


@router.get("/product-output/{record_id}", summary="获取产量记录详情")
async def get_product_output(
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取单条产量记录"""
    service = ProductOutputService(db)
    record = await service.get_by_id(record_id)
    if not record:
        return ApiResponse(code=404, message="记录不存在")
    return ApiResponse(data=ProductOutputResponse.model_validate(record))


@router.post("/product-output", summary="新建产量记录")
async def create_product_output(
    data: ProductOutputCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """新建产量记录"""
    service = ProductOutputService(db)
    record = await service.create(data)
    return ApiResponse(
        data=ProductOutputResponse.model_validate(record),
        message="创建成功",
    )


@router.put("/product-output/{record_id}", summary="更新产量记录")
async def update_product_output(
    record_id: uuid.UUID,
    data: ProductOutputUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """更新产量记录"""
    service = ProductOutputService(db)
    existing = await service.get_by_id(record_id)
    if not existing:
        return ApiResponse(code=404, message="记录不存在")
    record = await service.update(record_id, data)
    return ApiResponse(
        data=ProductOutputResponse.model_validate(record),
        message="更新成功",
    )


@router.delete("/product-output/{record_id}", summary="删除产量记录")
async def delete_product_output(
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """软删除产量记录"""
    service = ProductOutputService(db)
    success = await service.delete(record_id)
    if not success:
        return ApiResponse(code=404, message="记录不存在")
    return ApiResponse(message="删除成功")


@router.post("/product-output/import", summary="导入产量记录")
async def import_product_outputs(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """通过 CSV 文件批量导入产量记录

    CSV 列: 车间,产品名称,批号,生产日期,结束日期,重量,单位,备注
    """
    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    records_data = []
    for row in reader:
        workshop = row.get("车间", "").strip()
        product_name = row.get("产品名称", "").strip()
        batch_no = row.get("批号", "").strip()
        production_date_str = row.get("生产日期", "").strip()
        end_date_str = row.get("结束日期", "").strip()
        weight_str = row.get("重量", "0").strip()
        unit = row.get("单位", "kg").strip() or "kg"
        notes = row.get("备注", "").strip() or None

        if not all([workshop, product_name, batch_no, production_date_str]):
            continue

        try:
            weight = float(weight_str)
        except ValueError:
            continue

        record = {
            "workshop": workshop,
            "product_name": product_name,
            "batch_no": batch_no,
            "production_date": date.fromisoformat(production_date_str),
            "end_date": date.fromisoformat(end_date_str) if end_date_str else None,
            "weight": weight,
            "unit": unit,
            "notes": notes,
        }
        records_data.append(record)

    if not records_data:
        return ApiResponse(code=400, message="未找到有效数据，请检查 CSV 格式")

    service = ProductOutputService(db)
    count = await service.batch_import(records_data)
    return ApiResponse(data={"imported": count}, message=f"成功导入 {count} 条记录")
