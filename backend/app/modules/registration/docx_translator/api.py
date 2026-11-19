"""DOCX 翻译 —— 路由。

前缀：/api/v1/registration/docx-translator
"""

from __future__ import annotations

import asyncio
import logging
from io import BytesIO
from typing import Any
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.database import get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.platform.identity.public_api import resolve_user_names
from app.platform.permission.public_api import has_permission
from app.shared.schemas import DataResponse, MessageApiResponse

from .glossary import GlossaryError, build_excel_terms, parse_excel_terms
from .jobs import get_registry
from .models import SOURCE_IMPORT, SOURCE_MANUAL, DocxTranslationTerm
from .repository import (
    DocxTranslationFileRepository,
    DocxTranslationTaskRepository,
    DocxTranslationTermRepository,
)
from .schemas import (
    DocsTranslationRetranslateResponse,
    DocxGlossaryImportData,
    DocxGlossaryImportResponse,
    DocxGlossaryTermCreate,
    DocxGlossaryTermItemResponse,
    DocxGlossaryTermListData,
    DocxGlossaryTermListResponse,
    DocxGlossaryTermResponse,
    DocxGlossaryTermUpdate,
    DocxTranslationFileListData,
    DocxTranslationFileListResponse,
    DocxTranslationFileRecord,
    DocxTranslationJobAccepted,
    DocxTranslationJobStateResponse,
    DocxTranslationTaskDetailData,
    DocxTranslationTaskDetailResponse,
    DocxTranslationTaskFile,
    DocxTranslationTaskListData,
    DocxTranslationTaskListResponse,
    DocxTranslationTaskRecord,
)
from .service import (
    DOCX_CONTENT_TYPE,
    STORAGE_MODULE,
    UploadedDoc,
    build_job_config,
    delete_file_record,
    delete_task_records,
    find_output,
    get_file_record,
    get_task,
    load_glossary,
    load_limits,
    read_file_object,
    resolve_batch_size,
    run_job,
    sanitize_filename,
    sources_for_retranslate,
    validate_uploads,
)
from .service import (
    run_job as run_translation_job,
)

logger = logging.getLogger(__name__)

router = APIRouter()

PERM_READ = "registration:docx-translator:read"
PERM_CREATE = "registration:docx-translator:create"
PERM_UPDATE = "registration:docx-translator:update"
PERM_DELETE = "registration:docx-translator:delete"

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class DocxTranslationSubmitResponse(DataResponse[DocxTranslationJobAccepted]):
    pass


# ── 翻译任务 ──────────────────────────────────────────────


@router.post("/jobs", response_model=DocxTranslationSubmitResponse, summary="提交文档翻译任务")
async def post(
    current_user: RequiredUser,
    files: list[UploadFile] = File(..., description="待翻译的 Word 文档，可多选"),
    source_lang: str = Form("en", description="源语言: en / zh"),
    target_lang: str = Form("zh", description="目标语言: en / zh"),
    mode: str = Form("bilingual", description="输出模式: bilingual / replace / both"),
    batch_size: int | None = Form(None, description="每批段落数，留空取运行时配置"),
    ctx: PermissionContext = Depends(require_permission(PERM_CREATE)),
    db: AsyncSession = Depends(get_db),
) -> Any:
    max_file_mb, max_files, min_rate = await load_limits()
    uploads: list[UploadedDoc] = []
    for upload in files:
        data = await upload.read()
        uploads.append(UploadedDoc(filename=sanitize_filename(upload.filename or "document.docx"), data=data))
    validate_uploads(uploads, max_file_mb, max_files)

    config = build_job_config(source_lang, target_lang, mode, await resolve_batch_size(batch_size))
    glossary = await load_glossary(db)

    registry = get_registry()
    job_id = registry.start(
        "docx-translation",
        len(uploads),
        lambda jid: run_job(jid, uploads, config, glossary, min_rate, current_user.id),
    )
    logger.info(
        "docx translation job submitted: files=%d mode=%s",
        len(uploads),
        config.mode,
        extra={"job_id": job_id, "biz_module": "registration"},
    )
    return DocxTranslationSubmitResponse(data=DocxTranslationJobAccepted(job_id=job_id))


@router.get("/jobs/{job_id}", response_model=DocxTranslationJobStateResponse, summary="查询翻译任务状态")
async def get(
    current_user: RequiredUser,
    job_id: str,
    ctx: PermissionContext = Depends(require_permission(PERM_READ)),
) -> Any:
    return DocxTranslationJobStateResponse(data=get_registry().state(job_id))


