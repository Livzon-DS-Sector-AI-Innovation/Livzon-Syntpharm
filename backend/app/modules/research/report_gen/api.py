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
from app.modules.research.report_gen import review, service, versions
from app.modules.research.report_gen.schemas import (
    ReportGenDocumentVersionListData,
    ReportGenEditRequest,
    ReportGenEditResultData,
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
    ReportGenOpinionData,
    ReportGenOpinionDigestListData,
    ReportGenOpinionListData,
    ReportGenOpinionUpdateRequest,
    ReportGenOutlineData,
    ReportGenRenderData,
    ReportGenStepListData,
    ReportGenVersionRestoreRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/jobs",
    summary="提交 AI 生成文档任务",
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
    return DataResponse[ReportGenJobData](data=data, message="已开始生成，进度可以在列表里看")


@router.get(
    "/jobs",
    summary="AI 生成任务列表",
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
    summary="AI 生成任务详情",
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
    "/jobs/{job_id}/outline",
    summary="可写字段清单（审阅工作台）",
    response_model=DataResponse[ReportGenOutlineData],
)
async def get_report_gen_outline(
    job_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:report:read")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ReportGenOutlineData]:
    """母本可写位置与本次写入记录合并后的逐处清单。

    未写位置在 ``rd_report_gen_slots`` 里没有行，必须与母本位置取并集才列得出来；
    成品段落数一并返回，前端拿它自检预览 DOM 与段落下标是否对得上。
    """
    data = await review.build_review(db, job_id)
    return DataResponse[ReportGenOutlineData](data=data)


@router.get(
    "/jobs/{job_id}/steps",
    summary="生成过程记录（按序号增量拉取）",
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


@router.post(
    "/jobs/{job_id}/cancel",
    summary="停止生成",
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
    return DataResponse[ReportGenJobData](data=data, message="已发出停止请求，正在收尾")


@router.post(
    "/jobs/{job_id}/feedback",
    summary="对某一版文档提修改意见",
    response_model=DataResponse[ReportGenFeedbackData],
    status_code=201,
)
async def create_report_gen_feedback(
    job_id: UUID,
    payload: ReportGenFeedbackCreateRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:report:review")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ReportGenFeedbackData]:
    """意见只记录不立即执行：下次生成（含本页「重新生成」）会自动带上未落实的条目。"""
    data = await service.create_feedback(db, job_id, payload, current_user.id if current_user else None)
    return DataResponse[ReportGenFeedbackData](data=data, message="意见已记录，下次生成会参考")


@router.get(
    "/jobs/{job_id}/feedback",
    summary="某一版文档上提过的修改意见",
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
    summary="处理修改意见（不采纳 / 重新打开）",
    response_model=DataResponse[ReportGenFeedbackData],
)
async def update_report_gen_feedback(
    feedback_id: UUID,
    payload: ReportGenFeedbackUpdateRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:report:review")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ReportGenFeedbackData]:
    """标为不采纳后不再带入下一次生成；重新打开则恢复带入。"""
    data = await service.update_feedback(db, feedback_id, payload, current_user.id if current_user else None)
    return DataResponse[ReportGenFeedbackData](data=data, message="已更新")


@router.get(
    "/opinion-library",
    summary="意见库：跨报告归并后的历史意见",
    response_model=DataResponse[ReportGenOpinionListData],
)
async def list_report_gen_opinions(
    current_user: RequiredUser,
    status: str | None = Query(None, pattern="^(active|disabled)$", description="按状态过滤"),
    keyword: str | None = Query(None, max_length=100, description="按内容搜索"),
    limit: int = Query(200, ge=1, le=500),
    ctx: PermissionContext = Depends(require_permission("research:report:read")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ReportGenOpinionListData]:
    """每条意见都有被提出次数：次数高的要求会被优先收进生成前的写作要求。"""
    data = await service.list_opinions(db, status=status, keyword=keyword, limit=limit)
    return DataResponse[ReportGenOpinionListData](data=data)


@router.patch(
    "/opinion-library/{opinion_id}",
    summary="停用 / 恢复一条历史意见",
    response_model=DataResponse[ReportGenOpinionData],
)
async def update_report_gen_opinion(
    opinion_id: UUID,
    payload: ReportGenOpinionUpdateRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:report:review")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ReportGenOpinionData]:
    """停用后不再影响后续生成；同类意见再次被提出也不会自动恢复，需人工确认。"""
    data = await service.update_opinion(db, opinion_id, payload, current_user.id if current_user else None)
    return DataResponse[ReportGenOpinionData](data=data, message="已更新")


@router.get(
    "/opinion-library/digests",
    summary="历史意见汇总记录",
    response_model=DataResponse[ReportGenOpinionDigestListData],
)
async def list_report_gen_opinion_digests(
    current_user: RequiredUser,
    limit: int = Query(20, ge=1, le=100),
    ctx: PermissionContext = Depends(require_permission("research:report:read")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ReportGenOpinionDigestListData]:
    """每次生成前的汇总都留档：可回答「这一版按哪份写作要求写的」。"""
    data = await service.list_opinion_digests(db, limit=limit)
    return DataResponse[ReportGenOpinionDigestListData](data=data)


@router.get("/jobs/{job_id}/document", summary="下载生成的 Word 文档")
async def download_report_gen_document(
    job_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:report:read")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    name, data, mime = await service.document_payload(db, job_id)
    return _attachment(data, name, mime)


@router.get(
    "/jobs/{job_id}/versions",
    summary="文档版本列表（AI 初稿 / 重渲 / 人工上传）",
    response_model=DataResponse[ReportGenDocumentVersionListData],
)
async def list_report_gen_versions(
    job_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:report:read")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ReportGenDocumentVersionListData]:
    data = await versions.list_versions(db, job_id)
    return DataResponse[ReportGenDocumentVersionListData](data=data)


@router.get("/versions/{version_id}/document", summary="下载某个版本的 Word 文档")
async def download_report_gen_version_document(
    version_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:report:read")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    name, data, mime = await versions.version_document_payload(db, version_id)
    return _attachment(data, name, mime)


@router.post(
    "/jobs/{job_id}/edits",
    summary="在线编辑文档并保存为新版本",
    response_model=DataResponse[ReportGenEditResultData],
)
async def edit_report_gen_document(
    job_id: UUID,
    payload: ReportGenEditRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:report:update")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ReportGenEditResultData]:
    """逐条校验后原地改写当前版本 docx，落 ``manual_edit`` 新版本。

    校验未通过的操作只丢弃那一处并还原为母本原样，其余修改照常保存；返回逐条原因，
    前端按位置展示，不会因为一处写坏就丢掉整批。
    """
    data = await service.apply_job_edits(db, job_id, payload, current_user.id if current_user else None)
    if data.applied:
        message = f"已保存 {data.applied} 处修改"
        if data.removed:
            message += f"，{len(data.removed)} 处没有保存成功，已恢复原文"
    else:
        message = "这一批修改都没有保存成功，相关位置已恢复原文"
    return DataResponse[ReportGenEditResultData](data=data, message=message)


@router.post(
    "/jobs/{job_id}/versions/{version_id}/restore",
    summary="回滚到指定版本",
    response_model=DataResponse[ReportGenRenderData],
)
async def restore_report_gen_version(
    job_id: UUID,
    version_id: UUID,
    payload: ReportGenVersionRestoreRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:report:update")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ReportGenRenderData]:
    """不改写历史：把旧版文件再落一个新版本并置为当前，回滚本身也可再回滚。"""
    data = await service.restore_job_version(
        db,
        job_id,
        version_id,
        base_version_id=payload.base_version_id,
        user_id=current_user.id if current_user else None,
    )
    return DataResponse[ReportGenRenderData](data=data, message="已回滚")


@router.post(
    "/settings/test-model",
    summary="测试这个模型能不能用",
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
    summary="生成任务运行指标",
    response_model=DataResponse[ReportGenMetricsData],
)
async def get_report_gen_metrics(
    current_user: RequiredUser,
    days: int = Query(30, ge=1, le=90, description="统计最近多少天（只算已经结束的任务）"),
    ctx: PermissionContext = Depends(require_permission("platform:module-setting:read")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ReportGenMetricsData]:
    """配置页「Agent 运行情况」：只读聚合，返回成功率/平均轮次/平均耗时/缺口率与提示词指纹。"""
    data = await service.agent_metrics(db, days)
    return DataResponse[ReportGenMetricsData](data=data)


def _attachment(data: bytes, filename: str, mime: str) -> Response:
    """附件响应：中文文件名走 RFC 5987，避免乱码或响应头非法。"""
    quoted = quote(filename, safe="")
    fallback = "".join(ch if ch.isascii() and (ch.isalnum() or ch in "._-") else "_" for ch in filename)
    disposition = f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quoted}"
    return Response(content=data, media_type=mime, headers={"Content-Disposition": disposition})


__all__ = ["router"]
