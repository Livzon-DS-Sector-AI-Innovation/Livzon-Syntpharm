"""Registration dashboard API endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.response import DataResponse
from app.modules.registration.schemas.dashboard import DashboardSummaryResponse
from app.modules.registration.service.dashboard import get_dashboard_summary

router = APIRouter()


@router.get("/summary", summary="获取注册首页看板汇总数据")
async def dashboard_summary(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("registration:dashboard:read")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[DashboardSummaryResponse]:
    summary = await get_dashboard_summary(db)
    return DataResponse[DashboardSummaryResponse](data=summary.model_dump())
