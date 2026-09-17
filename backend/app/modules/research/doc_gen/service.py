"""文档生成服务层：任务创建校验、查询、下载与取消。"""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from html import unescape
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.modules.research import models as rd_models
from app.modules.research.doc_gen import cancellation, parsing, spec_source, status, store
from app.modules.research.doc_gen import repository as repo
from app.modules.research.doc_gen.models import (
    EDITABLE_INPUT_STATUSES,
    RUNNING_STATUSES,
    DocGenInputFile,
    DocGenJob,
    DocGenSlotValue,
)
from app.modules.research.doc_gen.runtime_config import load_runtime_config
from app.modules.research.doc_gen.schemas import (
    DocGenInputFileResponse,
    DocGenJobDetail,
    DocGenJobResponse,
    DocGenLimits,
    DocGenSectionAdjust,
    DocGenSectionResponse,
    DocGenSlotValueResponse,
    DocGenTemplateSummary,
)
from app.modules.research.doc_gen.sections import recompose_title
from app.modules.research.doc_gen.spec_draft import draft_spec_from_bytes
from app.modules.research.doc_gen.template_spec import SECTION_INSTANCE_SEP, TemplateSpec, split_slot_key

logger = logging.getLogger(__name__)

# 上传白名单直接由解析层的类型注册表派生（单一真相来源）：
# 解析层新增一种文档类型，这里和前端 accept 会自动跟上，不会出现「能传不能解析」。
ALLOWED_EXTENSIONS: set[str] = set(parsing.supported_extensions())
MAX_DOCX_BYTES = 20 * 1024 * 1024


@dataclass
class NewJobRequest:
    """创建任务的入参（由 multipart 表单组装）。"""

    template_code: str
    report_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    doc_code: str = ""
    doc_version: str = ""
    drug_name: str = ""
    roles: list[str] = field(default_factory=list)
    supplement_text: str = ""


def template_summaries() -> list[DocGenTemplateSummary]:
    """内置模板清单。"""
    from app.modules.research.doc_gen.templates import list_templates

    summaries: list[DocGenTemplateSummary] = []
    for spec in list_templates():
        summaries.append(
            DocGenTemplateSummary(
                code=spec.code,
                name=spec.name,
                version=spec.version,
                stage=spec.stage,
                description=spec.description,
                slot_count=len(spec.slots),
                required_count=sum(1 for s in spec.slots if s.required),
                unfilled_notes=list(spec.unfilled_notes),
            )
        )
    return summaries


async def limits() -> DocGenLimits:
    """规模限制（前端提交前校验用）。"""
    config = await load_runtime_config()
    return DocGenLimits(
        max_files=config.max_files,
        max_total_pages=config.max_total_pages,
        max_file_mb=config.max_file_mb,
        max_total_mb=config.max_total_mb,
        allowed_extensions=sorted(ALLOWED_EXTENSIONS),
        supported_formats=parsing.supported_formats(),
    )


def _validate_extensions(uploads: list[UploadFile]) -> None:
    """提交前统一校验类型：先校验再落盘，避免失败时留下无主文件。"""
    supported = "、".join(sorted(ALLOWED_EXTENSIONS))
    for upload in uploads:
        filename = (upload.filename or "").strip()
        if _extension(filename) not in ALLOWED_EXTENSIONS:
            raise BadRequestException(f"不支持的文件类型：{filename or '未命名文件'}（支持 {supported}）")


def _extension(filename: str) -> str:
    lowered = filename.lower()
    dot = lowered.rfind(".")
    return lowered[dot:] if dot >= 0 else ""



async def create_job_from_template(
    session: AsyncSession,
    deliverable_template_id: uuid.UUID,
    report_id: uuid.UUID | None,
    project_id: uuid.UUID | None,
    doc_code: str,
    doc_version: str,
    drug_name: str,
    uploads: list[UploadFile],
    file_roles: list[str] | None = None,
    user_id: uuid.UUID | None = None,
    supplement_text: str = "",
    *,
    report_title: str = "",
    report_type: str = "summary",
    report_stage: str | None = None,
    report_summary: str | None = None,
) -> DocGenJob:
    """从交付物模板创建生成任务（「新建报告」一次提交：任务 + 资料 + 补充说明）。

    对话补全开启时任务以 ``draft`` 落库（等用户点「AI 提取信息」才排队）；
    关闭时直接 ``pending``，worker 一路跑完「提取 → 成文 → 渲染」。

    未传 ``report_id`` 时自动创建一条 ``RdReport`` 记录，使报告列表可见。
    """
    from app.modules.research.models import RdDeliverableTemplate, RdProject, RdReport

    # 获取交付物模板
    template = await session.get(RdDeliverableTemplate, deliverable_template_id)
    if template is None or template.is_deleted:
        raise NotFoundException("交付物模板不存在")
    if not template.template_code:
        raise BadRequestException("该模板未关联填充项配置，无法用于 AI 生成")

    # 槽位定义：代码内置优先，其次母本上传时自动识别并落库的配置
    try:
        spec = await spec_source.resolve_for_template(session, template)
    except KeyError as exc:
        raise BadRequestException("该模板的填充项配置缺失，请重新上传 Word 母本以自动识别") from exc

    # 校验报告/项目
    report: Any = None
    if report_id is not None:
        report = await session.get(RdReport, report_id)
        if report is None or report.is_deleted:
            raise NotFoundException("研发报告不存在")
        project_id = project_id or report.project_id
    elif project_id is not None:
        project = await session.get(RdProject, project_id)
        if project is None or project.is_deleted:
            raise NotFoundException("研发项目不存在")

    # 校验文件数量上限（允许空列表，用户可稍后上传）
    config = await load_runtime_config()
    if len(uploads) > config.max_files:
        raise BadRequestException(f"资料文件最多 {config.max_files} 个，当前 {len(uploads)} 个")

    _validate_extensions(uploads)

    # 未关联已有报告时，自动创建一条 RdReport 使报告列表可见
    if report_id is None and project_id is not None:
        title = report_title.strip() or doc_code.strip() or drug_name.strip() or "新建报告"
        report = RdReport(
            project_id=project_id,
            title=title,
            report_type=report_type.strip() or "summary",
            stage=report_stage,
            version=doc_version.strip() or "v1.0",
            summary=report_summary,
            status="draft",
            author_id=user_id,
        )
        session.add(report)
        await session.flush()
        report_id = report.id
        logger.info(
            "auto-created RdReport for doc gen job",
            extra={"report_id": str(report_id), "template_id": str(deliverable_template_id)},
        )

    # 冻结本次生成所用的母本版本：产物据此可追溯「是哪一版模板渲染的」，
    # 也能反查「某版母本被哪些任务用过」。模板尚未留档版本时容错为空。
    current_version_row = await _current_template_version(session, template.id)

    # 创建任务：对话模式下先落「草稿」，由「AI 提取信息」按钮触发排队
    job = DocGenJob(
        report_id=report_id,
        project_id=project_id,
        template_code=spec.code,
        template_version=spec.version,
        deliverable_template_version_id=current_version_row.id if current_version_row is not None else None,
        status="draft" if config.chat_enabled else "pending",
        step="草稿" if config.chat_enabled else "排队中",
        progress=0,
        supplement_text=supplement_text.strip() or None,
        meta={
            "doc_code": doc_code.strip(),
            "doc_version": doc_version.strip(),
            "drug_name": drug_name.strip(),
            "deliverable_template_id": str(deliverable_template_id),
            "project_name": await _project_name(session, project_id),
        },
        created_by=user_id,
    )
    await repo.create_job(session, job)

    # 保存文件（角色标记与文件同序）
    files = await _store_uploads(session, job, uploads, list(file_roles or []), config)
    # 允许空文件列表创建任务（用户可稍后上传）
    # 只有当用户提供了文件但全部无效时才报错
    if uploads and not files:
        raise BadRequestException("资料文件均为空或重复，未能建立任务")

    # 人工填写的报告内容作为额外资料源接入生成上下文
    await _store_report_context(session, job, report)

    logger.info(
        "doc gen job created from deliverable template",
        extra={"job_id": str(job.id), "template_id": str(deliverable_template_id), "files": len(files)},
    )
    return job


