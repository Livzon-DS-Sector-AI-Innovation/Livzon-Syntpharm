"""AI 报告生成的 HTTP 入口。

路由挂在 ``/api/v1/research/report-gen/*`` 下，与既有 ``/research/doc-gen``（交付物模板）
互不干扰。所有响应使用 ``DataResponse[具体模型]``，避免 ``response_model=dict``。
"""

from __future__ import annotations

import logging
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.response import DataResponse
from app.modules.research.report_gen import service, versions
from app.modules.research.report_gen.schemas import (
    ReportGenDocumentVersionListData,
    ReportGenExampleData,
    ReportGenExampleListData,
    ReportGenExamplePromoteData,
    ReportGenExampleUpdateRequest,
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
    ReportGenRenderData,
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


@router.get(
    "/jobs/{job_id}/slots",
    summary="填充项结果",
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
    summary="手动修改填充内容",
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
    return DataResponse[ReportGenSlotData](data=data, message="已保存，下次生成会沿用")


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


@router.post(
    "/feedback/{feedback_id}/promote",
    summary="把已落实的意见存成示例写法",
    response_model=DataResponse[ReportGenExamplePromoteData],
)
async def promote_report_gen_feedback(
    feedback_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:report:review")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ReportGenExamplePromoteData]:
    """把这次被采纳的写法收进示例库，下次同模板生成直接当 few-shot 参照。"""
    data = await service.promote_feedback(db, feedback_id, current_user.id if current_user else None)
    return DataResponse[ReportGenExamplePromoteData](data=data, message="已存成示例写法，以后生成会参考")


@router.get("/jobs/{job_id}/document", summary="下载生成的 Word 文档")
async def download_report_gen_document(
    job_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:report:read")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    name, data, mime = await service.document_payload(db, job_id)
    return _attachment(data, name, mime)


@router.get("/jobs/{job_id}/comparison", summary="下载填充项对照表")
async def download_report_gen_comparison(
    job_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:report:read")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    name, data, mime = await service.comparison_payload(db, job_id)
    return _attachment(data, name, mime)


@router.post(
    "/jobs/{job_id}/render",
    summary="按当前填充内容重新生成 Word（不重跑 AI）",
    response_model=DataResponse[ReportGenRenderData],
)
async def rerender_report_gen_document(
    job_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:report:update")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ReportGenRenderData]:
    """槽位改完后按当前内容重出 docx：纯本地按锚点回填，不调用大模型、秒级返回。"""
    data = await versions.render_from_slots(db, job_id, current_user.id if current_user else None)
    message = (
        "已按当前内容重新生成 Word"
        if data.synced_deliverable
        else "已按当前内容重新生成 Word；交付物附件未同步，可到交付物页重新上传"
    )
    return DataResponse[ReportGenRenderData](data=data, message=message)


@router.get(
    "/jobs/{job_id}/versions",
    summary="文档版本列表（AI 初稿 / 人工重渲 / 人工上传）",
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


@router.post(
    "/jobs/{job_id}/versions/upload",
    summary="上传人工修改后的 Word（兜底改稿）",
    response_model=DataResponse[ReportGenRenderData],
)
async def upload_report_gen_version(
    job_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:report:update")),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ReportGenRenderData]:
    """下载改完再传回来：落一个新版本并置为当前，AI 初稿仍然保留。"""
    data = await versions.upload_version(db, job_id, file, current_user.id if current_user else None)
    return DataResponse[ReportGenRenderData](data=data, message="已上传并设为当前版本")


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
    "/versions/{version_id}/activate",
    summary="把某个历史版本设为当前",
    response_model=DataResponse[ReportGenRenderData],
)
async def activate_report_gen_version(
    version_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:report:update")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ReportGenRenderData]:
    """改坏了可以退回任意一版；当前版决定交付物附件与预览内容。"""
    data = await versions.activate_version(db, version_id, current_user.id if current_user else None)
    return DataResponse[ReportGenRenderData](data=data, message="已切换到该版本")


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


@router.get(
    "/templates/{template_id}/structure-runs",
    summary="模板结构分析记录（识别到多少、人工又改了多少）",
    response_model=DataResponse[ReportGenStructureRunListData],
)
async def list_report_gen_structure_runs(
    template_id: UUID,
    current_user: RequiredUser,
    limit: int = Query(10, ge=1, le=50, description="看最近 N 次分析记录"),
    ctx: PermissionContext = Depends(require_permission("research:report:read")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ReportGenStructureRunListData]:
    """看每次解析选了多少槽位、以及人工随后后补/否掉了多少（只读）。"""
    data = await service.list_structure_runs(db, template_id, limit)
    return DataResponse[ReportGenStructureRunListData](data=data)


@router.get(
    "/templates/{template_id}/examples",
    summary="这个模板下已存的示例写法",
    response_model=DataResponse[ReportGenExampleListData],
)
async def list_report_gen_examples(
    template_id: UUID,
    current_user: RequiredUser,
    include_inactive: bool = Query(True, description="是否连已停用的示例一起返回"),
    limit: int = Query(200, ge=1, le=500),
    ctx: PermissionContext = Depends(require_permission("research:report:read")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ReportGenExampleListData]:
    """示例库管理用：这个模板下有哪些示例、各自从哪来、被引用过几次。"""
    data = await service.list_examples(db, template_id, include_inactive=include_inactive, limit=limit)
    return DataResponse[ReportGenExampleListData](data=data)


@router.patch(
    "/examples/{example_id}",
    summary="手动维护示例写法",
    response_model=DataResponse[ReportGenExampleData],
)
async def update_report_gen_example(
    example_id: UUID,
    payload: ReportGenExampleUpdateRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:report:update")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ReportGenExampleData]:
    """改写法 / 补依据 / 停用错例；停用后不再注入下一次生成。"""
    data = await service.update_example(db, example_id, payload, current_user.id if current_user else None)
    return DataResponse[ReportGenExampleData](data=data, message="已更新")


@router.delete(
    "/examples/{example_id}",
    summary="删除示例写法（可恢复）",
    response_model=DataResponse[ReportGenExampleData],
)
async def delete_report_gen_example(
    example_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:report:update")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ReportGenExampleData]:
    """彻底不再参与注入，但保留记录可追「以前为什么这么写」。"""
    data = await service.delete_example(db, example_id, current_user.id if current_user else None)
    return DataResponse[ReportGenExampleData](data=data, message="已删除")


def _attachment(data: bytes, filename: str, mime: str) -> Response:
    """附件响应：中文文件名走 RFC 5987，避免乱码或响应头非法。"""
    quoted = quote(filename, safe="")
    fallback = "".join(ch if ch.isascii() and (ch.isalnum() or ch in "._-") else "_" for ch in filename)
    disposition = f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quoted}"
    return Response(content=data, media_type=mime, headers={"Content-Disposition": disposition})


__all__ = ["router"]
