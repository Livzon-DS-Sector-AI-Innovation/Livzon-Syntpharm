"""项目知识库业务逻辑：本地记录与 RAGFlow 数据集之间的两向同步。

同步方向与真相来源：

- **资料本体与解析结果**：真相在 RAGFlow。本地只镜像状态，每次列表查询都回源对账，
  因此 RAGFlow 重启、解析进度推进、文档被外部删除都能自然收敛，不需要额外的定时任务。
- **库与项目的关联**：真相在本地 ``research.rd_knowledge_bases``，RAGFlow 侧只存名字与描述。

外部服务不可用时的降级：读路径（列表/详情）返回本地镜像并标注 last_error，
写路径（上传/删除）直接报错——写操作静默失败会让两侧数据长期不一致。
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import mimetypes
import uuid
from collections.abc import Awaitable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BadRequestException, NotFoundException
from app.modules.research import models as rd_models
from app.modules.research.knowledge_base.models import DOC_RUN_VALUES, RdKbDocument, RdKnowledgeBase
from app.modules.research.knowledge_base.ragflow import RagflowClient, RagflowError
from app.shared.file_conversion import get_file_conversion

logger = logging.getLogger(__name__)

# 可提交给 RAGFlow 解析的扩展名（与 RAGFlow 内置解析器能力对齐）
ALLOWED_EXTENSIONS = frozenset(
    {
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".csv",
        ".txt",
        ".md",
        ".markdown",
        ".json",
        ".html",
        ".htm",
        ".png",
        ".jpg",
        ".jpeg",
        ".bmp",
        ".tif",
        ".tiff",
        ".webp",
    }
)
MAX_FILES_PER_UPLOAD = 10
MAX_FILE_MB = 100


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------


async def _remote_call(action: str, awaitable: Awaitable[Any]) -> Any:
    """执行一次远端调用，把 RagflowError 统一转成带动作前缀的业务异常。

    读路径要让用户看懂「哪一步失败 + 远端说了什么」，写路径不允许静默失败；
    各方法都照同一格式拼异常，集中在这里避免各写一遍。
    """
    try:
        return await awaitable
    except RagflowError as exc:
        raise BadRequestException(f"{action}：{exc.message}") from exc


# ---------------------------------------------------------------------------
# 查询
# ---------------------------------------------------------------------------


async def get_knowledge_base(session: AsyncSession, kb_id: uuid.UUID) -> RdKnowledgeBase:
    kb = await session.get(RdKnowledgeBase, kb_id)
    if kb is None or kb.is_deleted:
        raise NotFoundException("知识库")
    return kb


async def get_project_knowledge_base(session: AsyncSession, project_id: uuid.UUID) -> RdKnowledgeBase | None:
    """项目当前有效的知识库（一个项目至多一个）。"""
    result = await session.execute(
        select(RdKnowledgeBase)
        .where(
            RdKnowledgeBase.project_id == project_id,
            RdKnowledgeBase.is_deleted.is_(False),
        )
        .order_by(RdKnowledgeBase.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_knowledge_bases(
    session: AsyncSession, *, project_id: uuid.UUID | None = None
) -> list[tuple[RdKnowledgeBase, str]]:
    """知识库列表（附带项目名），供列表页一次取全。"""
    query = (
        select(RdKnowledgeBase, rd_models.RdProject.name)
        .join(rd_models.RdProject, rd_models.RdProject.id == RdKnowledgeBase.project_id)
        .where(RdKnowledgeBase.is_deleted.is_(False))
        .order_by(RdKnowledgeBase.created_at.desc())
    )
    if project_id is not None:
        query = query.where(RdKnowledgeBase.project_id == project_id)
    rows = await session.execute(query)
    return [(row[0], row[1] or "") for row in rows.all()]


async def load_documents(session: AsyncSession, kb_id: uuid.UUID) -> list[RdKbDocument]:
    result = await session.execute(
        select(RdKbDocument)
        .where(RdKbDocument.kb_id == kb_id, RdKbDocument.is_deleted.is_(False))
        .order_by(RdKbDocument.created_at.asc())
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# 建库 / 删库
# ---------------------------------------------------------------------------


async def create_knowledge_base(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    name: str = "",
    description: str = "",
    embedding_model: str = "",
    chunk_method: str = "",
    user_id: uuid.UUID | None = None,
) -> RdKnowledgeBase:
    """为一个研发项目创建知识库：先在 RAGFlow 建数据集，再落本地映射。"""
    project = await session.get(rd_models.RdProject, project_id)
    if project is None or project.is_deleted:
        raise NotFoundException("研发项目")

    existing = await get_project_knowledge_base(session, project_id)
    if existing is not None:
        raise BadRequestException("该项目已关联知识库，请直接进入知识库页面使用")

    settings = get_settings().ragflow
    if not (settings.base_url and settings.api_key):
        raise BadRequestException("知识库服务未配置，请联系管理员设置 RAGFLOW__BASE_URL 与 RAGFLOW__API_KEY")

    display_name = name.strip() or f"{project.name}-项目知识库"
    client = RagflowClient()
    dataset = await _remote_call(
        "创建知识库失败",
        client.create_dataset(
            display_name,
            description=description.strip() or f"研发项目「{project.name}」的项目知识库",
            embedding_model=embedding_model,
            chunk_method=chunk_method,
        ),
    )

    kb = RdKnowledgeBase(
        project_id=project_id,
        name=display_name,
        description=description.strip() or None,
        provider="ragflow",
        ragflow_dataset_id=str(dataset.get("id") or ""),
        # RAGFlow 的 embedding_model 可能是模型名（我们创建时传的值），
        # embedding_model_name 是列表接口联表解析出的可读名；两者都缺才回退部署配置
        embedding_model=str(
            dataset.get("embedding_model_name")
            or dataset.get("embedding_model")
            or settings.default_embedding_model
            or ""
        ),
        chunk_method=str(dataset.get("chunk_method") or settings.default_chunk_method),
        parser_config=dataset.get("parser_config") if isinstance(dataset.get("parser_config"), dict) else None,
        status="active",
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(kb)
    await session.flush()
    logger.info(
        "项目知识库已创建",
        extra={
            "kb_id": str(kb.id),
            "project_id": str(project_id),
            "dataset_id": kb.ragflow_dataset_id,
            "module_name": "research",
        },
    )
    return kb


async def delete_knowledge_base(session: AsyncSession, kb_id: uuid.UUID, *, user_id: uuid.UUID | None = None) -> None:
    """删除知识库：远端数据集删除失败不阻断本地清理（避免脏映射卡住重建）。"""
    kb = await get_knowledge_base(session, kb_id)
    if kb.ragflow_dataset_id:
        try:
            await RagflowClient().delete_datasets([kb.ragflow_dataset_id])
        except RagflowError as exc:
            # 远端已不存在或服务不可用：本地照删，只记录，避免用户被卡住
            logger.warning(
                "删除知识库远端数据集失败，仅清理本地映射",
                extra={"kb_id": str(kb.id), "dataset_id": kb.ragflow_dataset_id, "error": exc.message},
            )
            kb.last_error = f"远端数据集删除失败：{exc.message}"
    for row in await load_documents(session, kb.id):
        row.is_deleted = True
        row.updated_by = user_id
    kb.is_deleted = True
    kb.updated_by = user_id
    await session.flush()


# ---------------------------------------------------------------------------
# 文档上传与状态同步
# ---------------------------------------------------------------------------


def _apply_remote(row: RdKbDocument, item: dict[str, Any], now: datetime) -> None:
    """把 RAGFlow 文档对象写回本地镜像行。"""
    run = str(item.get("run") or "UNSTART").upper()
    row.run_status = run if run in DOC_RUN_VALUES else "UNSTART"
    try:
        row.progress = max(0.0, min(1.0, float(item.get("progress") or 0.0)))
    except (TypeError, ValueError):
        row.progress = 0.0
    progress_msg = item.get("progress_msg")
    row.progress_msg = str(progress_msg)[-4000:] if progress_msg else None
    row.chunk_count = int(item.get("chunk_count") or 0)
    row.token_count = int(item.get("token_count") or 0)
    if item.get("name"):
        row.file_name = str(item["name"])
    if item.get("size") is not None:
        try:
            row.size_bytes = int(item["size"])
        except (TypeError, ValueError):
            pass
    if row.run_status == "DONE":
        row.progress = 1.0
        row.last_error = None
        row.parsed_at = row.parsed_at or now
    elif row.run_status == "FAIL":
        row.last_error = (row.progress_msg or "解析失败")[-1000:]
        row.parsed_at = now
    elif row.run_status == "CANCEL":
        row.parsed_at = now


async def sync_documents(
    session: AsyncSession, kb: RdKnowledgeBase, *, client: RagflowClient | None = None
) -> list[RdKbDocument]:
    """回源 RAGFlow 对账：补齐新文档、刷新进度、更新库计数。

    回源失败时降级为返回本地镜像（读路径不因外部服务抖动而不可用）。
    """
    client = client or RagflowClient()
    now = datetime.now(UTC)
    try:
        remote = await client.list_documents(kb.ragflow_dataset_id) if kb.ragflow_dataset_id else []
        detail = await client.get_dataset(kb.ragflow_dataset_id) if kb.ragflow_dataset_id else {}
    except RagflowError as exc:
        kb.last_error = exc.message
        logger.warning("知识库状态同步失败，返回本地镜像", extra={"kb_id": str(kb.id), "error": exc.message})
        return await load_documents(session, kb.id)

    local = {row.ragflow_document_id: row for row in await load_documents(session, kb.id)}
    for item in remote:
        doc_id = str(item.get("id") or "")
        if not doc_id:
            continue
        row = local.get(doc_id)
        if row is None:
            row = RdKbDocument(
                kb_id=kb.id,
                ragflow_document_id=doc_id,
                file_name=str(item.get("name") or doc_id),
                file_ext=Path(str(item.get("name") or "")).suffix.lower(),
            )
            session.add(row)
            local[doc_id] = row
        _apply_remote(row, item, now)

    kb.document_count = int(detail.get("document_count") or len(remote))
    kb.chunk_count = int(detail.get("chunk_count") or 0)
    kb.token_count = int(detail.get("token_count") or 0)
    kb.last_synced_at = now
    kb.last_error = None
    await session.flush()
    return await load_documents(session, kb.id)


async def upload_documents(
    session: AsyncSession,
    kb: RdKnowledgeBase,
    files: list[UploadFile],
    *,
    user_id: uuid.UUID | None = None,
) -> tuple[list[str], list[dict[str, str]], list[RdKbDocument]]:
    """上传资料到知识库并立即触发解析。

    返回 (成功文件名, 跳过项, 刷新后的文档列表)。单个文件失败不影响其余文件，
    逐份读取上传以避免一次性把所有文件读进内存。
    """
    if kb.status != "active" or not kb.ragflow_dataset_id:
        raise BadRequestException("知识库尚未就绪，无法上传资料")
    if not files:
        raise BadRequestException("请选择要上传的文件")
    if len(files) > MAX_FILES_PER_UPLOAD:
        raise BadRequestException(f"单次最多上传 {MAX_FILES_PER_UPLOAD} 个文件")

    client = RagflowClient()
    uploaded: list[str] = []
    skipped: list[dict[str, str]] = []
    new_doc_ids: list[str] = []
    now = datetime.now(UTC)

    for upload in files:
        name = (upload.filename or "").strip() or "未命名文件"
        ext = Path(name).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            skipped.append({"file_name": name, "reason": f"不支持的文件类型（{ext or '无扩展名'}）"})
            continue
        content = await upload.read()
        if not content:
            skipped.append({"file_name": name, "reason": "文件内容为空"})
            continue
        if len(content) > MAX_FILE_MB * 1024 * 1024:
            skipped.append({"file_name": name, "reason": f"超过 {MAX_FILE_MB}MB 上限"})
            continue
        try:
            created = await client.upload_document(
                kb.ragflow_dataset_id, name, content, upload.content_type or "application/octet-stream"
            )
        except RagflowError as exc:
            skipped.append({"file_name": name, "reason": f"上传到知识库服务失败：{exc.message}"})
            continue
        doc_ids = [str(item.get("id") or "") for item in created if item.get("id")]
        if not doc_ids:
            skipped.append({"file_name": name, "reason": "知识库服务未返回文档 ID"})
            continue
        digest = hashlib.sha256(content).hexdigest()
        for doc_id in doc_ids:
            session.add(
                RdKbDocument(
                    kb_id=kb.id,
                    ragflow_document_id=doc_id,
                    file_name=name,
                    file_ext=ext,
                    size_bytes=len(content),
                    sha256=digest,
                    run_status="UNSTART",
                    parse_started_at=now,
                    created_by=user_id,
                    updated_by=user_id,
                )
            )
        new_doc_ids.extend(doc_ids)
        uploaded.append(name)

    await session.flush()

    if new_doc_ids:
        try:
            await client.parse_documents(kb.ragflow_dataset_id, new_doc_ids)
        except RagflowError as exc:
            # 解析未触发：文件已入库，用户可稍后在列表里点「重新解析」
            logger.warning(
                "知识库解析触发失败，等待人工重试",
                extra={"kb_id": str(kb.id), "documents": len(new_doc_ids), "error": exc.message},
            )
            skipped.append({"file_name": f"（{len(new_doc_ids)} 份文件）", "reason": f"解析触发失败：{exc.message}"})

    documents = await sync_documents(session, kb, client=client)
    return uploaded, skipped, documents


async def delete_document(
    session: AsyncSession, kb: RdKnowledgeBase, document_row_id: uuid.UUID, *, user_id: uuid.UUID | None = None
) -> list[RdKbDocument]:
    """删除知识库中的一份文档（远端删除成功后才软删本地记录）。"""
    row = await session.get(RdKbDocument, document_row_id)
    if row is None or row.is_deleted or row.kb_id != kb.id:
        raise NotFoundException("文档")
    if kb.ragflow_dataset_id:
        await _remote_call(
            "删除失败",
            RagflowClient().delete_documents(kb.ragflow_dataset_id, [row.ragflow_document_id]),
        )
    row.is_deleted = True
    row.updated_by = user_id
    await session.flush()
    return await sync_documents(session, kb)


async def reparse_document(
    session: AsyncSession, kb: RdKnowledgeBase, document_row_id: uuid.UUID
) -> list[RdKbDocument]:
    """重新解析一份文档（清空旧切片后重跑，用于解析失败或资料更新）。"""
    row = await session.get(RdKbDocument, document_row_id)
    if row is None or row.is_deleted or row.kb_id != kb.id:
        raise NotFoundException("文档")
    if not kb.ragflow_dataset_id:
        raise BadRequestException("知识库尚未就绪，无法重新解析")
    await _remote_call(
        "重新解析失败",
        RagflowClient().parse_documents(kb.ragflow_dataset_id, [row.ragflow_document_id]),
    )
    row.run_status = "RUNNING"
    row.progress = 0.0
    row.last_error = None
    row.parsed_at = None
    row.parse_started_at = datetime.now(UTC)
    await session.flush()
    return await sync_documents(session, kb)


# ---------------------------------------------------------------------------
# 预览 / 下载（原文与解析内容）
# ---------------------------------------------------------------------------


async def get_document(session: AsyncSession, kb_id: uuid.UUID, document_row_id: uuid.UUID) -> RdKbDocument:
    """取本知识库下的一份文档记录（校验归属，避免跨库读取）。"""
    row = await session.get(RdKbDocument, document_row_id)
    if row is None or row.is_deleted or row.kb_id != kb_id:
        raise NotFoundException("文档")
    return row


def _require_dataset(kb: RdKnowledgeBase) -> str:
    if kb.status != "active" or not kb.ragflow_dataset_id:
        raise BadRequestException("知识库尚未就绪，无法查看资料")
    return kb.ragflow_dataset_id


async def document_file(kb: RdKnowledgeBase, row: RdKbDocument, *, as_pdf: bool = False) -> tuple[bytes, str]:
    """取资料原件字节流与 MIME（预览与下载共用一次实现）。

    文件本体只存在 RAGFlow，这里按其文档详情端点回源，本地不落副本。

    ``as_pdf=True`` 时把 Office 文档（.doc/.docx/.xls(x)/.ppt(x)）转成 PDF 再返回：
    浏览器只能原生渲染 pdf/图片/纯文本，这类格式直接内联只会触发下载。
    转换失败自动回退原件，由前端按实际 MIME 决定展示方式。
    """
    dataset_id = _require_dataset(kb)
    if not row.ragflow_document_id:
        raise BadRequestException("该资料尚未同步到知识库服务，无法获取文件")
    content, content_type, _ = await _remote_call(
        "获取资料文件失败",
        RagflowClient().download_document(dataset_id, row.ragflow_document_id),
    )
    # RAGFlow 多数情况下回正确的 MIME；异常时按本地记录的扩展名兜底
    if not content_type or content_type == "application/octet-stream":
        content_type = mimetypes.guess_type(row.file_name or "")[0] or content_type
    content_type = content_type or "application/octet-stream"

    if as_pdf and content_type != "application/pdf":
        # LibreOffice 调用是阻塞的，放线程池里跑，别占住事件循环
        pdf = await asyncio.to_thread(get_file_conversion().convert_bytes_to_pdf, content, row.file_name)
        if pdf:
            return pdf, "application/pdf"
        logger.warning("资料转 PDF 失败，回退为原件", extra={"file_name": row.file_name, "module_name": "research"})
    return content, content_type


async def document_chunks(
    kb: RdKnowledgeBase, row: RdKbDocument, *, page: int = 1, page_size: int = 50
) -> dict[str, Any]:
    """解析切片分页（预览「解析内容」；docx/xls 等无法在浏览器直接渲染时靠它看内容）。"""
    dataset_id = _require_dataset(kb)
    if not row.ragflow_document_id:
        raise BadRequestException("该资料尚未同步到知识库服务，无法查看解析内容")
    total, chunks = await _remote_call(
        "获取解析内容失败",
        RagflowClient().list_document_chunks(dataset_id, row.ragflow_document_id, page=page, page_size=page_size),
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [chunk_payload(chunk) for chunk in chunks],
    }


async def document_image(kb: RdKnowledgeBase, image_id: str) -> tuple[bytes, str]:
    """取切片关联的图片（PDF 页图 / 图注配图）。

    RAGFlow 的取图端点只按 ``{dataset_id}-{对象名}`` 拆桶取对象、**不校验库归属**，
    所以这里必须自己校验前缀，否则拼一个别的数据集 ID 就能读到别人的图。
    """
    dataset_id = _require_dataset(kb)
    if not image_id or not image_id.startswith(f"{dataset_id}-"):
        raise NotFoundException("图片")
    content, content_type = await _remote_call(
        "获取图片失败",
        RagflowClient().download_image(image_id),
    )
    if not content:
        raise NotFoundException("图片")
    return content, content_type


def chunk_payload(chunk: dict[str, Any]) -> dict[str, Any]:
    """RAGFlow 切片 → 前端展示字段（docnm_kwd 是它给文档名的字段名）。"""
    positions = chunk.get("positions")
    return {
        "id": str(chunk.get("id") or ""),
        "content": str(chunk.get("content") or ""),
        "positions": positions if isinstance(positions, list) else [],
        "document_keyword": str(chunk.get("docnm_kwd") or ""),
        "image_id": str(chunk.get("image_id") or ""),
        "available": bool(chunk.get("available", True)),
    }


# ---------------------------------------------------------------------------
# 响应装配
# ---------------------------------------------------------------------------


def document_payload(row: RdKbDocument) -> dict[str, Any]:
    return {
        "id": row.id,
        "ragflow_document_id": row.ragflow_document_id,
        "file_name": row.file_name,
        "file_ext": row.file_ext,
        "size_bytes": row.size_bytes,
        "run": row.run_status,
        "progress": row.progress,
        "progress_msg": row.progress_msg or "",
        "chunk_count": row.chunk_count,
        "token_count": row.token_count,
        "last_error": row.last_error or "",
        "parse_started_at": row.parse_started_at,
        "parsed_at": row.parsed_at,
        "created_at": row.created_at,
    }


def knowledge_base_payload(
    kb: RdKnowledgeBase, project_name: str = "", documents: list[RdKbDocument] | None = None
) -> dict[str, Any]:
    docs = documents or []
    return {
        "id": kb.id,
        "project_id": kb.project_id,
        "project_name": project_name,
        "name": kb.name,
        "description": kb.description or "",
        "provider": kb.provider,
        "ragflow_dataset_id": kb.ragflow_dataset_id,
        "embedding_model": kb.embedding_model or "",
        "chunk_method": kb.chunk_method,
        "status": kb.status,
        "last_error": kb.last_error or "",
        "document_count": kb.document_count,
        "chunk_count": kb.chunk_count,
        "token_count": kb.token_count,
        "parsed_count": sum(1 for d in docs if d.run_status == "DONE"),
        "parsing_count": sum(1 for d in docs if d.run_status in ("UNSTART", "RUNNING")),
        "failed_count": sum(1 for d in docs if d.run_status in ("FAIL", "CANCEL")),
        "last_synced_at": kb.last_synced_at,
        "created_at": kb.created_at,
    }


async def limits() -> dict[str, Any]:
    """上传前校验用的限制（含服务是否已配置，供前端提前提示）。"""
    settings = get_settings().ragflow
    return {
        "max_files": MAX_FILES_PER_UPLOAD,
        "max_file_mb": MAX_FILE_MB,
        "allowed_extensions": sorted(ALLOWED_EXTENSIONS),
        "configured": bool(settings.base_url and settings.api_key),
        "provider": "ragflow",
    }
