"""AI 报告生成的 HTTP 入口。

路由挂在 ``/api/v1/research/report-gen/*`` 下，与既有 ``/research/doc-gen``（交付物模板）
互不干扰。所有响应使用 ``DataResponse[具体模型]``，避免 ``response_model=dict``。
"""

from __future__ import annotations

import logging
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.response import DataResponse
from app.modules.research.report_gen import service
from app.modules.research.report_gen.schemas import (
    ReportGenFeedbackCreateRequest,
    ReportGenFeedbackData,
    ReportGenFeedbackListData,
    ReportGenFeedbackUpdateRequest,
    ReportGenJobCreateRequest,
    ReportGenJobData,
    ReportGenJobListData,
    ReportGenMetricsData,
    ReportGenModelTestData,
    ReportGenModelTestRequest,
    ReportGenSlotData,
    ReportGenSlotListData,
    ReportGenSlotUpdateRequest,
    ReportGenStepListData,
    ReportGenStructureRunListData,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/jobs",
    summary="提交 AI 报告生成任务",
    response_model=DataResponse[ReportGenJobData],
    status_code=201,
)
async def create_report_gen_job(
    payload: ReportGenJobCreateRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:report:create")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ReportGenJobData]:
    """建任务并立刻返回；真正的 Agent 执行在后台 worker 内进行，不阻塞本请求。"""
    data = await service.create_job(db, payload, current_user.id if current_user else None)
    return DataResponse[ReportGenJobData](data=data, message="已提交生成任务")


@router.get(
    "/jobs",
    summary="AI 报告生成任务列表",
    response_model=DataResponse[ReportGenJobListData],
)
async def list_report_gen_jobs(
    current_user: RequiredUser,
    project_id: UUID | None = Query(None, description="按项目过滤"),
    report_id: UUID | None = Query(None, description="按报告过滤"),
    limit: int = Query(100, ge=1, le=200),
    ctx: PermissionContext = Depends(require_permission("research:report:read")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ReportGenJobListData]:
    """列表页一次取回整项目的任务，避免逐报告请求。"""
    data = await service.list_jobs(db, project_id=project_id, report_id=report_id, limit=limit)
    return DataResponse[ReportGenJobListData](data=data)


@router.get(
    "/jobs/{job_id}",
    summary="AI 报告生成任务详情",
    response_model=DataResponse[ReportGenJobData],
)
async def get_report_gen_job(
    job_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:report:read")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ReportGenJobData]:
    data = await service.get_job(db, job_id)
    return DataResponse[ReportGenJobData](data=data)


@router.get(
    "/jobs/{job_id}/steps",
    summary="执行过程（按 seq 增量）",
    response_model=DataResponse[ReportGenStepListData],
)
async def list_report_gen_steps(
    job_id: UUID,
    current_user: RequiredUser,
    after_seq: int = Query(0, ge=0, description="只返回 seq 大于该值的步骤"),
    limit: int = Query(200, ge=1, le=500),
    ctx: PermissionContext = Depends(require_permission("research:report:read")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ReportGenStepListData]:
    data = await service.list_steps(db, job_id, after_seq=after_seq, limit=limit)
    return DataResponse[ReportGenStepListData](data=data)


@router.get(
    "/jobs/{job_id}/slots",
    summary="槽位填充结果",
    response_model=DataResponse[ReportGenSlotListData],
)
async def list_report_gen_slots(
    job_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:report:read")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ReportGenSlotListData]:
    data = await service.list_slots(db, job_id)
    return DataResponse[ReportGenSlotListData](data=data)


@router.put(
    "/jobs/{job_id}/slots/{slot_key}",
    summary="人工修正槽位",
    response_model=DataResponse[ReportGenSlotData],
)
async def update_report_gen_slot(
    job_id: UUID,
    slot_key: str,
    payload: ReportGenSlotUpdateRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:report:update")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ReportGenSlotData]:
    """只改结果区与对照表口径；成品 docx 不重渲染（按已确认的需求口径）。"""
    data = await service.update_slot(db, job_id, slot_key, payload, current_user.id if current_user else None)
    return DataResponse[ReportGenSlotData](data=data, message="已保存")


@router.post(
    "/jobs/{job_id}/cancel",
    summary="终止生成任务",
    response_model=DataResponse[ReportGenJobData],
)
async def cancel_report_gen_job(
    job_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:report:update")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ReportGenJobData]:
    """置取消标记：排队中直接落终态，执行中由 Agent 循环在下一轮自行退出。"""
    data = await service.cancel_job(db, job_id, current_user.id if current_user else None)
    return DataResponse[ReportGenJobData](data=data, message="已请求终止")


@router.post(
    "/jobs/{job_id}/feedback",
    summary="对某一版报告提修改意见",
    response_model=DataResponse[ReportGenFeedbackData],
    status_code=201,
)
async def create_report_gen_feedback(
    job_id: UUID,
    payload: ReportGenFeedbackCreateRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:report:update")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ReportGenFeedbackData]:
    """意见只记录不立即执行：下次生成（含本页「重新生成」）会自动带上未落实的条目。"""
    data = await service.create_feedback(db, job_id, payload, current_user.id if current_user else None)
    return DataResponse[ReportGenFeedbackData](data=data, message="已记录意见")


@router.get(
    "/jobs/{job_id}/feedback",
    summary="某一版报告上提过的修改意见",
    response_model=DataResponse[ReportGenFeedbackListData],
)
async def list_report_gen_feedback(
    job_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:report:read")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ReportGenFeedbackListData]:
    data = await service.list_feedback(db, job_id)
    return DataResponse[ReportGenFeedbackListData](data=data)


@router.patch(
    "/feedback/{feedback_id}",
    summary="处置修改意见（不采纳 / 重新打开）",
    response_model=DataResponse[ReportGenFeedbackData],
)
async def update_report_gen_feedback(
    feedback_id: UUID,
    payload: ReportGenFeedbackUpdateRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:report:update")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ReportGenFeedbackData]:
    """标为不采纳后不再带入下一次生成；重新打开则恢复带入。"""
    data = await service.update_feedback(db, feedback_id, payload, current_user.id if current_user else None)
    return DataResponse[ReportGenFeedbackData](data=data, message="已更新")


@router.get("/jobs/{job_id}/document", summary="下载生成的 Word 文档")
async def download_report_gen_document(
    job_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:report:read")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    name, data, mime = await service.document_payload(db, job_id)
    return _attachment(data, name, mime)


@router.get("/jobs/{job_id}/comparison", summary="下载槽位对照表")
async def download_report_gen_comparison(
    job_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:report:read")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    name, data, mime = await service.comparison_payload(db, job_id)
    return _attachment(data, name, mime)


@router.post(
    "/settings/test-model",
    summary="测试报告生成模型档位连通性",
    response_model=DataResponse[ReportGenModelTestData],
)
async def test_report_gen_model(
    payload: ReportGenModelTestRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("platform:module-setting:manage")),
) -> DataResponse[ReportGenModelTestData]:
    """只发一次极短对话验证该档位可用，不修改任何配置、不影响全局活跃模型。"""
    data = await service.test_model(payload.slot)
    return DataResponse[ReportGenModelTestData](data=data, message="测试完成")


@router.get(
    "/settings/metrics",
    summary="报告生成 Agent 运行指标",
    response_model=DataResponse[ReportGenMetricsData],
)
async def get_report_gen_metrics(
    current_user: RequiredUser,
    days: int = Query(30, ge=1, le=90, description="统计窗口天数（近 N 天已终态任务）"),
    ctx: PermissionContext = Depends(require_permission("platform:module-setting:read")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ReportGenMetricsData]:
    """配置页「Agent 运行情况」：只读聚合，返回成功率/平均轮次/平均耗时/缺口率与提示词指纹。"""
    data = await service.agent_metrics(db, days)
    return DataResponse[ReportGenMetricsData](data=data)


@router.get(
    "/templates/{template_id}/structure-runs",
    summary="母本解析留痕与漏选/多选统计",
    response_model=DataResponse[ReportGenStructureRunListData],
)
async def list_report_gen_structure_runs(
    template_id: UUID,
    current_user: RequiredUser,
    limit: int = Query(10, ge=1, le=50, description="最近 N 次解析"),
    ctx: PermissionContext = Depends(require_permission("research:report:read")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ReportGenStructureRunListData]:
    """看每次解析选了多少槽位、以及人工随后后补/否掉了多少（只读）。"""
    data = await service.list_structure_runs(db, template_id, limit)
    return DataResponse[ReportGenStructureRunListData](data=data)


def _attachment(data: bytes, filename: str, mime: str) -> Response:
    """附件响应：中文文件名走 RFC 5987，避免乱码或响应头非法。"""
    quoted = quote(filename, safe="")
    fallback = "".join(ch if ch.isascii() and (ch.isalnum() or ch in "._-") else "_" for ch in filename)
    disposition = f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quoted}"
    return Response(content=data, media_type=mime, headers={"Content-Disposition": disposition})


__all__ = ["router"]