async def create_job(
    session: AsyncSession, request: NewJobRequest, uploads: list[UploadFile], user_id: uuid.UUID | None
) -> DocGenJob:
    """创建生成任务并保存资料。"""
    config = await load_runtime_config()
    try:
        spec = await spec_source.resolve_by_code(session, request.template_code)
    except KeyError as exc:
        raise BadRequestException(f"模板不存在：{request.template_code}") from exc
    if not uploads:
        raise BadRequestException("请至少上传一份资料文件")
    if len(uploads) > config.max_files:
        raise BadRequestException(f"资料文件最多 {config.max_files} 个，当前 {len(uploads)} 个")
    _validate_extensions(uploads)

    project_id = request.project_id
    report: Any = None
    if request.report_id is not None:
        report = await session.get(rd_models.RdReport, request.report_id)
        if report is None or report.is_deleted:
            raise NotFoundException("研发报告不存在")
        project_id = project_id or report.project_id
    elif project_id is not None:
        project = await session.get(rd_models.RdProject, project_id)
        if project is None or project.is_deleted:
            raise NotFoundException("研发项目不存在")

    job = DocGenJob(
        report_id=request.report_id,
        project_id=project_id,
        template_code=spec.code,
        template_version=spec.version,
        status="draft" if config.chat_enabled else "pending",
        step="草稿" if config.chat_enabled else "排队中",
        progress=0,
        supplement_text=request.supplement_text.strip() or None,
        meta={
            "doc_code": request.doc_code.strip(),
            "doc_version": request.doc_version.strip(),
            "drug_name": request.drug_name.strip(),
            "project_name": await _project_name(session, project_id),
        },
        created_by=user_id,
    )
    await repo.create_job(session, job)
    files = await _store_uploads(session, job, uploads, request.roles, config)
    # 允许空文件列表创建任务（用户可稍后上传）
    if uploads and not files:
        raise BadRequestException("资料文件均为空或重复，未能建立任务")
    await _store_report_context(session, job, report)
    logger.info(
        "doc gen job created",
        extra={"job_id": str(job.id), "template": spec.code, "files": len(files), "module_code": "research"},
    )
    return job


async def _project_name(session: AsyncSession, project_id: uuid.UUID | None) -> str:
    """取项目名用于元数据回填。"""
    if project_id is None:
        return ""
    project = await session.get(rd_models.RdProject, project_id)
    return project.name if project is not None else ""


async def _store_uploads(
    session: AsyncSession, job: DocGenJob, uploads: list[UploadFile], roles: list[str], config: Any
) -> list[DocGenInputFile]:
    """保存资料并落库；同一任务内重复文件只保留一份。"""
    records: list[DocGenInputFile] = []
    seen: set[str] = set()
    max_bytes = config.max_file_mb * 1024 * 1024
    max_total_bytes = config.max_total_mb * 1024 * 1024
    accepted_bytes = 0
    for index, upload in enumerate(uploads):
        filename = (upload.filename or "").strip() or f"未命名文件{index + 1}"
        data = await upload.read()
        if not data:
            continue
        if len(data) > max_bytes:
            raise BadRequestException(f"文件 {filename} 超过单文件上限 {config.max_file_mb}MB")
        digest = hashlib.sha256(data).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        # 合计校验放在落盘之前：先写对象存储再抛错会留下无主文件
        accepted_bytes += len(data)
        if accepted_bytes > max_total_bytes:
            raise BadRequestException(
                f"资料文件合计 {accepted_bytes / 1024 / 1024:.1f}MB，超过总量上限 "
                f"{config.max_total_mb}MB，请减少文件或分批生成"
            )
        role = roles[index] if index < len(roles) and roles[index] in ("material", "literature") else "material"
        object_key = store.save_bytes(filename, data)
        records.append(
            DocGenInputFile(
                job_id=job.id,
                original_filename=filename[:500],
                object_key=object_key[:500],
                file_id=digest[:16],
                sha256=digest,
                size_bytes=len(data),
                mime_type=(upload.content_type or "")[:200] or None,
                role=role,
                parse_status="pending",
            )
        )
    await repo.add_input_files(session, records)
    return records


REPORT_CONTEXT_FILENAME = "本报告已填内容.txt"

# 块级标签转成换行；行内标签（b/span/a 等）直接去掉，避免把一句话切断
_HTML_BLOCK_TAG_RE = re.compile(r"</?(p|div|br|li|ul|ol|tr|h[1-6])[^>]*>", re.IGNORECASE)


