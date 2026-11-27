"""统计、需关注批号与导出接口。"""

from __future__ import annotations

import logging
import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import RequiredUser
from app.modules.quality.qc_report.schemas import (
    QcAttentionBatchListApiResponse,
    QcStatsApiResponse,
)
from app.modules.quality.qc_report.service import batch as batch_service
from app.modules.quality.qc_report.service.exporter import export_product_xlsx

logger = logging.getLogger(__name__)

router = APIRouter()

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/products/{product_id}/stats", response_model=QcStatsApiResponse, summary="五级统计")
async def get_stats_api(
    product_id: uuid.UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> QcStatsApiResponse:
    data = await batch_service.get_stats(db, product_id)
    return QcStatsApiResponse(data=data)


@router.get("/attention-batches", response_model=QcAttentionBatchListApiResponse, summary="全品种需关注批号")
async def attention_batches_api(
    current_user: RequiredUser,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> QcAttentionBatchListApiResponse:
    data = await batch_service.get_attention_batches(db, limit=limit)
    return QcAttentionBatchListApiResponse(data=data)


@router.get("/products/{product_id}/export", summary="导出当前筛选结果为 Excel")
async def export_api(
    product_id: uuid.UUID,
    current_user: RequiredUser,
    batch_no: str | None = Query(default=None),
    level: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> Response:
    content, file_name = await export_product_xlsx(db, product_id, batch_no=batch_no, level=level)
    # 文件下载需要直接控制响应头，属规范允许绕过 response_model 的场景
    return Response(
        content=content,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(file_name)}"},
    )


__all__ = ["router"]