@router.get("/jobs/{job_id}/files/{file_index}", summary="下载翻译结果")
async def download(
    current_user: RequiredUser,
    job_id: str,
    file_index: int,
    ctx: PermissionContext = Depends(require_permission(PERM_READ)),
) -> StreamingResponse:
    output = find_output(get_registry().result(job_id), file_index)
    if output is None:
        raise NotFoundException("翻译结果不存在或任务状态已过期，请重新提交")

    stored = storage.get_object(STORAGE_MODULE, str(output["object_key"]))
    if stored is None:
        raise NotFoundException("翻译结果文件已不可用，请重新提交任务")
    data, _content_type = stored
    filename = str(output["filename"])
    return StreamingResponse(
        BytesIO(data),
        media_type=DOCX_CONTENT_TYPE,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


# ── 任务级历史 ────────────────────────────────────────────


def _task_to_record(
    task: Any,
    *,
    names: dict[Any, str],
    allow_delete_all: bool,
    user_id: Any,
) -> DocxTranslationTaskRecord:
    record = DocxTranslationTaskRecord.model_validate(task, from_attributes=True)
    record.created_by_name = names.get(task.created_by) if task.created_by else None
    record.can_delete = allow_delete_all or task.created_by == user_id
    record.can_retranslate = bool(task.source_keys)
    return record


@router.get("/tasks", response_model=DocxTranslationTaskListResponse, summary="任务级翻译历史")
async def list_tasks(
    current_user: RequiredUser,
    keyword: str | None = Query(None, description="按文件名模糊搜索"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    ctx: PermissionContext = Depends(require_permission(PERM_READ)),
    db: AsyncSession = Depends(get_db),
) -> Any:
    rows, total = await DocxTranslationTaskRepository(db).list_tasks(keyword=keyword, page=page, page_size=page_size)
    names = await resolve_user_names(db, {row.created_by for row in rows if row.created_by})
    allow_delete_all = ctx.is_superuser or await has_permission(db, current_user, PERM_DELETE)
    items = [
        _task_to_record(row, names=names, allow_delete_all=allow_delete_all, user_id=current_user.id) for row in rows
    ]
    return DocxTranslationTaskListResponse(
        data=DocxTranslationTaskListData(
            items=items,
            total=total,
            meta={"page": page, "page_size": page_size, "total": total},
        )
    )


@router.get("/tasks/{task_id}", response_model=DocxTranslationTaskDetailResponse, summary="翻译任务详情")
async def get_task_detail(
    current_user: RequiredUser,
    task_id: UUID,
    ctx: PermissionContext = Depends(require_permission(PERM_READ)),
    db: AsyncSession = Depends(get_db),
) -> Any:
    task = await get_task(db, task_id)
    files = await DocxTranslationFileRepository(db).list_by_job(task.job_ref)
    names = await resolve_user_names(db, {task.created_by} if task.created_by else set())
    allow_delete_all = ctx.is_superuser or await has_permission(db, current_user, PERM_DELETE)
    record = _task_to_record(task, names=names, allow_delete_all=allow_delete_all, user_id=current_user.id)
    record.total_file_size = sum(row.file_size for row in files)
    items = [
        DocxTranslationTaskFile(
            id=row.id,
            source_filename=row.source_filename,
            output_filename=row.output_filename,
            output_kind=row.output_kind,
            success=row.success,
            success_rate=row.success_rate,
            translated_units=row.translated_units,
            total_units=row.total_units,
            file_size=row.file_size,
            error=row.error,
        )
        for row in files
    ]
    return DocxTranslationTaskDetailResponse(data=DocxTranslationTaskDetailData(task=record, files=items))


@router.post(
    "/tasks/{task_id}/retranslate",
    response_model=DocsTranslationRetranslateResponse,
    summary="按原件再次翻译",
)
async def retranslate_task(
    current_user: RequiredUser,
    task_id: UUID,
    ctx: PermissionContext = Depends(require_permission(PERM_CREATE)),
    db: AsyncSession = Depends(get_db),
) -> Any:
    task = await get_task(db, task_id)
    files = await sources_for_retranslate(task)
    config = build_job_config(task.source_lang, task.target_lang, task.mode, task.batch_size)
    glossary = await load_glossary(db)
    _max_mb, _max_files, min_rate = await load_limits()

    registry = get_registry()
    job_id = registry.start(
        "docx-translation",
        len(files),
        lambda jid: run_translation_job(jid, files, config, glossary, min_rate, current_user.id),
    )
    logger.info(
        "docx translation retranslate submitted: from=%s files=%d",
        str(task_id),
        len(files),
        extra={"job_id": job_id, "biz_module": "registration"},
    )
    return DocsTranslationRetranslateResponse(data=DocxTranslationJobAccepted(job_id=job_id))


@router.delete("/tasks/{task_id}", response_model=MessageApiResponse, summary="删除翻译任务")
async def delete_task(
    current_user: RequiredUser,
    task_id: UUID,
    ctx: PermissionContext = Depends(require_permission(PERM_READ)),
    db: AsyncSession = Depends(get_db),
) -> Any:
    task = await get_task(db, task_id)
    allow_delete_all = ctx.is_superuser or await has_permission(db, current_user, PERM_DELETE)
    if not allow_delete_all and task.created_by != current_user.id:
        raise ForbiddenException("只能删除自己创建的翻译任务")
    await delete_task_records(db, task)
    logger.info("docx translation task deleted", extra={"task_id": str(task_id), "biz_module": "registration"})
    return MessageApiResponse(message="删除成功")


# ── 历史产出文件 ──────────────────────────────────────────


@router.get("/files", response_model=DocxTranslationFileListResponse, summary="历史翻译文件列表")
async def list_files(
    current_user: RequiredUser,
    keyword: str | None = Query(None, description="按原文件名或产出文件名模糊搜索"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    ctx: PermissionContext = Depends(require_permission(PERM_READ)),
    db: AsyncSession = Depends(get_db),
) -> Any:
    repo = DocxTranslationFileRepository(db)
    rows, total = await repo.list_files(keyword=keyword, page=page, page_size=page_size)
    names = await resolve_user_names(db, {row.created_by for row in rows if row.created_by})
    # 权限判定只做一次，避免逐行查权限。
    allow_delete_all = ctx.is_superuser or await has_permission(db, current_user, PERM_DELETE)
    items: list[DocxTranslationFileRecord] = []
    for row in rows:
        item = DocxTranslationFileRecord.model_validate(row)
        item.created_by_name = names.get(row.created_by) if row.created_by else None
        item.can_delete = allow_delete_all or row.created_by == current_user.id
        items.append(item)
    return DocxTranslationFileListResponse(
        data=DocxTranslationFileListData(
            items=items,
            total=total,
            meta={"page": page, "page_size": page_size, "total": total},
        )
    )


@router.get("/files/{file_id}/download", summary="下载历史翻译文件")
async def download_file(
    current_user: RequiredUser,
    file_id: UUID,
    ctx: PermissionContext = Depends(require_permission(PERM_READ)),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    record = await get_file_record(db, file_id)
    data = await asyncio.to_thread(read_file_object, record)
    if data is None:
        raise NotFoundException("译文文件已被清理，无法下载")
    return StreamingResponse(
        BytesIO(data),
        media_type=DOCX_CONTENT_TYPE,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(record.output_filename)}"},
    )


@router.delete("/files/{file_id}", response_model=MessageApiResponse, summary="删除历史翻译文件")
async def delete_file(
    current_user: RequiredUser,
    file_id: UUID,
    ctx: PermissionContext = Depends(require_permission(PERM_READ)),
    db: AsyncSession = Depends(get_db),
) -> Any:
    record = await get_file_record(db, file_id)
    allow_delete_all = ctx.is_superuser or await has_permission(db, current_user, PERM_DELETE)
    if not allow_delete_all and record.created_by != current_user.id:
        raise ForbiddenException("只能删除自己创建的翻译文件")
    await delete_file_record(db, record)
    logger.info(
        "docx translation file deleted",
        extra={"file_id": str(file_id), "biz_module": "registration"},
    )
    return MessageApiResponse(message="删除成功")


# ── 术语表 ────────────────────────────────────────────────


@router.get("/glossary", response_model=DocxGlossaryTermListResponse, summary="术语表列表")
async def list_terms(
    current_user: RequiredUser,
    keyword: str | None = Query(None, description="按英文或中文模糊搜索"),
    enabled: bool | None = Query(None, description="仅看启用/停用"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    ctx: PermissionContext = Depends(require_permission(PERM_READ)),
    db: AsyncSession = Depends(get_db),
) -> Any:
    repo = DocxTranslationTermRepository(db)
    rows, total = await repo.list_terms(keyword=keyword, enabled=enabled, page=page, page_size=page_size)
    return DocxGlossaryTermListResponse(
        data=DocxGlossaryTermListData(
            items=[DocxGlossaryTermResponse.model_validate(row) for row in rows],
            total=total,
            meta={"page": page, "page_size": page_size, "total": total},
        )
    )


@router.post("/glossary", response_model=DocxGlossaryTermItemResponse, summary="新增术语")
async def create_term(
    current_user: RequiredUser,
    payload: DocxGlossaryTermCreate,
    ctx: PermissionContext = Depends(require_permission(PERM_CREATE)),
    db: AsyncSession = Depends(get_db),
) -> Any:
    repo = DocxTranslationTermRepository(db)
    term_en = payload.term_en.strip()
    if await repo.get_by_en(term_en):
        raise BadRequestException(f"术语已存在：{term_en}")
    term = DocxTranslationTerm(
        term_en=term_en,
        term_en_lower=term_en.lower(),
        term_zh=payload.term_zh.strip(),
        is_enabled=payload.is_enabled,
        source=SOURCE_MANUAL,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    saved = await repo.create(term)
    return DocxGlossaryTermItemResponse(data=DocxGlossaryTermResponse.model_validate(saved))


@router.put("/glossary/{term_id}", response_model=DocxGlossaryTermItemResponse, summary="更新术语")
async def update_term(
    current_user: RequiredUser,
    term_id: UUID,
    payload: DocxGlossaryTermUpdate,
    ctx: PermissionContext = Depends(require_permission(PERM_UPDATE)),
    db: AsyncSession = Depends(get_db),
) -> Any:
    repo = DocxTranslationTermRepository(db)
    term = await repo.get(term_id)
    if term is None:
        raise NotFoundException("术语不存在")

    if payload.term_en is not None:
        new_en = payload.term_en.strip()
        existing = await repo.get_by_en(new_en)
        if existing is not None and existing.id != term.id:
            raise BadRequestException(f"术语已存在：{new_en}")
        term.term_en = new_en
        term.term_en_lower = new_en.lower()
    if payload.term_zh is not None:
        term.term_zh = payload.term_zh.strip()
    if payload.is_enabled is not None:
        term.is_enabled = payload.is_enabled
    term.updated_by = current_user.id
    saved = await repo.save(term)
    return DocxGlossaryTermItemResponse(data=DocxGlossaryTermResponse.model_validate(saved))


@router.delete("/glossary/{term_id}", response_model=MessageApiResponse, summary="删除术语")
async def delete_term(
    current_user: RequiredUser,
    term_id: UUID,
    ctx: PermissionContext = Depends(require_permission(PERM_DELETE)),
    db: AsyncSession = Depends(get_db),
) -> Any:
    repo = DocxTranslationTermRepository(db)
    term = await repo.get(term_id)
    if term is None:
        raise NotFoundException("术语不存在")
    term.is_deleted = True
    term.updated_by = current_user.id
    await repo.save(term)
    return MessageApiResponse(message="删除成功")


@router.post("/glossary/import", response_model=DocxGlossaryImportResponse, summary="导入术语表 xlsx")
async def import_terms(
    current_user: RequiredUser,
    file: UploadFile = File(..., description="xlsx，列名须为「英文」「中文」"),
    ctx: PermissionContext = Depends(require_permission(PERM_CREATE)),
    db: AsyncSession = Depends(get_db),
) -> Any:
    data = await file.read()
    try:
        rows = parse_excel_terms(data)
    except GlossaryError as e:
        raise BadRequestException(str(e)) from e

    repo = DocxTranslationTermRepository(db)
    imported = 0
    updated = 0
    skipped = 0
    seen: set[str] = set()
    for en, zh in rows:
        key = en.strip().lower()
        if key in seen:
            skipped += 1
            continue
        seen.add(key)
        existing = await repo.get_by_en(en)
        if existing is None:
            db.add(
                DocxTranslationTerm(
                    term_en=en.strip(),
                    term_en_lower=key,
                    term_zh=zh.strip(),
                    is_enabled=True,
                    source=SOURCE_IMPORT,
                    created_by=current_user.id,
                    updated_by=current_user.id,
                )
            )
            imported += 1
        else:
            if existing.term_zh != zh.strip():
                existing.term_zh = zh.strip()
                existing.updated_by = current_user.id
                updated += 1
            else:
                skipped += 1
    await db.commit()
    logger.info(
        "docx glossary imported: imported=%d updated=%d skipped=%d",
        imported,
        updated,
        skipped,
        extra={"biz_module": "registration"},
    )
    return DocxGlossaryImportResponse(
        data=DocxGlossaryImportData(imported=imported, updated=updated, skipped=skipped, total=len(rows))
    )


@router.get("/glossary/export", summary="导出术语表 xlsx")
async def export_terms(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_READ)),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    repo = DocxTranslationTermRepository(db)
    rows = await repo.list_all()
    content = build_excel_terms([(row.term_en, row.term_zh) for row in rows])
    return StreamingResponse(
        BytesIO(content),
        media_type=XLSX_CONTENT_TYPE,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote('术语表.xlsx')}"},
    )