def _html_to_text(value: str) -> str:
    """富文本字段剥标签后作为纯文本使用；不含标签的纯文本原样返回。"""
    if "<" not in value:
        return value
    cleaned = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", value, flags=re.IGNORECASE | re.DOTALL)
    cleaned = _HTML_BLOCK_TAG_RE.sub("\n", cleaned)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    cleaned = unescape(cleaned)
    cleaned = re.sub(r"[ \t]*\n[ \t]*", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _report_context_text(report: Any) -> str:
    """把研发报告里人工填写的字段整理成一段带小标题的文本。

    人工内容要能和资料一起被检索，因此保持「【字段名】+ 正文」的结构，
    让模型既能取到值，也能在生成说明里说清依据来自哪个字段。
    """
    parts: list[str] = []

    def add(title: str, value: Any) -> None:
        text = _html_to_text(str(value)).strip() if value else ""
        if text:
            parts.append(f"【{title}】\n{text}")

    add("报告标题", getattr(report, "title", ""))
    add("报告摘要", getattr(report, "summary", ""))
    add("报告正文", getattr(report, "content", ""))
    findings = getattr(report, "key_findings", None) or {}
    if isinstance(findings, dict):
        add("关键发现总结", findings.get("summary"))
        add("关键数据", findings.get("key_data"))
        add("发现的问题", findings.get("issues"))
    add("结论与建议", getattr(report, "recommendations", ""))
    add("备注", getattr(report, "notes", ""))
    return "\n\n".join(parts)


async def _store_report_context(session: AsyncSession, job: DocGenJob, report: Any) -> None:
    """把人工填写的报告内容作为一份虚拟资料接入生成上下文（无内容则跳过）。"""
    if report is None:
        return
    text = _report_context_text(report)
    if not text.strip():
        logger.info("报告无人工填写内容，跳过上下文注入", extra={"job_id": str(job.id), "module_code": "research"})
        return
    data = text.encode("utf-8")
    digest = hashlib.sha256(data).hexdigest()
    object_key = store.save_bytes(REPORT_CONTEXT_FILENAME, data, "text/plain; charset=utf-8")
    record = DocGenInputFile(
        job_id=job.id,
        original_filename=REPORT_CONTEXT_FILENAME,
        object_key=object_key[:500],
        file_id=f"report-{digest[:12]}",
        sha256=digest,
        size_bytes=len(data),
        mime_type="text/plain",
        role="report_draft",
        parse_status="pending",
    )
    await repo.add_input_files(session, [record])


def _to_job_response(job: DocGenJob) -> DocGenJobResponse:
    """ORM → 响应模型（不暴露存储键）。"""
    return DocGenJobResponse(
        id=job.id,
        report_id=job.report_id,
        project_id=job.project_id,
        template_code=job.template_code,
        template_version=job.template_version,
        status=job.status,
        step=job.step,
        progress=job.progress,
        has_document=bool(job.docx_object_key),
        has_report=bool(job.report_object_key),
        error_code=job.error_code,
        error_message=job.error_message,
        stats=job.stats,
        meta=job.meta,
        parent_job_id=job.parent_job_id,
        supplement_text=job.supplement_text,
        created_at=job.created_at,
        finished_at=job.finished_at,
    )


async def job_response(job: DocGenJob) -> DocGenJobResponse:
    """对外暴露的任务序列化。"""
    return _to_job_response(job)


async def get_job(session: AsyncSession, job_id: uuid.UUID) -> DocGenJob:
    """取任务，不存在则 404。"""
    job = await repo.get_job(session, job_id)
    if job is None:
        raise NotFoundException("生成任务不存在")
    return job


async def job_detail(session: AsyncSession, job_id: uuid.UUID) -> DocGenJobDetail:
    """任务详情（含大纲）。"""
    job = await get_job(session, job_id)
    files = await repo.list_input_files(session, job.id)
    slots = await repo.list_slot_values(session, job.id)
    return DocGenJobDetail(
        job=_to_job_response(job),
        files=[DocGenInputFileResponse.model_validate(f) for f in files],
        slots=[DocGenSlotValueResponse.model_validate(s) for s in slots],
        sections=await _section_responses(session, job),
    )


async def _section_responses(session: AsyncSession, job: DocGenJob) -> list[DocGenSectionResponse]:
    """任务大纲，附带各片段的预设标题池（供前端换标题的下拉）。"""
    rows = await repo.list_sections(session, job.id)
    if not rows:
        return []
    try:
        spec = await spec_source.resolve_for_job(session, job)
    except KeyError:
        spec = None
    responses: list[DocGenSectionResponse] = []
    for row in rows:
        fragment = spec.fragment(row.fragment_key) if spec is not None else None
        responses.append(
            DocGenSectionResponse(
                id=row.id,
                section_key=row.section_key,
                fragment_key=row.fragment_key,
                extension_point_key=row.extension_point_key,
                parent_section_key=row.parent_section_key,
                level=row.level,
                title=row.title,
                order_index=row.order_index,
                source=row.source,
                state=row.state,
                trigger_trace=row.trigger_trace,
                title_pool=list(fragment.title_pool) if fragment is not None else [],
            )
        )
    return responses


async def job_outline(session: AsyncSession, job_id: uuid.UUID) -> list[DocGenSectionResponse]:
    """任务大纲（复核界面的结构树数据源）。"""
    job = await get_job(session, job_id)
    return await _section_responses(session, job)


async def list_jobs_for_report(session: AsyncSession, report_id: uuid.UUID) -> list[DocGenJobResponse]:
    """某报告下的历次生成任务。"""
    jobs = await repo.list_jobs_by_report(session, report_id)
    return [_to_job_response(job) for job in jobs]


async def list_jobs_for_project(session: AsyncSession, project_id: uuid.UUID) -> list[DocGenJobResponse]:
    """某项目下全部生成任务。"""
    jobs = await repo.list_jobs_by_project(session, project_id)
    return [_to_job_response(job) for job in jobs]


async def latest_jobs_for_reports(
    session: AsyncSession, report_ids: list[uuid.UUID]
) -> dict[uuid.UUID, DocGenJobResponse]:
    """列表页用的「最新一次生成状态」批量查询。"""
    mapping = await repo.latest_jobs_by_reports(session, report_ids)
    return {rid: _to_job_response(job) for rid, job in mapping.items()}


async def cancel_job(session: AsyncSession, job_id: uuid.UUID) -> DocGenJob:
    """终止任务（排队中、执行中、待确认都可停；已完成的保持原样）。

    两步缺一不可：

    1. 先提交 ``cancelled`` 到数据库——这是跨进程的真相来源，worker 的取消轮询协程
       会在秒级内看到它（全局 session 是 ``expire_on_commit=False``，执行中的 worker
       光靠 ORM 对象永远读不到这次修改）；
    2. 再请求进程内强制终止——立即打断正在等待的模型调用与解析线程，
       而不是等这一批（最坏几分钟）跑完。
    """
    job = await get_job(session, job_id)
    if job.status in ("ready", "completed", "failed"):
        raise BadRequestException("任务已结束，无法取消")
    if job.status != "cancelled":
        job.status = "cancelled"
        job.step = "已取消"
        job.lease_expires_at = None
        job.finished_at = datetime.now(UTC)
        await session.commit()
    aborted = cancellation.request_abort(job_id, "cancelled")
    logger.info(
        "文档生成任务终止请求",
        extra={"job_id": str(job_id), "preempted": aborted},
    )
    return job


def _is_table_slot(spec: TemplateSpec, key: str) -> bool:
    """判断（可能带章节前缀的）填充项是否为表格类。"""
    section_key, raw = split_slot_key(key)
    if section_key is None:
        slot = spec.slot(raw)
        return slot is not None and slot.kind == "table"
    fragment_key = section_key.rpartition(SECTION_INSTANCE_SEP)[0]
    slot = spec.fragment_slot(fragment_key, raw)
    return slot is not None and slot.kind == "table"


async def confirm_job(
    session: AsyncSession,
    job_id: uuid.UUID,
    overrides: Mapping[str, str],
    outline: Sequence[DocGenSectionAdjust] | None = None,
) -> DocGenJob:
    """人工确认提取结果：写入修正值与大纲调整，再把任务交回 worker 续跑成文 + 渲染。

    两种状态机分支：

    - ``awaiting_review``（对话模式）：提交被修改过的填充项增量覆盖已有提取行；
    - ``draft``（直达生成模式）：确认页以「AI 提取信息」的落库结果为底，人工文本优先，
      整表重建后继续；因此草稿必须先完成提取。

    大纲调整（启用/禁用/换标题/排序）同样落库，渲染阶段按它决定章节取舍。
    """
    job = await get_job(session, job_id)
    if job.status not in ("awaiting_review", "draft"):
        raise BadRequestException("任务当前不处于待确认状态，无法确认")
    is_generate = job.status == "draft"
    if is_generate:
        # draft 状态下确认页的数据来自「AI 提取信息」；没提取过就直接生成只会得到空报告
        if not await repo.list_slot_values(session, job.id):
            raise BadRequestException("请先点击「AI 提取信息」完成提取，再确认生成")
        # 覆盖「提取未取到」的空槽（确认页上留空的可选槽位提交 ""），
        # 人工留空即视为有意不填，正常按待补充处理
        await repo.reset_extraction_results(session, job.id)
    rows = list(await repo.list_slot_values(session, job_id))
    by_key = {row.slot_key: row for row in rows}

    try:
        spec = await spec_source.resolve_for_job(session, job)
    except KeyError as exc:
        raise BadRequestException("该任务的填充项配置已失效，请重新发起生成") from exc

    if is_generate:
        changed = await _apply_overrides(session, job, spec, overrides)
        rows = list(await repo.list_slot_values(session, job_id))
        by_key = {row.slot_key: row for row in rows}
    else:
        if not rows:
            raise BadRequestException("任务没有可确认的提取结果")
        unknown = sorted(set(overrides) - set(by_key))
        if unknown:
            raise BadRequestException(f"未知的填充项：{'、'.join(unknown[:5])}")
        # 表格类填充项的值是结构化行数据，本版不支持在线编辑，明确拒绝而不是静默忽略
        rejected = sorted(key for key in overrides if _is_table_slot(spec, key))
        if rejected:
            raise BadRequestException(f"表格类填充项暂不支持在线编辑：{'、'.join(rejected[:5])}")
        changed = 0
        for key, raw in overrides.items():
            text = (raw or "").strip()
            row = by_key[key]
            if not text or text == (row.text or "").strip():
                continue
            row.text = text
            row.state = status.STATUS_OK
            row.reason = "人工确认"
            row.confidence = None
            changed += 1

    outline_changed = 0
    if outline:
        outline_changed = await _apply_outline(session, job, spec, outline, by_key)

    job.status = "confirmed"
    job.step = "已确认，等待生成"
    job.progress = 95
    job.error_code = None
    job.error_message = None
    job.finished_at = None
    logger.info(
        "doc gen job confirmed",
        extra={"job_id": str(job_id), "edited": changed, "outline": outline_changed, "module_code": "research"},
    )
    return job


def _slot_label(spec: TemplateSpec, key: str) -> str:
    """填充项 key → 展示名；章节槽位（``section__i.key``）查段内局部定义。"""
    section_key, raw_key = split_slot_key(key)
    if section_key:
        fragment_key = section_key.rpartition(SECTION_INSTANCE_SEP)[0]
        slot = spec.fragment_slot(fragment_key, raw_key)
        return slot.label if slot is not None else raw_key
    slot = spec.slot(key)
    return slot.label if slot is not None else key


async def _apply_overrides(
    session: AsyncSession,
    job: DocGenJob,
    spec: TemplateSpec,
    overrides: Mapping[str, str],
) -> int:
    """把人工确认文本作为已验证槽位值整表落库（直达生成模式），返回写入条数。

    提取阶段写入的证据/置信度行由前面的 ``reset_extraction_results`` 清掉；
    本函数重建带人工来源的行，保证后续成文/渲染有统一的取值底稿。
    表格类槽位（带 rows 的值）不支持文本覆盖，直接报错而不是静默忽略。
    """
    existing = {row.slot_key for row in await repo.list_slot_values(session, job.id)}
    unknown = sorted(set(overrides) - existing)
    if unknown:
        raise BadRequestException(f"未知的填充项：{'、'.join(unknown[:5])}")
    rows: list[DocGenSlotValue] = []
    for key, raw in overrides.items():
        text = (raw or "").strip()
        section_key, raw_key = split_slot_key(key)
        instance_index = int(section_key.rsplit(SECTION_INSTANCE_SEP, 1)[1]) if section_key else None
        rows.append(
            DocGenSlotValue(
                job_id=job.id,
                slot_key=key,
                section_key=section_key,
                instance_index=instance_index,
                label=_slot_label(spec, key),
                text=text,
                rows=None,
                state=status.STATUS_OK,
                reason="人工确认",
                evidence=[{"file_id": "human", "quote": text, "page": None}] if text else [],
                pre_compose_text=None,
            )
        )
    await repo.add_slot_values(session, rows)
    await session.flush()
    return len(rows)


async def extract_inputs(session: AsyncSession, job_id: uuid.UUID) -> DocGenJob:
    """「AI 提取信息」：草稿任务排队提取；复核/失败任务清空旧结果重新提取。

    提取完成后由流水线落库槽位值并停在「等待确认」。提取中/生成中拒绝重入。
    """
    job = await get_job(session, job_id)
    if job.status in RUNNING_STATUSES:
        raise BadRequestException("任务正在运行中，请等待完成或先终止")
    if job.status == "completed":
        raise BadRequestException("报告已生成，如需重做请使用「重新生成」")
    if job.status == "cancelled":
        raise BadRequestException("任务已终止，请重新创建生成任务")
    if job.status in ("awaiting_review", "failed"):
        # 重新提取会清空确认页上的人工修改，这是明确操作，不做静默保留
        await repo.reset_extraction_results(session, job.id)
    elif job.status != "draft":
        raise BadRequestException(f"任务当前状态（{job.status}）不支持提取信息")
    await repo.enqueue_extract(session, job.id)
    logger.info("doc gen extraction queued", extra={"job_id": str(job_id), "module_code": "research"})
    return job


async def list_superseded(session: AsyncSession, job_id: uuid.UUID) -> list[dict[str, Any]]:
    """任务所在重新生成链上、已被新一轮取代的历史生成任务（含祖先链与子孙链）。"""
    job = await get_job(session, job_id)
    chain = await repo.list_superseded_sibling_jobs(session, job.id, job.parent_job_id)
    return [
        {
            "id": str(item.id),
            "status": item.status,
            "step": item.step,
            "progress": item.progress,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "finished_at": item.finished_at.isoformat() if item.finished_at else None,
        }
        for item in chain
    ]


async def regenerate_job(session: AsyncSession, job_id: uuid.UUID, user_id: uuid.UUID | None) -> DocGenJob:
    """「重新生成」：新建任务挂到当前任务之下，沿用资料、补充说明与人工确认值。

    旧任务不原地重跑——产物与审计链完整保留，新任务通过 parent_job_id 溯源；
    若旧任务还在排队/执行中则先请求终止，避免两轮并写同一报告。
    """
    source = await get_job(session, job_id)
    if source.status not in ("awaiting_review", "failed", "completed", "cancelled"):
        raise BadRequestException("任务当前状态不支持重新生成")
    try:
        await spec_source.resolve_for_job(session, source)
    except KeyError as exc:
        raise BadRequestException("该任务的填充项配置已失效，请重新发起生成") from exc
    job = DocGenJob(
        report_id=source.report_id,
        project_id=source.project_id,
        parent_job_id=source.id,
        template_code=source.template_code,
        template_version=source.template_version,
        meta=dict(source.meta or {}),
        supplement_text=source.supplement_text,
        status="pending",
        step="排队中",
        progress=0,
        attempts=0,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(job)
    await session.flush()
    await repo.copy_input_files(session, source.id, job.id)
    if source.status == "completed":
        # 已定稿报告上点「重新生成」是换写法不是换提取：确认过的取值整表沿用，
        # 新任务检测到已有结果直接成文 + 渲染；复核/失败状态重新生成则完整重跑提取
        await repo.copy_extraction_results(session, source.id, job.id)
    report: Any = None
    if source.report_id is not None:
        report = await session.get(rd_models.RdReport, source.report_id)
    await _store_report_context(session, job, report)
    logger.info(
        "doc gen job regenerated",
        extra={"job_id": str(job.id), "parent_job_id": str(source.id), "module_code": "research"},
    )
    return job


async def append_input_files(
    session: AsyncSession,
    job_id: uuid.UUID,
    files: Sequence[UploadFile],
    roles: Sequence[str] = (),
) -> DocGenJobDetail:
    """向未运行的任务追加资料文件（逐文件上传入口），返回最新任务详情。"""
    job = await get_job(session, job_id)
    if job.status in RUNNING_STATUSES:
        raise BadRequestException("任务正在运行中，请等待完成或先终止")
    if job.status == "completed":
        raise BadRequestException("报告已生成，如需调整资料请使用「重新生成」")
    if job.status != "draft":
        raise BadRequestException("资料已进入提取流程，无法追加文件")
    config = await load_runtime_config()
    if len(files) > config.max_files:
        raise BadRequestException(f"资料文件最多 {config.max_files} 个，当前 {len(files)} 个")
    _validate_extensions(list(files))
    stored = await _store_uploads(session, job, list(files), list(roles), config)
    if not stored:
        raise BadRequestException("文件为空或重复，未能追加")
    await session.flush()
    logger.info(
        "doc gen files appended",
        extra={"job_id": str(job_id), "count": len(stored), "module_code": "research"},
    )
    return await job_detail(session, job_id)


async def remove_input_file(session: AsyncSession, job_id: uuid.UUID, file_row_id: uuid.UUID) -> DocGenJobDetail:
    """从任务移除一个资料文件（软删除），返回最新任务详情。"""
    job = await get_job(session, job_id)
    if job.status not in EDITABLE_INPUT_STATUSES:
        raise BadRequestException("任务当前状态不允许删除资料文件")
    if not await repo.soft_delete_input_file(session, job_id, file_row_id):
        raise NotFoundException("资料文件不存在或已删除")
    await session.flush()
    return await job_detail(session, job_id)


async def _apply_outline(
    session: AsyncSession,
    job: DocGenJob,
    spec: TemplateSpec,
    adjustments: Sequence[DocGenSectionAdjust],
    slot_rows_by_key: Mapping[str, Any],
) -> int:
    """把人工的大纲调整落到章节实例上，返回调整的章节数。"""
    section_rows = {row.section_key: row for row in await repo.list_sections(session, job.id)}
    if not section_rows:
        raise BadRequestException("该任务没有大纲可调整")
    changed = 0
    for adjust in adjustments:
        row = section_rows.get(adjust.section_key)
        if row is None:
            raise BadRequestException(f"未知的章节：{adjust.section_key}")
        if adjust.state is not None and adjust.state != row.state:
            row.state = adjust.state
            changed += 1
        if adjust.order_index is not None and adjust.order_index != row.order_index:
            row.order_index = adjust.order_index
            changed += 1
        if adjust.title is not None and adjust.title.strip() and adjust.title.strip() != row.title:
            row.title = _resolve_section_title(spec, row, adjust.title.strip(), slot_rows_by_key, job)
            changed += 1
    await session.flush()
    return changed


def _resolve_section_title(
    spec: TemplateSpec,
    row: Any,
    chosen: str,
    slot_rows_by_key: Mapping[str, Any],
    job: DocGenJob,
) -> str:
    """把人工选定的标题池项重新合成成最终标题（变量用当前取值与重复源行填充）。"""
    fragment = spec.fragment(row.fragment_key)
    if fragment is None:
        raise BadRequestException(f"章节 {row.section_key} 的片段定义已失效，无法更换标题")
    repeat_row = ((row.trigger_trace or {}).get("repeat") or {}).get("row") or {}
    try:
        title, _warnings = recompose_title(
            fragment,
            row.section_key,
            chosen,
            results=slot_rows_by_key,
            meta=dict(job.meta or {}),
            repeat_row=repeat_row,
        )
    except ValueError as exc:
        raise BadRequestException(str(exc)) from exc
    return title


async def download_artifact(session: AsyncSession, job_id: uuid.UUID, kind: str) -> tuple[bytes, str, str]:
    """下载产物，返回 (字节, 文件名, MIME)。"""
    job = await get_job(session, job_id)
    key = job.docx_object_key if kind == "document" else job.report_object_key
    if not key:
        raise NotFoundException("该任务还没有可下载产物")
    data = store.load_bytes(key)
    if data is None:
        raise NotFoundException("产物读取失败（存储不可用或已被清理）")
    if kind == "document":
        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        suffix = ".docx"
    else:
        mime = "text/markdown; charset=utf-8"
        suffix = ".md"
    name = f"{job.template_code}-v{job.template_version}-初版{suffix}"
    return data, name, mime


async def download_input_file(
    session: AsyncSession, job_id: uuid.UUID, file_id: uuid.UUID
) -> tuple[bytes, str, str]:
    """下载任务的资料文件，返回 (字节, 文件名, MIME)。"""
    await get_job(session, job_id)  # 校验任务存在
    file_record = await repo.get_input_file(session, job_id, file_id)
    if file_record is None:
        raise NotFoundException("资料文件不存在")
    data = store.load_bytes(file_record.object_key)
    if data is None:
        raise NotFoundException("文件读取失败（存储不可用或已被清理）")
    mime = file_record.mime_type or "application/octet-stream"
    return data, file_record.original_filename, mime



# ===== 交付物模板：Word 母本管理 =====

WORD_EXTENSIONS = {".docx", ".dotx", ".doc"}
_ZIP_MAGIC = b"PK\x03\x04"
_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
MAX_TEMPLATE_BYTES = 50 * 1024 * 1024


def sniff_word_ext(filename: str, data: bytes) -> str:
    """校验文件内容与扩展名一致，返回规范化扩展名。

    只看扩展名会让改后缀的垃圾文件进库，直到渲染阶段才以 anchor_unresolved 暴露，
    排查成本极高，因此在入口处用文件头判断真实格式。
    """
    ext = Path(filename).suffix.lower()
    if ext not in WORD_EXTENSIONS:
        raise BadRequestException(f"不支持的模板格式：{ext or '未知'}（仅支持 {'、'.join(sorted(WORD_EXTENSIONS))}）")
    if not data:
        raise BadRequestException(f"模板文件为空：{filename}")
    if len(data) > MAX_TEMPLATE_BYTES:
        raise BadRequestException(f"模板文件超过 {MAX_TEMPLATE_BYTES // 1024 // 1024}MB 上限：{filename}")
    head = data[:8]
    if ext in {".docx", ".dotx"} and not head.startswith(_ZIP_MAGIC):
        raise BadRequestException(f"文件内容与扩展名不符（{filename} 不是真正的 Word XML 文档）")
    if ext == ".doc" and not head.startswith(_OLE_MAGIC):
        raise BadRequestException(f"文件内容与扩展名不符（{filename} 不是真正的 Word 97-2003 文档）")
    return ext


def _spec_summary(spec: TemplateSpec) -> dict[str, Any]:
    """规格概况（对外回显用，不暴露锚点细节）。"""
    return {
        "code": spec.code,
        "name": spec.name,
        "version": spec.version,
        "stage": spec.stage,
        "description": spec.description,
        "slot_count": len(spec.slots),
        "required_count": sum(1 for slot in spec.slots if slot.required),
        "unfilled_notes": list(spec.unfilled_notes),
    }


async def slot_profiles() -> list[dict[str, Any]]:
    """代码内置的槽位定义清单（排错用；上传时不需要用户选择）。"""
    from app.modules.research.doc_gen.templates import list_templates

    return [_spec_summary(spec) for spec in list_templates()]


async def _known_specs(session: AsyncSession) -> list[TemplateSpec]:
    """可参与上传自动匹配的规格：代码内置 + 历史自动识别并落库的结构。"""
    from sqlalchemy import select

    from app.modules.research.doc_gen.templates import list_templates
    from app.modules.research.models import RdDeliverableTemplate

    specs: dict[str, TemplateSpec] = {spec.code: spec for spec in list_templates()}
    rows = (
        await session.execute(
            select(RdDeliverableTemplate).where(
                RdDeliverableTemplate.is_deleted.is_(False),
                RdDeliverableTemplate.template_structure.isnot(None),
            )
        )
    ).scalars().all()
    for row in rows:
        spec = spec_source.spec_from_structure(row.template_structure, code_hint=row.template_code or "")
        if spec is not None:
            specs.setdefault(spec.code, spec)
    return list(specs.values())


def _auto_draft(data: bytes, name: str) -> TemplateSpec:
    """识别不到既有配置时，按母本结构自动草拟一套规格（用户无需任何选择）。"""
    try:
        return draft_spec_from_bytes(data, name=name)
    except Exception as exc:  # noqa: BLE001 - 损坏文件要给出可读提示而不是 500
        logger.exception("母本结构识别失败", extra={"name": name, "module_code": "research"})
        raise BadRequestException(f"无法读取这份 Word 的结构：{name}（{type(exc).__name__}）") from exc


async def usable_templates(session: AsyncSession) -> list[dict[str, Any]]:
    """可用于 AI 生成的交付物模板：必须有 Word 母本 + 可解析的槽位定义。"""
    from sqlalchemy import select

    from app.modules.research.models import RdDeliverableTemplate

    rows = (
        await session.execute(
            select(RdDeliverableTemplate)
            .where(
                RdDeliverableTemplate.is_deleted.is_(False),
                RdDeliverableTemplate.is_active.is_(True),
                RdDeliverableTemplate.file_object_key.isnot(None),
            )
            .order_by(RdDeliverableTemplate.created_at.desc())
        )
    ).scalars().all()
    result: list[dict[str, Any]] = []
    for row in rows:
        spec = spec_source.spec_from_code(row.template_code or "") or spec_source.spec_from_structure(
            row.template_structure, code_hint=row.template_code or ""
        )
        if spec is None:
            continue  # 既无代码配置也无可解析结构：不暴露给生成入口，避免选了必失败
        profile = _spec_summary(spec)
        result.append(
            {
                "id": str(row.id),
                "name": row.name,
                "template_code": row.template_code,
                "template_version": profile["version"],
                "stage": row.stage,
                "description": row.description or profile["description"],
                "file_name": row.file_name,
                "file_ext": row.file_ext,
                "slot_count": profile["slot_count"],
                "required_count": profile["required_count"],
                "unfilled_notes": profile["unfilled_notes"],
            }
        )
    return result


async def attach_template_file(
    session: AsyncSession,
    template: Any,
    filename: str,
    data: bytes,
    user_id: uuid.UUID | None,
    change_note: str | None = None,
) -> str:
    """校验并挂载一个 Word 母本到模板记录，返回存储键。

    槽位定义由系统自动确定：先按母本结构匹配已有规格，匹配不到就直接按母本结构
    自动识别生成一套并落库。用户不需要（也不应该）理解「填充项配置」这个概念。

    每次挂载都会在版本表留档一条新记录（首次即 v1），并把模板主表指向它——主表
    始终等于「当前生效版本」，所以生成链路完全不需要感知版本表。

    刻意不碰 ``is_active``：上传 ≠ 启用，母本与槽位需人工核对后才手动开启。
    """
    ext = sniff_word_ext(filename, data)
    existing = spec_source.spec_from_code(template.template_code or "") or spec_source.spec_from_structure(
        template.template_structure, code_hint=template.template_code or ""
    )
    if existing is None:
        probe = probe_template_match(data, await _known_specs(session))
        if probe["matched"] is not None:
            template.template_code = str(probe["matched"])[:100]
            template.template_structure = None  # 代码内置规格不需要落库副本
        else:
            draft = _auto_draft(data, Path(filename).stem or template.name)
            template.template_code = draft.code[:100]
            template.template_structure = draft.model_dump(mode="json")
    key = store.save_bytes(
        f"template{ext}",
        data,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if ext != ".doc"
        else "application/msword",
    )
    template.file_object_key = key
    template.file_name = filename[:500]
    template.file_ext = ext
    template.updated_by = user_id
    # 先同步主表再留档：版本快照记录的应是「本次挂载后」的槽位定义
    await _record_template_version(
        session,
        template,
        filename=filename,
        ext=ext,
        size=len(data),
        key=key,
        change_note=change_note,
        user_id=user_id,
    )
    await session.flush()
    return key


async def _record_template_version(
    session: AsyncSession,
    template: Any,
    *,
    filename: str,
    ext: str,
    size: int | None,
    key: str,
    change_note: str | None,
    user_id: uuid.UUID | None,
) -> Any:
    """把刚挂载的母本留档为模板的新版本，并置为当前生效版本。

    版本号在模板行锁内取 ``max(version_no) + 1``：并发上传同一模板不会算出同一个号，
    ``UniqueConstraint(template_id, version_no)`` 是最后一道保险。软删的版本仍占号，
    因此版本号单调递增、永不复用。
    """
    from sqlalchemy import func, select, update

    from app.modules.research.models import RdDeliverableTemplate, RdDeliverableTemplateVersion

    # 锁模板行，避免并发上传把同一个版本号写两次
    await session.execute(
        select(RdDeliverableTemplate.id).where(RdDeliverableTemplate.id == template.id).with_for_update()
    )
    current_max = (
        await session.execute(
            select(func.max(RdDeliverableTemplateVersion.version_no)).where(
                RdDeliverableTemplateVersion.template_id == template.id
            )
        )
    ).scalar_one_or_none()
    version_no = int(current_max or 0) + 1

    # 旧的当前版本退位；连软删记录一并清掉，保证部分唯一索引不被占用
    await session.execute(
        update(RdDeliverableTemplateVersion)
        .where(
            RdDeliverableTemplateVersion.template_id == template.id,
            RdDeliverableTemplateVersion.is_current.is_(True),
        )
        .values(is_current=False)
        .execution_options(synchronize_session=False)
    )

    version = RdDeliverableTemplateVersion(
        template_id=template.id,
        version_no=version_no,
        file_object_key=key,
        file_name=filename[:500],
        file_ext=ext,
        file_size=size,
        template_code=template.template_code,
        template_structure=template.template_structure,
        change_note=(change_note or "").strip() or None,
        is_current=True,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(version)
    await session.flush()
    return version


async def batch_upload_templates(
    session: AsyncSession,
    uploads: list[UploadFile],
    stage: str = "",
    deliverable_type: str = "",
    user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """批量上传 Word 母本：每个文件建一条模板记录，槽位定义自动识别。

    同名文件不再跳过，而是作为该模板的新版本挂载——原行为要求先删掉旧模板再传，
    会把历史版本一并丢掉，正是版本管理要解决的问题。
    """
    from sqlalchemy import select

    from app.modules.research.models import RdDeliverableTemplate

    if not uploads:
        raise BadRequestException("请选择至少一个模板文件")

    created: list[dict[str, str]] = []
    versioned: list[dict[str, str]] = []
    skipped: list[str] = []
    for upload in uploads:
        filename = (upload.filename or "").strip()
        if not filename:
            continue
        data = await upload.read()
        try:
            ext = sniff_word_ext(filename, data)
        except BadRequestException as exc:
            skipped.append(f"{filename}：{exc.detail if hasattr(exc, 'detail') else exc}")
            continue
        probe = probe_template_match(data, await _known_specs(session))
        matched = probe["matched"]
        best = probe["best"] or {}
        hit_text = f"{best.get('hit', 0)}/{best.get('total', 0)}"
        name = Path(filename).stem[:200]
        existing = (
            await session.execute(
                select(RdDeliverableTemplate).where(
                    RdDeliverableTemplate.name == name,
                    RdDeliverableTemplate.is_deleted.is_(False),
                )
            )
        ).scalars().first()
        if existing is not None:
            # 同名即该模板的新版本：母本换代，旧版本留在版本表里可回滚
            await attach_template_file(
                session, existing, filename, data, user_id, change_note="批量上传新版本"
            )
            current = await _current_template_version(session, existing.id)
            versioned.append(
                {
                    "id": str(existing.id),
                    "name": name,
                    "version_no": str(current.version_no if current is not None else ""),
                    "file_name": filename,
                }
            )
            continue
        if matched is not None:
            template = RdDeliverableTemplate(
                name=name,
                deliverable_type=(deliverable_type or str(matched))[:50],
                stage=(stage or str(best.get("stage") or ""))[:50],
                template_code=str(matched)[:100],
                description=f"由 {filename} 上传，自动匹配为「{best.get('name', '')}」填充项配置（匹配 {hit_text}）",
                is_active=False,
                created_by=user_id,
            )
        else:
            # 没有既有配置：按母本结构自动识别生成一套，用户无需选择
            draft = _auto_draft(data, name)
            matched = draft.code
            hit_text = f"自动识别 {len(draft.slots)} 项"
            template = RdDeliverableTemplate(
                name=name,
                deliverable_type=(deliverable_type or draft.code)[:50],
                stage=(stage or "")[:50],
                template_code=draft.code[:100],
                template_structure=draft.model_dump(mode="json"),
                description=f"由 {filename} 上传，已按母本结构自动识别 {len(draft.slots)} 处填充项",
                is_active=False,
                created_by=user_id,
            )
        session.add(template)
        await session.flush()
        await attach_template_file(session, template, filename, data, user_id)
        created.append(
            {"id": str(template.id), "name": name, "file_ext": ext, "matched": str(matched), "hit": hit_text}
        )
    return {"created": created, "versioned": versioned, "skipped": skipped}


def _template_mime(ext: str) -> str:
    """按扩展名给出下载 MIME。"""
    if ext == ".doc":
        return "application/msword"
    if ext == ".dotx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.template"
    return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


async def _load_template_or_404(session: AsyncSession, template_id: uuid.UUID) -> Any:
    """取模板记录，不存在（或已软删）即 404。"""
    from app.modules.research.models import RdDeliverableTemplate

    template = await session.get(RdDeliverableTemplate, template_id)
    if template is None or template.is_deleted:
        raise NotFoundException("模板不存在")
    return template


async def _current_template_version(session: AsyncSession, template_id: uuid.UUID) -> Any:
    """该模板当前生效的版本记录（尚未留档任何版本时返回 None）。"""
    from sqlalchemy import select

    from app.modules.research.models import RdDeliverableTemplateVersion

    return (
        await session.execute(
            select(RdDeliverableTemplateVersion).where(
                RdDeliverableTemplateVersion.template_id == template_id,
                RdDeliverableTemplateVersion.is_current.is_(True),
                RdDeliverableTemplateVersion.is_deleted.is_(False),
            )
        )
    ).scalars().first()


async def template_download_payload(session: AsyncSession, template_id: uuid.UUID) -> tuple[bytes, str, str]:
    """取模板「当前生效版本」的母本字节流，返回 (data, 下载文件名, MIME)。"""
    template = await _load_template_or_404(session, template_id)
    if not template.file_object_key:
        raise NotFoundException("该模板尚未上传 Word 模板原件")
    data = store.load_bytes(template.file_object_key)
    if data is None:
        raise NotFoundException("模板文件读取失败（存储不可用或文件已被清理）")
    ext = template.file_ext or ".docx"
    return data, f"{template.name}{ext}", _template_mime(ext)


async def _get_template_version(
    session: AsyncSession, template_id: uuid.UUID, version_id: uuid.UUID
) -> tuple[Any, Any]:
    """取模板 + 指定版本；不存在、已软删或不属于该模板均按 404 处理。"""
    from app.modules.research.models import RdDeliverableTemplateVersion

    template = await _load_template_or_404(session, template_id)
    version = await session.get(RdDeliverableTemplateVersion, version_id)
    if version is None or version.is_deleted or version.template_id != template.id:
        raise NotFoundException("模板版本不存在")
    return template, version


async def template_version_download_payload(
    session: AsyncSession, template_id: uuid.UUID, version_id: uuid.UUID
) -> tuple[bytes, str, str]:
    """取某个历史版本的母本字节流，返回 (data, 下载文件名, MIME)。

    文件名带版本号，避免多次下载同名文件互相覆盖。
    """
    template, version = await _get_template_version(session, template_id, version_id)
    data = store.load_bytes(version.file_object_key)
    if data is None:
        raise NotFoundException("该版本文件读取失败（存储不可用或文件已被清理）")
    ext = version.file_ext or ".docx"
    return data, f"{template.name}-v{version.version_no}{ext}", _template_mime(ext)


async def list_template_versions(session: AsyncSession, template_id: uuid.UUID) -> list[dict[str, Any]]:
    """模板的版本历史（新版本在前），带上传人姓名便于审计。"""
    from sqlalchemy import select

    from app.modules.research.models import RdDeliverableTemplateVersion
    from app.platform.identity.models import User

    template = await _load_template_or_404(session, template_id)
    rows = (
        await session.execute(
            select(RdDeliverableTemplateVersion)
            .where(
                RdDeliverableTemplateVersion.template_id == template.id,
                RdDeliverableTemplateVersion.is_deleted.is_(False),
            )
            .order_by(RdDeliverableTemplateVersion.version_no.desc())
        )
    ).scalars().all()

    # 上传人姓名一次性批量取，避免逐行查询
    uploader_ids = {row.created_by for row in rows if row.created_by is not None}
    names: dict[uuid.UUID, str] = {}
    if uploader_ids:
        names = {
            user_id: name
            for user_id, name in (
                await session.execute(select(User.id, User.name).where(User.id.in_(uploader_ids)))
            ).all()
        }

    return [
        {
            "id": row.id,
            "version_no": row.version_no,
            "file_name": row.file_name,
            "file_ext": row.file_ext,
            "file_size": row.file_size,
            "template_code": row.template_code,
            "change_note": row.change_note,
            "is_current": row.is_current,
            "created_by": row.created_by,
            "created_by_name": names.get(row.created_by) if row.created_by is not None else None,
            "created_at": row.created_at,
        }
        for row in rows
    ]


async def restore_template_version(
    session: AsyncSession,
    template_id: uuid.UUID,
    version_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """回滚：以目标版本的内容新建 v(N+1) 并设为当前生效版本。

    历史版本本身不被改写（版本号单调递增，类似 git revert），也不复制存储对象——
    新版本复用目标版本的文件键，所以回滚不产生额外文件副本。槽位定义快照一并回填，
    避免出现「旧母本 + 新槽位」的错配。
    """
    template, version = await _get_template_version(session, template_id, version_id)
    if version.is_current:
        raise BadRequestException(f"v{version.version_no} 已是当前生效版本，无需回滚")
    # 先让主表等于目标版本，_record_template_version 才能快照到正确的槽位定义
    template.file_object_key = version.file_object_key
    template.file_name = version.file_name
    template.file_ext = version.file_ext
    template.template_code = version.template_code
    template.template_structure = version.template_structure
    template.updated_by = user_id
    new_version = await _record_template_version(
        session,
        template,
        filename=version.file_name or template.name,
        ext=version.file_ext or ".docx",
        size=version.file_size,
        key=version.file_object_key,
        change_note=f"回滚自 v{version.version_no}",
        user_id=user_id,
    )
    logger.info(
        "template version restored",
        extra={
            "template_id": str(template.id),
            "from_version": version.version_no,
            "new_version": new_version.version_no,
        },
    )
    return {
        "id": str(new_version.id),
        "template_id": str(template.id),
        "version_no": new_version.version_no,
        "from_version_no": version.version_no,
        "file_name": new_version.file_name,
        "file_ext": new_version.file_ext,
    }


async def delete_template_version(
    session: AsyncSession,
    template_id: uuid.UUID,
    version_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
) -> None:
    """软删一个历史版本。

    当前生效版本与模板的唯一版本都不能删（否则就没有可用母本了）。只软删记录、
    不删存储对象：留档的意义在于可追溯，物理删文件不可逆，风险高于收益。
    """
    from sqlalchemy import func, select

    from app.modules.research.models import RdDeliverableTemplateVersion

    template, version = await _get_template_version(session, template_id, version_id)
    if version.is_current:
        raise BadRequestException("当前生效版本不能删除；如需替换请上传新版本，或先回滚到其他版本")
    total = (
        await session.execute(
            select(func.count())
            .select_from(RdDeliverableTemplateVersion)
            .where(
                RdDeliverableTemplateVersion.template_id == template.id,
                RdDeliverableTemplateVersion.is_deleted.is_(False),
            )
        )
    ).scalar_one()
    if total <= 1:
        raise BadRequestException("这是该模板的唯一版本，不能删除")
    version.is_deleted = True
    version.updated_by = user_id
    await session.flush()


MIN_ANCHOR_HIT_RATIO = 0.5


def probe_template_match(data: bytes, specs: list[TemplateSpec] | None = None) -> dict[str, Any]:
    """用上传的 Word 试匹配已有填充项配置，返回匹配最好的那套。

    目的是让上传方不必理解「填充项配置」这个概念：系统自己判断这份 Word 像哪种文档。
    全部低于阈值时返回 matched=None，由调用方按母本结构自动识别并生成新配置。
    """
    from app.modules.research.doc_gen.anchors import AnchorUnresolvedError, resolve_anchor
    from app.modules.research.doc_gen.renderer import open_document
    from app.modules.research.doc_gen.templates import list_templates

    pool = specs if specs is not None else list_templates()
    candidates: list[dict[str, Any]] = []
    for spec in pool:
        doc = open_document(data)  # 每套定义用全新副本，避免探测时的段落补建互相影响
        hit = 0
        for slot in spec.slots:
            try:
                for anchor in slot.anchors:
                    resolve_anchor(doc, slot, anchor)
                hit += 1
            except AnchorUnresolvedError:
                continue
        total = len(spec.slots) or 1
        candidates.append(
            {"code": spec.code, "name": spec.name, "stage": spec.stage, "hit": hit, "total": total}
        )
    candidates.sort(key=lambda c: c["hit"] / c["total"], reverse=True)
    best = candidates[0] if candidates else None
    matched = best["code"] if best and best["hit"] / best["total"] >= MIN_ANCHOR_HIT_RATIO else None
    return {"matched": matched, "candidates": candidates, "best": best}

