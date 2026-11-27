"""批次查询与手工录入接口。"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import RequiredUser
from app.core.exceptions import AppException
from app.modules.quality.qc_report.schemas import (
    QcBatchApiResponse,
    QcBatchCreate,
    QcBatchImportApiResponse,
    QcBatchImportResult,
    QcBatchPageApiResponse,
)
from app.modules.quality.qc_report.service import batch as batch_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/products/{product_id}/batches", response_model=QcBatchPageApiResponse, summary="批次分页")
async def list_batches_api(
    product_id: uuid.UUID,
    current_user: RequiredUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    batch_no: str | None = Query(default=None, description="批号模糊搜索"),
    level: str | None = Query(default=None, description="判定等级"),
    db: AsyncSession = Depends(get_db),
) -> QcBatchPageApiResponse:
    data = await batch_service.list_batches(
        db, product_id, page=page, page_size=page_size, batch_no=batch_no, level=level
    )
    return QcBatchPageApiResponse(data=data)


@router.post("/products/{product_id}/batches", response_model=QcBatchApiResponse, summary="手工新增一批")
async def create_batch_api(
    product_id: uuid.UUID,
    data: QcBatchCreate,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> QcBatchApiResponse:
    row = await batch_service.create_batch(db, product_id, data, current_user.id, current_user.name)
    await db.commit()
    return QcBatchApiResponse(data=row)


@router.post(
    "/products/{product_id}/batches/import",
    response_model=QcBatchImportApiResponse,
    summary="从 Excel 批量新增检验批次",
)
async def import_batches_api(
    product_id: uuid.UUID,
    current_user: RequiredUser,
    file: UploadFile = File(..., description="检验结果表 xlsx"),
    db: AsyncSession = Depends(get_db),
) -> QcBatchImportApiResponse:
    """上传结果表批量新增批次。

    列按位置对应已有项目，列数或表头对不上直接拒绝；批号重复的行跳过。
    """
    if not (file.filename or "").lower().endswith(".xlsx"):
        raise AppException(status_code=400, message="请上传 .xlsx 格式的检验结果表")

    content = await file.read()
    if not content:
        raise AppException(status_code=400, message="文件是空的")
    if len(content) > 20 * 1024 * 1024:
        raise AppException(status_code=400, message="文件超过 20MB，请拆分后再上传")

    result = await batch_service.import_batches_from_xlsx(
        db,
        product_id,
        content,
        user_id=current_user.id,
        user_name=current_user.name,
    )
    await db.commit()
    return QcBatchImportApiResponse(data=QcBatchImportResult(**result.__dict__))


__all__ = ["router"]
