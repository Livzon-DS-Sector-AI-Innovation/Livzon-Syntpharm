"""成品文档版本：留档、切换、按当前槽位重渲染、上传改稿。

职责边界：``service.py`` 顶层 import ``agent``，而 agent 出稿后要记一条 ``ai_draft``
版本；版本逻辑若写进 service 会形成 service ↔ agent 双向依赖。本模块只依赖
models / render / store，交付物同步用函数内延迟导入。

并发：同一任务的版本号由「锁任务行 + max(version_no)+1」保证，
配合 ``uq_research_rd_report_gen_doc_versions_no`` 唯一约束兜底。
"""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.modules.research.doc_template import store
from app.modules.research.models import (
    RdDeliverableTemplate,
    RdReport,
    RdReportGenDocumentVersion,
    RdReportGenJob,
    RdReportGenSlot,
)
from app.modules.research.report_gen.fills import build_fills
from app.modules.research.report_gen.render import render_document
from app.modules.research.report_gen.schemas import (
    ReportGenDocumentVersionData,
    ReportGenDocumentVersionListData,
    ReportGenRenderData,
)

logger = logging.getLogger(__name__)

DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_MARKDOWN_CONTENT_TYPE = "text/markdown; charset=utf-8"

# 与交付物上传保持同一量级：研发报告正文远小于此，超过基本是传错文件
_MAX_UPLOAD_BYTES = 50 * 1024 * 1024

KIND_AI_DRAFT = "ai_draft"
KIND_MANUAL_RENDER = "manual_render"
KIND_MANUAL_UPLOAD = "manual_upload"


def _to_version_data(row: RdReportGenDocumentVersion) -> ReportGenDocumentVersionData:
    return ReportGenDocumentVersionData(
        id=row.id,
        job_id=row.job_id,
        version_no=row.version_no,
        kind=row.kind,
        file_name=row.file_name,
        file_size=row.file_size,
        note=row.note,
        is_current=bool(row.is_current),
        created_at=row.created_at,
    )


async def _get_job(session: AsyncSession, job_id: UUID) -> RdReportGenJob:
    job = await session.get(RdReportGenJob, job_id)
    if job is None or job.is_deleted:
        raise NotFoundException("生成任务")
    return job


async def _lock_job(session: AsyncSession, job_id: UUID) -> RdReportGenJob:
    """锁任务行：版本号自增与「当前版本」切换必须串行，否则并发改稿会出现两个 current。"""
    result = await session.execute(select(RdReportGenJob).where(RdReportGenJob.id == job_id).with_for_update())
    job = result.scalars().first()
    if job is None or job.is_deleted:
        raise NotFoundException("生成任务")
    return job


async def _next_version_no(session: AsyncSession, job_id: UUID) -> int:
    result = await session.execute(
        select(func.max(RdReportGenDocumentVersion.version_no)).where(
            RdReportGenDocumentVersion.job_id == job_id,
            RdReportGenDocumentVersion.is_deleted.is_(False),
        )
    )
    return (result.scalar() or 0) + 1


