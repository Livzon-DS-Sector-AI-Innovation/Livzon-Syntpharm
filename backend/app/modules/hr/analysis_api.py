"""HR turnover analysis API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory, get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.job_store import start_job
from app.modules.hr.analysis_service import TurnoverAnalysisService
from app.modules.hr.job_store import hr_job_store
from app.shared.schemas import AsyncJobAccepted, AsyncJobAcceptedResponse

router = APIRouter(prefix="/turnover-analysis", tags=["HR人员流动分析"])


def get_turnover_analysis_service(
    session: AsyncSession = Depends(get_db),
) -> TurnoverAnalysisService:
    return TurnoverAnalysisService(session)


@router.post("", response_model=AsyncJobAcceptedResponse, summary="提交人员流动分析任务")
async def submit(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("hr:turnover-analysis:read")),
) -> AsyncJobAcceptedResponse:
    """提交分析后台任务（LLM 报告生成 >5s，不再在 GET 请求里内联执行）。

    轮询 GET /api/v1/hr/jobs/{job_id}；`result.data` 即原响应体 `data`。
    后台任务在响应返回后执行，必须自建 session —— 请求级 session 此时已关闭。
    """

    async def _run(_job: str) -> dict[str, Any]:
        async with async_session_factory() as job_db:
            result = await TurnoverAnalysisService(job_db).analyze()
            return result.model_dump(mode="json")

    job_id = start_job(hr_job_store, "hr-turnover-analysis", _run)
    return AsyncJobAcceptedResponse(data=AsyncJobAccepted(job_id=job_id))
