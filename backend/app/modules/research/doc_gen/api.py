"""文档生成 API：/api/v1/research/doc-gen/*

写操作全部要求登录（require_user）；文件下载直接返回 Response，
按 AGENTS.md 属于「需要控制 HTTP 响应」的例外场景。
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import RequiredUser
from app.core.exceptions import BadRequestException, NotFoundException
from app.core.response import build_response
from app.modules.research.doc_gen import conversation as conversation_mod
from app.modules.research.doc_gen import service, spec_source
from app.modules.research.doc_gen.schemas import (
    DocGenBatchUploadResponse,
    DocGenConfirmRequest,
    DocGenConversationData,
    DocGenConversationDataResponse,
    DocGenConversationResponse,
    DocGenExtractedInfoResponse,
    DocGenJobDataResponse,
    DocGenJobDetailResponse,
    DocGenJobListResponse,
    DocGenJobUpdateRequest,
    DocGenLimitsResponse,
    DocGenMessageResponse,
    DocGenOperationResponse,
    DocGenOutlineResponse,
    DocGenSendMessageRequest,
    DocGenSendMessageResponse,
    DocGenSlotProfileListResponse,
    DocGenSupersededList,
    DocGenSupersededResponse,
    DocGenTemplateFileResponse,
    DocGenTemplateListResponse,
    DocGenTemplateVersionListResponse,
    DocGenTemplateVersionRestoreResponse,
    DocGenUsableTemplateListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/limits", summary="文档生成规模限制", response_model=DocGenLimitsResponse)
async def read_limits(current_user: RequiredUser) -> Any:
    """前端提交前据此校验文件数量与大小。"""
    limits = await service.limits()
    return build_response(data=limits)


@router.post("/jobs", summary="新建报告（任务 + 资料一次提交）", response_model=DocGenJobDataResponse, status_code=201)
async def create_job(
    current_user: RequiredUser,
    deliverable_template_id: UUID = Form(..., description="交付物模板 ID（Word 母本 + 填充项配置）"),
    files: list[UploadFile] | None = File(default=None, description="资料文件（可多个，非必填）"),
    file_roles: list[str] = Form(default_factory=list, description="与 files 顺序对应的角色：material/literature"),
    report_id: UUID | None = Form(None, description="关联研发报告"),
    project_id: UUID | None = Form(None, description="关联研发项目"),
    doc_code: str = Form("", description="受控编码"),
    doc_version: str = Form("", description="版本号"),
    drug_name: str = Form("", description="品种名称（模板占位符替换用）"),
    supplement_text: str = Form("", description="人工补充说明（作为补充资料参与提取与成文）"),
    report_title: str = Form("", description="报告标题（自动创建 RdReport 时使用）"),
    report_type: str = Form("summary", description="报告类型（自动创建 RdReport 时使用）"),
    report_stage: str = Form("", description="关联阶段（自动创建 RdReport 时使用）"),
    report_summary: str = Form("", description="报告摘要（自动创建 RdReport 时使用）"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """「新建报告」一次提交：建任务 + 挂资料，不再分步向导。

    对话补全开启时任务停在草稿（由 ``/extract`` 触发提取）；关闭时直接排队，
    worker 一路跑完「提取 → 成文 → 渲染」。

    未传 ``report_id`` 时自动创建一条 ``RdReport`` 记录，使报告列表可见。
    """
    job = await service.create_job_from_template(
        db,
        deliverable_template_id,
        report_id,
        project_id,
        doc_code,
        doc_version,
        drug_name,
        list(files or []),
        list(file_roles),
        current_user.id if current_user else None,
        supplement_text,
        report_title=report_title,
        report_type=report_type,
        report_stage=report_stage or None,
        report_summary=report_summary or None,
    )
    await db.commit()
    logger.info("doc gen job submitted", extra={"job_id": str(job.id), "module_code": "research"})
    return build_response(data=await service.job_response(job), message="报告已创建")


@router.patch("/jobs/{job_id}", summary="修改报告基本信息与补充说明", response_model=DocGenJobDataResponse)
async def update_job(
    job_id: UUID,
    payload: DocGenJobUpdateRequest,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """修改受控编码/版本号/品种与人工补充说明。

    草稿、复核、失败、已完成状态均可修改元数据；仅运行中（parsing/extracting/composing/rendering）不允许。
    补充说明以 role=supplement 参与提取与成文，改完需重新提取才会生效；
    「重新生成」新建的任务自动沿用最新补充说明，作为使用者的长期背景知识。
    """
    from app.modules.research.doc_gen.models import RUNNING_STATUSES

    job = await service.get_job(db, job_id)
    if job.status in RUNNING_STATUSES:
        raise BadRequestException("任务正在运行中，请等待完成后再修改")
    meta = dict(job.meta or {})
    if payload.doc_code is not None:
        meta["doc_code"] = payload.doc_code.strip()
    if payload.doc_version is not None:
        meta["doc_version"] = payload.doc_version.strip()
    if payload.drug_name is not None:
        meta["drug_name"] = payload.drug_name.strip()
    job.meta = meta
    if payload.supplement_text is not None:
        job.supplement_text = payload.supplement_text.strip() or None
    if payload.template_code is not None:
        # 支持 UUID 格式：查找对应的交付物模板并获取 template_code
        template_value = payload.template_code.strip()
        try:
            # 尝试解析为 UUID
            template_uuid = UUID(template_value)
            from app.modules.research.models import RdDeliverableTemplate
            template = await db.get(RdDeliverableTemplate, template_uuid)
            if template and template.template_code:
                job.template_code = template.template_code
                meta["deliverable_template_id"] = str(template_uuid)
            else:
                raise BadRequestException("交付物模板不存在或未配置填充项")
        except ValueError:
            # 不是 UUID，直接作为 template_code 使用
            job.template_code = template_value
    job.meta = meta
    await db.flush()
    return build_response(data=await service.job_response(job), message="已保存")


@router.post("/jobs/{job_id}/files", summary="追加资料文件", response_model=DocGenJobDetailResponse)
async def upload_job_files(
    job_id: UUID,
    current_user: RequiredUser,
    files: list[UploadFile] = File(..., description="资料文件"),
    file_roles: list[str] = Form(default_factory=list, description="与 files 顺序对应的角色"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """逐个上传入口：向尚未进入提取流程的任务追加资料。"""
    detail = await service.append_input_files(db, job_id, list(files), list(file_roles))
    await db.commit()
    return build_response(data=detail, message="资料已追加")


@router.delete(
    "/jobs/{job_id}/input-files/{file_row_id}", summary="删除资料文件", response_model=DocGenJobDetailResponse
)
async def delete_job_input_file(
    job_id: UUID,
    file_row_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """从任务移除一份资料（软删除），返回最新任务详情。"""
    detail = await service.remove_input_file(db, job_id, file_row_id)
    await db.commit()
    return build_response(data=detail, message="资料已删除")


@router.get("/jobs/{job_id}/input-files/{file_id}/download", summary="下载资料文件")
async def download_input_file(
    job_id: UUID,
    file_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """下载任务的一份资料文件原件，供前端预览。"""
    data, name, mime = await service.download_input_file(db, job_id, file_id)
    return _attachment(data, name, mime)


@router.get("/jobs", summary="按项目查询生成任务", response_model=DocGenJobListResponse)
async def read_jobs_for_project(
    current_user: RequiredUser,
    project_id: UUID = Query(..., description="研发项目ID"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """一次取回项目下所有生成任务，供报告列表显示最新状态（避免逐报告请求）。"""
    jobs = await service.list_jobs_for_project(db, project_id)
    return build_response(data=jobs)


@router.get("/jobs/{job_id}", summary="查询生成任务", response_model=DocGenJobDetailResponse)
async def read_job(
    job_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """任务状态与进度（前端轮询此端点）。"""
    detail = await service.job_detail(db, job_id)
    return build_response(data=detail)


@router.get("/jobs/{job_id}/slots", summary="查询逐项填充结果", response_model=DocGenJobDetailResponse)
async def read_job_slots(
    job_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """逐项填充结果与依据。"""
    detail = await service.job_detail(db, job_id)
    return build_response(data=detail)


@router.get("/jobs/{job_id}/extracted-info", summary="查询结构化提取信息", response_model=DocGenExtractedInfoResponse)
async def read_extracted_info(
    job_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """仅返回已提取的结构化信息（槽位值），用于前端预览与编辑。"""
    detail = await service.job_detail(db, job_id)
    # 只返回 slots 部分，不含 job 元数据
    return build_response(data={"slots": detail.slots})


@router.get("/jobs/{job_id}/outline", summary="查询任务大纲", response_model=DocGenOutlineResponse)
async def read_job_outline(
    job_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """动态章节大纲：复核界面的结构树数据源（含触发依据与预设标题池）。"""
    return build_response(data=await service.job_outline(db, job_id))


@router.get("/reports/{report_id}/jobs", summary="按报告查询生成任务", response_model=DocGenJobListResponse)
async def read_jobs_for_report(
    report_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """某研发报告下的历次生成任务。"""
    jobs = await service.list_jobs_for_report(db, report_id)
    return build_response(data=jobs)


@router.post("/jobs/{job_id}/cancel", summary="取消生成任务", response_model=DocGenJobDataResponse)
async def cancel_job(
    job_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """取消排队中或进行中的任务。"""
    job = await service.cancel_job(db, job_id)
    await db.commit()
    return build_response(data=await service.job_response(job), message="已取消")


@router.post("/jobs/{job_id}/confirm", summary="确认提取结果并生成", response_model=DocGenJobDataResponse)
async def confirm_job(
    job_id: UUID,
    payload: DocGenConfirmRequest,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """人工确认（可含修正与大纲调整）后交回 worker 渲染；提取结果已落库，不重复调用模型。"""
    job = await service.confirm_job(db, job_id, payload.slots, payload.outline)
    await db.commit()
    return build_response(data=await service.job_response(job), message="已确认，开始生成")


# ---------------------------------------------------------------------------
# 对话补全（初抽完成后自动开始；只补值，渲染仍走 confirm 链路）
# ---------------------------------------------------------------------------


async def _conversation_data(db: AsyncSession, conversation: Any) -> DocGenConversationData:
    """会话 ORM + 消息 → 响应数据。"""
    messages = await conversation_mod.list_messages(db, conversation.id)
    return DocGenConversationData(
        conversation=DocGenConversationResponse.model_validate(conversation),
        messages=[DocGenMessageResponse.model_validate(m) for m in messages],
    )


def _ensure_conversation_editable(job: Any) -> None:
    """对话写入/完成/跳过的任务状态守卫：仅在「等待人工确认」阶段允许操作会话。

    生成中/已生成后输入进入锁定，防止用户补值与成文/渲染并发写槽位。
    """
    if job.status != "awaiting_review":
        raise BadRequestException("任务当前状态不支持对话补全，请到确认页逐项检查")


@router.get("/jobs/{job_id}/conversation", summary="查询对话会话", response_model=DocGenConversationDataResponse)
async def read_conversation(
    job_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """会话与全部消息；任务尚未创建会话（未完成初抽）时返回空 data。"""
    conversation = await conversation_mod.get_conversation(db, job_id)
    if conversation is None:
        return build_response(data=None)
    return build_response(data=await _conversation_data(db, conversation))


@router.post("/jobs/{job_id}/messages", summary="发送对话消息", response_model=DocGenSendMessageResponse)
async def send_message(
    job_id: UUID,
    payload: DocGenSendMessageRequest,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """用户补充信息：模型抽值 → 校验 → 写入槽位结果，返回更新后的会话与全部消息。"""
    job = await service.get_job(db, job_id)
    _ensure_conversation_editable(job)
    try:
        spec = await spec_source.resolve_for_job(db, job)
    except KeyError as exc:
        raise BadRequestException("该任务的填充项配置已失效，无法进行对话补全") from exc
    try:
        await conversation_mod.send_user_message(db, job_id, spec, payload.content)
    except conversation_mod.ConversationError as exc:
        raise BadRequestException(str(exc)) from exc
    await db.commit()
    # 返回全量消息：前端据此整体刷新，用户自己那条也要在列表里，不能只回助手回复
    conversation = await conversation_mod.get_conversation(db, job_id)
    return build_response(data=await _conversation_data(db, conversation), message="已回复")


@router.post(
    "/jobs/{job_id}/conversation/complete", summary="完成对话", response_model=DocGenConversationDataResponse
)
async def complete_conversation(
    job_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """结束对话（保留已补值），后续到确认页逐项检查并确认生成。"""
    job = await service.get_job(db, job_id)
    _ensure_conversation_editable(job)
    try:
        conversation = await conversation_mod.complete_conversation(db, job_id)
    except conversation_mod.ConversationError as exc:
        raise BadRequestException(str(exc)) from exc
    await db.commit()
    return build_response(data=await _conversation_data(db, conversation), message="对话已完成")


@router.post("/jobs/{job_id}/conversation/skip", summary="跳过对话", response_model=DocGenConversationDataResponse)
async def skip_conversation(
    job_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """跳过对话直接前往确认页（与完成等效，语义不同）。"""
    job = await service.get_job(db, job_id)
    _ensure_conversation_editable(job)
    try:
        conversation = await conversation_mod.skip_conversation(db, job_id)
    except conversation_mod.ConversationError as exc:
        raise BadRequestException(str(exc)) from exc
    await db.commit()
    return build_response(data=await _conversation_data(db, conversation), message="已跳过对话")


@router.get("/slot-profiles", summary="内置填充项配置清单", response_model=DocGenSlotProfileListResponse)
async def read_slot_profiles(current_user: RequiredUser) -> Any:
    """上传 Word 模板原件时，用它选择这份模板对应哪套填充项配置。"""
    return build_response(data=await service.slot_profiles())


@router.get("/templates", summary="可用于 AI 生成的模板", response_model=DocGenUsableTemplateListResponse)
async def read_usable_templates(
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """只返回「有 Word 模板原件 + 填充项配置有效」的交付物模板，避免选了必然失败。"""
    return build_response(data=await service.usable_templates(db))


@router.get("/builtin-templates", summary="内置模板定义（排错用）", response_model=DocGenTemplateListResponse)
async def read_builtin_templates(current_user: RequiredUser) -> Any:
    """代码内置的填充项配置视图，供排查与对账。"""
    return build_response(data=service.template_summaries())


@router.post(
    "/deliverable-templates/batch-upload",
    summary="批量上传 Word 模板",
    response_model=DocGenBatchUploadResponse,
    status_code=201,
)
async def batch_upload_templates(
    current_user: RequiredUser,
    files: list[UploadFile] = File(..., description="Word 模板文件（docx/dotx/doc）"),
    stage: str = Form("", description="所属阶段，留空则由系统按识别结果填"),
    deliverable_type: str = Form("", description="交付物类型，留空则用识别出的模板 code"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """每个文件建一条模板记录；同名文件转为该模板的新版本，格式不符的跳过并说明原因。"""
    result = await service.batch_upload_templates(
        db, files, stage, deliverable_type, current_user.id if current_user else None
    )
    await db.commit()
    message = f"成功上传 {len(result['created'])} 个模板"
    if result["versioned"]:
        message += f"，新增 {len(result['versioned'])} 个版本"
    if result["skipped"]:
        message += f"，跳过 {len(result['skipped'])} 个"
    return build_response(data=result, message=message)


@router.post(
    "/deliverable-templates/{template_id}/upload",
    summary="上传 Word 模板原件",
    response_model=DocGenTemplateFileResponse,
)
async def upload_template_file(
    template_id: UUID,
    current_user: RequiredUser,
    file: UploadFile = File(..., description="Word 模板文件（docx/dotx/doc）"),
    change_note: str = Form("", description="版本说明（变更备注，可空）"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """给已存在的交付物模板挂载/替换 Word 模板原件，并自动留档为一个新版本。

    上传不会自动启用模板：母本与槽位经核对后由用户手动开启，避免半成品被 AI 生成选中。
    """
    from app.modules.research.models import RdDeliverableTemplate

    template = await db.get(RdDeliverableTemplate, template_id)
    if template is None or template.is_deleted:
        raise NotFoundException("模板不存在")
    data = await file.read()
    await service.attach_template_file(
        db,
        template,
        (file.filename or "").strip(),
        data,
        current_user.id if current_user else None,
        change_note=change_note,
    )
    await db.commit()
    return build_response(
        data={"id": str(template.id), "file_name": template.file_name, "file_ext": template.file_ext},
        message="上传成功，已生成新版本",
    )


@router.get("/deliverable-templates/{template_id}/download", summary="下载 Word 模板原件")
async def download_template_file(
    template_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """下载模板的 Word 原件（保留原始扩展名）。"""
    data, name, mime = await service.template_download_payload(db, template_id)
    return _attachment(data, name, mime)


@router.get(
    "/deliverable-templates/{template_id}/versions",
    summary="交付物模板版本历史",
    response_model=DocGenTemplateVersionListResponse,
)
async def list_template_versions(
    template_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """模板的留档版本（新版本在前），据此可预览、下载或回滚任一个历史版本。"""
    return build_response(data=await service.list_template_versions(db, template_id))


@router.get(
    "/deliverable-templates/{template_id}/versions/{version_id}/download",
    summary="下载历史版本 Word 原件",
)
async def download_template_version(
    template_id: UUID,
    version_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """下载指定历史版本的 Word 原件（文件名带版本号，避免多次下载互相覆盖）。"""
    data, name, mime = await service.template_version_download_payload(db, template_id, version_id)
    return _attachment(data, name, mime)


@router.post(
    "/deliverable-templates/{template_id}/versions/{version_id}/restore",
    summary="回滚到指定历史版本",
    response_model=DocGenTemplateVersionRestoreResponse,
)
async def restore_template_version(
    template_id: UUID,
    version_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """回滚 = 以该版本内容新建一个版本并设为当前：版本号单调递增，历史不可改写。

    不就地改写历史版本（类似 git revert），因此审计链完整，且可再次回滚回来。
    """
    result = await service.restore_template_version(
        db, template_id, version_id, current_user.id if current_user else None
    )
    await db.commit()
    return build_response(
        data=result,
        message=f"已回滚到 v{result['from_version_no']}（生成 v{result['version_no']}）",
    )


@router.delete(
    "/deliverable-templates/{template_id}/versions/{version_id}",
    summary="删除历史版本",
    response_model=DocGenOperationResponse,
)
async def delete_template_version(
    template_id: UUID,
    version_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """软删一个历史版本；当前生效版本与唯一版本不允许删除。"""
    await service.delete_template_version(db, template_id, version_id, current_user.id if current_user else None)
    await db.commit()
    return build_response(message="已删除该版本")


@router.post("/jobs/{job_id}/extract", summary="AI 提取信息", response_model=DocGenJobDataResponse)
async def extract_job(
    job_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """两步流程第一步：排队提取资料信息，完成后停在「等待确认」。

    提取中/生成中拒绝重入；复核或失败后可再次调用重新提取（会清空上一轮提取
    结果与对话中的人工修改，属明确操作）。
    """
    job = await service.extract_inputs(db, job_id)
    await db.commit()
    return build_response(data=await service.job_response(job), message="已排队，开始 AI 提取信息")


@router.post("/jobs/{job_id}/generate", summary="AI 报告生成（确认后成文）", response_model=DocGenJobDataResponse)
async def generate_job(
    job_id: UUID,
    payload: DocGenConfirmRequest,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """两步流程第二步：确认提取信息，交回 worker 成文 + 渲染。

    成文由写作模型把确认值改写成连续叙述；含未确认数字或超字数上限的
    输出整槽回退人工文本。带修正值时即「人工确认后重新生成正文」。
    """
    job = await service.confirm_job(db, job_id, payload.slots, payload.outline)
    await db.commit()
    return build_response(data=await service.job_response(job), message="已确认，开始 AI 报告生成")


@router.post(
    "/jobs/{job_id}/regenerate",
    summary="重新生成（新任务，沿用资料与确认值）",
    response_model=DocGenJobDataResponse,
    status_code=201,
)
async def regenerate_job(
    job_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """在复核/失败/已完成任务上点「重新生成」：新建任务挂在本任务之下。

    资料、补充说明与已确认填充值全部沿用到新任务（旧产物与审计链完整保留）；
    新任务排队后直接提取 → 成文 → 渲染。旧报告标记为「已被新一轮取代」。
    """
    job = await service.regenerate_job(db, job_id, current_user.id if current_user else None)
    await db.commit()
    return build_response(data=await service.job_response(job), message="已创建新一轮生成")


@router.get(
    "/jobs/{job_id}/superseded", summary="查询被本轮取代的历史任务", response_model=DocGenSupersededResponse
)
async def read_superseded(
    job_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """重新生成链上的历史节点（上一轮及其祖先、兄弟分支），供详情页展示失效徽标。"""
    jobs = await service.list_superseded(db, job_id)
    return build_response(data=DocGenSupersededList(items=jobs, total=len(jobs)))


@router.get("/jobs/{job_id}/document", summary="下载文档初版")
async def download_document(
    job_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """下载渲染出的 docx。"""
    data, name, mime = await service.download_artifact(db, job_id, "document")
    return _attachment(data, name, mime)


@router.get("/jobs/{job_id}/report", summary="下载生成说明")
async def download_report(
    job_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """下载记录取值来源与待人工清单的生成说明。"""
    data, name, mime = await service.download_artifact(db, job_id, "report")
    return _attachment(data, name, mime)


def _attachment(data: bytes, filename: str, mime: str) -> Response:
    """附件响应：中文文件名走 RFC 5987，避免乱码或响应头非法。"""
    quoted = quote(filename, safe="")
    fallback = "".join(ch if ch.isascii() and (ch.isalnum() or ch in "._-") else "_" for ch in filename)
    disposition = f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quoted}"
    return Response(content=data, media_type=mime, headers={"Content-Disposition": disposition})
