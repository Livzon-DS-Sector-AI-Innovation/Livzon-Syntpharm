"""Registration dashboard API endpoint."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import success_response
from app.modules.registration.service.dashboard import get_dashboard_summary

router = APIRouter()


@router.get("/summary", summary="获取注册首页看板汇总数据")
async def dashboard_summary(
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    summary = await get_dashboard_summary(db)
    return success_response(data=summary.model_dump())
