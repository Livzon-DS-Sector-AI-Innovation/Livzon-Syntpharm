"""成品文档版本：AI 初稿留档、人工改稿上传、按版本取字节。

职责边界：``service.py`` 顶层 import ``agent``，而 agent 出稿后要记一条 ``ai_draft``
版本；版本逻辑若写进 service 会形成 service ↔ agent 双向依赖。本模块只依赖
models / store，交付物同步用函数内延迟导入。

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
from app.modules.research.models import RdReportGenDocumentVersion, RdReportGenJob
from app.modules.research.report_gen.schemas import (
    ReportGenDocumentVersionData,
    ReportGenDocumentVersionListData,
    ReportGenRenderData,
)

logger = logging.getLogger(__name__)

DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

# 与交付物上传保持同一量级：研发报告正文远小于此，超过基本是传错文件
_MAX_UPLOAD_BYTES = 50 * 1024 * 1024

KIND_AI_DRAFT = "ai_draft"
KIND_MANUAL_UPLOAD = "manual_upload"
KIND_MANUAL_EDIT = "manual_edit"


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


def to_version_data(row: RdReportGenDocumentVersion) -> ReportGenDocumentVersionData:
    """对外暴露的转换：编辑接口要回传新版本，避免调用方再碰私有函数。"""
    return _to_version_data(row)


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
        file_name=file_name,
        file_size=file_size,
        note="AI 生成初稿",
        user_id=None,
    )


async def _sync_deliverable(session: AsyncSession, job: RdReportGenJob) -> bool:
    """把最新成品同步到阶段交付物附件；失败只记日志，不影响改稿本身。"""
    from app.modules.research.deliverable_generation import sync_job_result

    try:
        await sync_job_result(session, job)
    except Exception:  # noqa: BLE001 - 回写是增益项，不能让重渲染整体失败
        logger.exception("report gen rerender: sync deliverable failed", extra={"job_id": str(job.id)})
        return False
    return True


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

    version = await _append_version(
        session,
        job,
        kind=KIND_MANUAL_UPLOAD,
        object_key=object_key,
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


async def current_version_id(session: AsyncSession, job_id: UUID) -> UUID | None:
    """当前版 id：编辑请求带 base_version_id 时用它做并发校验。"""
    result = await session.execute(
        select(RdReportGenDocumentVersion.id).where(
            RdReportGenDocumentVersion.job_id == job_id,
            RdReportGenDocumentVersion.is_current.is_(True),
            RdReportGenDocumentVersion.is_deleted.is_(False),
        )
    )
    return result.scalar()


async def record_manual_edit(
    session: AsyncSession,
    job: RdReportGenJob,
    *,
    data: bytes,
    file_name: str,
    note: str | None,
    user_id: UUID | None,
) -> tuple[RdReportGenDocumentVersion, bool]:
    """站内编辑保存：落新版本、更新任务当前文档、同步交付物。

    不在这里 commit：编辑流水与 slots 要在同一个事务里一起成功，由调用方统一提交。
    """
    object_key = store.save_bytes(file_name, data, DOCX_CONTENT_TYPE)
    job.document_file_name = file_name
    job.document_object_key = object_key
    version = await _append_version(
        session,
        job,
        kind=KIND_MANUAL_EDIT,
        object_key=object_key,
        file_name=file_name,
        file_size=len(data),
        note=note,
        user_id=user_id,
    )
    synced = await _sync_deliverable(session, job)
    return version, synced


async def restore_version(
    session: AsyncSession,
    job_id: UUID,
    version_id: UUID,
    user_id: UUID | None,
    *,
    base_version_id: UUID | None = None,
) -> ReportGenRenderData:
    """回滚到指定版本：用旧版的文件键落一个新版本，历史不被改写。"""
    job = await _lock_job(session, job_id)
    target = await session.get(RdReportGenDocumentVersion, version_id)
    if target is None or target.is_deleted or target.job_id != job.id:
        raise NotFoundException("文档版本")

    current_id = await current_version_id(session, job.id)
    if base_version_id is not None and current_id != base_version_id:
        raise BadRequestException("这一版已经被改过，请刷新后再回滚")

    job.document_file_name = target.file_name
    job.document_object_key = target.object_key
    version = await _append_version(
        session,
        job,
        kind=KIND_MANUAL_EDIT,
        object_key=str(target.object_key),
        file_name=target.file_name,
        file_size=target.file_size,
        note=f"回滚到第 {target.version_no} 版",
        user_id=user_id,
    )
    synced = await _sync_deliverable(session, job)
    await session.commit()
    logger.info(
        "report gen version restored",
        extra={"job_id": str(job.id), "version_no": version.version_no, "from_version": target.version_no},
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
    "KIND_AI_DRAFT",
    "KIND_MANUAL_EDIT",
    "KIND_MANUAL_UPLOAD",
    "current_version_id",
    "list_versions",
    "record_ai_draft",
    "record_manual_edit",
    "restore_version",
    "to_version_data",
    "upload_version",
    "version_document_payload",
]