async def _append_version(
    session: AsyncSession,
    job: RdReportGenJob,
    *,
    kind: str,
    object_key: str,
    comparison_object_key: str | None,
    file_name: str | None,
    file_size: int | None,
    note: str | None,
    user_id: UUID | None,
) -> RdReportGenDocumentVersion:
    """追加一版并置为当前：先把旧 current 落掉，再插新行。"""
    await session.execute(
        update(RdReportGenDocumentVersion)
        .where(
            RdReportGenDocumentVersion.job_id == job.id,
            RdReportGenDocumentVersion.is_current.is_(True),
        )
        .values(is_current=False)
    )
    row = RdReportGenDocumentVersion(
        job_id=job.id,
        version_no=await _next_version_no(session, job.id),
        kind=kind,
        object_key=object_key,
        comparison_object_key=comparison_object_key,
        file_name=file_name,
        file_size=file_size,
        note=note,
        is_current=True,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(row)
    await session.flush()
    return row


async def list_versions(session: AsyncSession, job_id: UUID) -> ReportGenDocumentVersionListData:
    """版本时间线：新到旧，第一屏就能看到当前版。"""
    await _get_job(session, job_id)
    result = await session.execute(
        select(RdReportGenDocumentVersion)
        .where(
            RdReportGenDocumentVersion.job_id == job_id,
            RdReportGenDocumentVersion.is_deleted.is_(False),
        )
        .order_by(RdReportGenDocumentVersion.version_no.desc())
    )
    rows = result.scalars().all()
    return ReportGenDocumentVersionListData(items=[_to_version_data(row) for row in rows], total=len(rows))


async def record_ai_draft(
    session: AsyncSession,
    job: RdReportGenJob,
    *,
    file_name: str | None,
    file_size: int | None = None,
) -> RdReportGenDocumentVersion | None:
    """Agent 出稿后记一条 ai_draft。缺键（异常中断）时静默跳过，不拖失败状态。"""
    if not job.document_object_key:
        return None
    return await _append_version(
        session,
        job,
        kind=KIND_AI_DRAFT,
        object_key=job.document_object_key,
        comparison_object_key=job.comparison_object_key,
        file_name=file_name,
        file_size=file_size,
        note="AI 生成初稿",
        user_id=None,
    )


def _safe_stem(text: str | None, fallback: str = "report") -> str:
    cleaned = (text or "").replace("/", "_").replace("\\", "_").strip()
    return (cleaned or fallback)[:60]


async def _load_template_bytes(session: AsyncSession, job: RdReportGenJob) -> bytes:
    """取母本：优先任务快照，缺失时回退模板当前文件，两者都没有就明确报错。"""
    if job.template_file_key:
        data = store.load_bytes(job.template_file_key)
        if data:
            return data
        logger.warning(
            "report gen rerender: template snapshot missing, fallback to template file",
            extra={"job_id": str(job.id)},
        )
    if job.deliverable_template_id:
        template = await session.get(RdDeliverableTemplate, job.deliverable_template_id)
        if template is not None and template.file_object_key:
            data = store.load_bytes(str(template.file_object_key))
            if data:
                return data
    raise BadRequestException("找不到这次生成用的 Word 母本，无法重新渲染，请重新生成一次")


async def _sync_deliverable(session: AsyncSession, job: RdReportGenJob) -> bool:
    """把最新成品同步到阶段交付物附件；失败只记日志，不影响改稿本身。"""
    from app.modules.research.deliverable_generation import sync_job_result

    try:
        await sync_job_result(session, job)
    except Exception:  # noqa: BLE001 - 回写是增益项，不能让重渲染整体失败
        logger.exception("report gen rerender: sync deliverable failed", extra={"job_id": str(job.id)})
        return False
    return True


async def render_from_slots(session: AsyncSession, job_id: UUID, user_id: UUID | None) -> ReportGenRenderData:
    """按当前槽位重新渲染 docx：不跑 LLM，纯按母本锚点回填，秒级完成。"""
    job = await _lock_job(session, job_id)
    if job.status != "completed":
        raise BadRequestException("这次生成还没跑完，等出稿后再应用修改")

    template_bytes = await _load_template_bytes(session, job)
    rows = (
        (
            await session.execute(
                select(RdReportGenSlot)
                .where(
                    RdReportGenSlot.job_id == job.id,
                    RdReportGenSlot.is_deleted.is_(False),
                )
                .order_by(RdReportGenSlot.slot_key)
            )
        )
        .scalars()
        .all()
    )

    report = await session.get(RdReport, job.report_id)
    meta = {
        "title": report.title if report else "",
        "doc_code": job.doc_code,
        "drug_name": job.drug_name,
    }
    output = render_document(template_bytes, build_fills(rows), meta=meta)

    for key in output.unresolved:
        row = next((item for item in rows if item.slot_key == key), None)
        if row is not None:
            row.state = "anchor_unresolved"

    title = _safe_stem(report.title if report else job.document_file_name)
    file_name = f"{title}.docx"
    object_key = store.save_bytes(file_name, output.document, DOCX_CONTENT_TYPE)
    comparison_key = store.save_bytes(
        f"{title}-填充项对照表.md",
        output.comparison_markdown.encode("utf-8"),
        _MARKDOWN_CONTENT_TYPE,
    )

    job.document_file_name = file_name
    job.document_object_key = object_key
    job.comparison_object_key = comparison_key
    job.slot_filled = output.filled
    job.slot_gap = output.gaps

    version = await _append_version(
        session,
        job,
        kind=KIND_MANUAL_RENDER,
        object_key=object_key,
        comparison_object_key=comparison_key,
        file_name=file_name,
        file_size=len(output.document),
        note="按当前填充内容重新渲染",
        user_id=user_id,
    )
    synced = await _sync_deliverable(session, job)
    await session.commit()

    logger.info(
        "report gen rerendered from slots",
        extra={
            "job_id": str(job.id),
            "version_no": version.version_no,
            "filled": output.filled,
            "gaps": output.gaps,
        },
    )
    return ReportGenRenderData(
        version=_to_version_data(version),
        filled=output.filled,
        gaps=output.gaps,
        unresolved=list(output.unresolved),
        synced_deliverable=synced,
    )


async def upload_version(
    session: AsyncSession, job_id: UUID, upload: UploadFile, user_id: UUID | None
) -> ReportGenRenderData:
    """兜底改稿：用户下载 Word 改完再传回来，落一个新版本并置为当前。"""
    if job_id is None:
        raise BadRequestException("缺少生成任务")
    job = await _lock_job(session, job_id)
    if job.status != "completed":
        raise BadRequestException("这次生成还没跑完，等出稿后再上传改稿")

    name = Path(upload.filename or "").name or "report.docx"
    if not name.lower().endswith(".docx"):
        raise BadRequestException("只能上传 .docx 文件；Word 另存为时请选「Word 文档」")

    data = await upload.read()
    if not data:
        raise BadRequestException("上传的文件是空的")
    if len(data) > _MAX_UPLOAD_BYTES:
        raise BadRequestException("文件超过 50MB，请确认没有选错文件")

    object_key = store.save_bytes(name, data, DOCX_CONTENT_TYPE)
    job.document_file_name = name
    job.document_object_key = object_key
    # 对照表描述的是 AI 的填充依据，人工上传的稿子没有新的对照表，沿用上一版

    version = await _append_version(
        session,
        job,
        kind=KIND_MANUAL_UPLOAD,
        object_key=object_key,
        comparison_object_key=job.comparison_object_key,
        file_name=name,
        file_size=len(data),
        note="人工修改后上传",
        user_id=user_id,
    )
    synced = await _sync_deliverable(session, job)
    await session.commit()
    logger.info(
        "report gen version uploaded",
        extra={"job_id": str(job.id), "version_no": version.version_no, "bytes": len(data)},
    )
    return ReportGenRenderData(
        version=_to_version_data(version),
        filled=job.slot_filled,
        gaps=job.slot_gap,
        unresolved=[],
        synced_deliverable=synced,
    )


async def activate_version(session: AsyncSession, version_id: UUID, user_id: UUID | None) -> ReportGenRenderData:
    """把历史版本设为当前：回写任务上的成品键，交付物附件同步跟着换。"""
    version = await session.get(RdReportGenDocumentVersion, version_id)
    if version is None or version.is_deleted:
        raise NotFoundException("文档版本")

    job = await _lock_job(session, version.job_id)
    if job.status != "completed":
        raise BadRequestException("这次生成还没跑完，不能切换版本")

    await session.execute(
        update(RdReportGenDocumentVersion)
        .where(
            RdReportGenDocumentVersion.job_id == job.id,
            RdReportGenDocumentVersion.is_current.is_(True),
        )
        .values(is_current=False)
    )
    version.is_current = True
    version.updated_by = user_id

    job.document_file_name = version.file_name
    job.document_object_key = version.object_key
    if version.comparison_object_key:
        job.comparison_object_key = version.comparison_object_key

    synced = await _sync_deliverable(session, job)
    await session.commit()
    logger.info(
        "report gen version activated",
        extra={"job_id": str(job.id), "version_id": str(version.id), "version_no": version.version_no},
    )
    return ReportGenRenderData(
        version=_to_version_data(version),
        filled=job.slot_filled,
        gaps=job.slot_gap,
        unresolved=[],
        synced_deliverable=synced,
    )


async def version_document_payload(session: AsyncSession, version_id: UUID) -> tuple[str, bytes, str]:
    """按版本取 docx 字节，供预览与下载。"""
    version = await session.get(RdReportGenDocumentVersion, version_id)
    if version is None or version.is_deleted:
        raise NotFoundException("文档版本")
    data = store.load_bytes(str(version.object_key))
    if data is None:
        raise BadRequestException("这一版的文件找不到了，可能已被清理，请重新渲染一次")
    return version.file_name or "report.docx", data, DOCX_CONTENT_TYPE


__all__ = [
    "activate_version",
    "list_versions",
    "record_ai_draft",
    "render_from_slots",
    "upload_version",
    "version_document_payload",
]
