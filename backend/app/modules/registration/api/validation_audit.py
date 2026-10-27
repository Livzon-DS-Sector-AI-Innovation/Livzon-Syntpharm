"""Validation Audit API endpoints."""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory, get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.job_store import JobStore, start_job
from app.core.response import build_response, error_response
from app.modules.registration.schemas.validation_audit import (
    ValidationAuditFileListApiResponse,
    ValidationAuditFileListItem,
    ValidationAuditFileUploadApiResponse,
    ValidationAuditIssueListApiResponse,
    ValidationAuditIssueResponse,
    ValidationAuditMessageApiResponse,
    ValidationAuditReportApiResponse,
    ValidationAuditReportResponse,
    ValidationAuditTaskApiResponse,
    ValidationAuditTaskCreate,
    ValidationAuditTaskListApiResponse,
    ValidationAuditTaskListItem,
    ValidationAuditTaskResponse,
    ValidationAuditTaskUpdate,
)
from app.modules.registration.service.validation_audit import ValidationAuditService

logger = logging.getLogger(__name__)

router = APIRouter()

# 解析/审核后台任务的状态表（进程内，前端轮询 GET /tasks/{task_id} 的任务状态）
_job_store = JobStore()


# ── 任务管理 ──────────────────────────────────────────────


@router.post("/tasks", response_model=ValidationAuditTaskApiResponse, summary="创建审核任务")
async def post(
    current_user: RequiredUser,
    data: ValidationAuditTaskCreate,
    ctx: PermissionContext = Depends(require_permission("registration:validation-audit:create")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = ValidationAuditService(db)
    task = await service.create_task(data)
    return build_response(
        data=ValidationAuditTaskResponse.model_validate(task),
        message="创建成功",
    )


@router.get("/tasks", response_model=ValidationAuditTaskListApiResponse, summary="任务列表")
async def get(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("registration:validation-audit:read")),
    product_name: str | None = Query(None),
    source_company: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = ValidationAuditService(db)
    items, total = await service.list_tasks(
        product_name=product_name,
        source_company=source_company,
        status=status,
        page=page,
        page_size=page_size,
    )
    return build_response(
        data={
            "items": [ValidationAuditTaskListItem.model_validate(i) for i in items],
            "total": total,
        },
        meta={"page": page, "page_size": page_size, "total": total},
        message="获取成功",
    )


@router.get("/tasks/{task_id}", response_model=ValidationAuditTaskApiResponse, summary="任务详情")  # type: ignore[no-redef]
async def get(  # noqa: F811
    current_user: RequiredUser,
    task_id: UUID,
    ctx: PermissionContext = Depends(require_permission("registration:validation-audit:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = ValidationAuditService(db)
    task = await service.get_task(task_id)
    if not task:
        return error_response(message="任务不存在", status_code=404)
    return build_response(
        data=ValidationAuditTaskResponse.model_validate(task),
        message="获取成功",
    )


@router.put("/tasks/{task_id}", response_model=ValidationAuditTaskApiResponse, summary="更新任务")
async def put(
    current_user: RequiredUser,
    task_id: UUID,
    data: ValidationAuditTaskUpdate,
    ctx: PermissionContext = Depends(require_permission("registration:validation-audit:update")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = ValidationAuditService(db)
    task = await service.get_task(task_id)
    if not task:
        return error_response(message="任务不存在", status_code=404)
    updated = await service.update_task(task, data)
    return build_response(
        data=ValidationAuditTaskResponse.model_validate(updated),
        message="更新成功",
    )


@router.delete("/tasks/{task_id}", response_model=ValidationAuditMessageApiResponse, summary="删除任务")
async def delete(
    current_user: RequiredUser,
    task_id: UUID,
    ctx: PermissionContext = Depends(require_permission("registration:validation-audit:delete")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = ValidationAuditService(db)
    task = await service.get_task(task_id)
    if not task:
        return error_response(message="任务不存在", status_code=404)
    await service.delete_task(task)
    return build_response(message="删除成功")


# ── 文件管理 ──────────────────────────────────────────────


@router.post("/tasks/{task_id}/files", response_model=ValidationAuditFileUploadApiResponse, summary="上传文件")  # type: ignore[no-redef]
async def post(  # noqa: F811
    current_user: RequiredUser,
    task_id: UUID,
    ctx: PermissionContext = Depends(require_permission("registration:validation-audit:create")),
    files: list[UploadFile] = File(...),
    file_type: str = Form(...),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """上传审核文件。file_type: protocol / report / attachment"""
    service = ValidationAuditService(db)
    task = await service.get_task(task_id)
    if not task:
        return error_response(message="任务不存在", status_code=404)

    results = []
    for upload_file in files:
        filename = upload_file.filename or "unknown"
        ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        if ext not in ("docx", "pdf"):
            results.append(
                {
                    "filename": filename,
                    "status": "failed",
                    "error": "仅支持 .docx 和 .pdf 格式",
                }
            )
            continue

        try:
            content = await upload_file.read()
            saved = await service.save_uploaded_file(task, filename, content, file_type)
            results.append(
                {
                    "file_id": str(saved.id),
                    "filename": saved.original_filename,
                    "file_size": saved.file_size,  # type: ignore[dict-item]
                    "status": "success",
                }
            )
        except Exception as e:
            logger.exception("文件上传失败: %s", filename)
            results.append(
                {
                    "filename": filename,
                    "status": "failed",
                    "error": str(e),
                }
            )

    return build_response(data=results, message="上传完成")


@router.get("/tasks/{task_id}/files", response_model=ValidationAuditFileListApiResponse, summary="文件列表")  # type: ignore[no-redef]
async def get(  # noqa: F811
    current_user: RequiredUser,
    task_id: UUID,
    ctx: PermissionContext = Depends(require_permission("registration:validation-audit:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = ValidationAuditService(db)
    task = await service.get_task(task_id)
    if not task:
        return error_response(message="任务不存在", status_code=404)
    files = await service.list_files(task_id)
    return build_response(
        data=[ValidationAuditFileListItem.model_validate(f) for f in files],
        message="获取成功",
    )


# ── 解析与审核 ────────────────────────────────────────────


@router.post("/tasks/{task_id}/parse", response_model=ValidationAuditTaskApiResponse, summary="解析文件")  # type: ignore[no-redef]
async def post(  # noqa: F811
    current_user: RequiredUser,
    task_id: UUID,
    ctx: PermissionContext = Depends(require_permission("registration:validation-audit:create")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """提交文件解析后台任务（解析耗时 >5s，不再阻塞请求；前端轮询任务状态）。"""
    service = ValidationAuditService(db)
    task = await service.get_task(task_id)
    if not task:
        return error_response(message="任务不存在", status_code=404)

    # 同步置 parsing，避免前端轮询期出现「后台还没起、状态没变」的竞态
    await service.mark_parsing(task)
    await db.commit()

    async def _run(job_id: str) -> dict[str, Any] | None:
        async with async_session_factory() as job_db:
            job_service = ValidationAuditService(job_db)
            job_task = await job_service.get_task(task_id)
            if not job_task:
                raise RuntimeError("任务不存在")
            await job_service.parse_files(job_task)
            await job_db.commit()
        return None

    start_job(_job_store, "validation-audit-parse", _run)

    task = await service.get_task(task_id)
    return build_response(
        data=ValidationAuditTaskResponse.model_validate(task),
        message="文件解析已开始",
    )


@router.post("/tasks/{task_id}/audit", response_model=ValidationAuditTaskApiResponse, summary="执行审核")  # type: ignore[no-redef]
async def post(  # noqa: F811
    current_user: RequiredUser,
    task_id: UUID,
    ctx: PermissionContext = Depends(require_permission("registration:validation-audit:create")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """提交 AI 审核后台任务（多轮 LLM 调用 >5s，不再阻塞请求；前端轮询任务状态）。"""
    service = ValidationAuditService(db)
    task = await service.get_task(task_id)
    if not task:
        return error_response(message="任务不存在", status_code=404)

    await service.mark_auditing(task)
    await db.commit()

    async def _run(job_id: str) -> dict[str, Any] | None:
        async with async_session_factory() as job_db:
            job_service = ValidationAuditService(job_db)
            job_task = await job_service.get_task(task_id)
            if not job_task:
                raise RuntimeError("任务不存在")
            result = await job_service.run_audit(job_task)
            await job_service.save_issues(job_task, result)
            await job_service.generate_report(job_task, result)
            await job_db.commit()
        return None

    start_job(_job_store, "validation-audit-run", _run)

    task = await service.get_task(task_id)
    return build_response(
        data=ValidationAuditTaskResponse.model_validate(task),
        message="审核已开始",
    )


# ── 问题与报告 ────────────────────────────────────────────


@router.get("/tasks/{task_id}/issues", response_model=ValidationAuditIssueListApiResponse, summary="问题列表")  # type: ignore[no-redef]
async def get(  # noqa: F811
    current_user: RequiredUser,
    task_id: UUID,
    ctx: PermissionContext = Depends(require_permission("registration:validation-audit:read")),
    issue_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = ValidationAuditService(db)
    task = await service.get_task(task_id)
    if not task:
        return error_response(message="任务不存在", status_code=404)
    issues = await service.list_issues(task_id, issue_type=issue_type)
    return build_response(
        data=[ValidationAuditIssueResponse.model_validate(i) for i in issues],
        message="获取成功",
    )


@router.get("/tasks/{task_id}/report", response_model=ValidationAuditReportApiResponse, summary="审核报告")  # type: ignore[no-redef]
async def get(  # noqa: F811
    current_user: RequiredUser,
    task_id: UUID,
    ctx: PermissionContext = Depends(require_permission("registration:validation-audit:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = ValidationAuditService(db)
    task = await service.get_task(task_id)
    if not task:
        return error_response(message="任务不存在", status_code=404)
    report = await service.get_report(task_id)
    if not report:
        return error_response(message="报告尚未生成", status_code=404)
    return build_response(
        data=ValidationAuditReportResponse.model_validate(report),
        message="获取成功",
    )


@router.post("/tasks/{task_id}/export", summary="导出报告")  # type: ignore[no-redef]
async def post(  # noqa: F811
    current_user: RequiredUser,
    task_id: UUID,
    ctx: PermissionContext = Depends(require_permission("registration:validation-audit:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = ValidationAuditService(db)
    task = await service.get_task(task_id)
    if not task:
        return error_response(message="任务不存在", status_code=404)
    report_path = await service.export_report(task_id)
    if not report_path:
        return error_response(message="报告尚未生成", status_code=404)

    import os

    if not os.path.exists(report_path):
        return error_response(message="报告文件不存在", status_code=404)

    return FileResponse(
        path=report_path,
        filename=os.path.basename(report_path),
        media_type="text/markdown",
    )
