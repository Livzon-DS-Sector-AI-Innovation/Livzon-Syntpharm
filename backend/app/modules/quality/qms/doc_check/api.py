"""Doc Check（文档校验）API 路由

挂载前缀：/api/v1/quality
- 操作人一律取登录态 current_user，不接受客户端传入
- 结构化响应统一走 build_response + 具体 response_model（禁止 response_model=dict）
- 错误统一抛 app/core/exceptions.py 中的业务异常
"""

import logging
from html import escape
from typing import Any

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory, get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.exceptions import BadRequestException
from app.core.job_store import JobStore, start_job
from app.core.response import build_response
from app.modules.quality.qms.doc_check.schemas import (
    DocCheckApiResponse,
    DocCheckBatchApiResponse,
    DocCheckBatchCreate,
    DocCheckBatchResponse,
    DocCheckConfigApiResponse,
    DocCheckConfigCreate,
    DocCheckConfigListApiResponse,
    DocCheckConfigResponse,
    DocCheckConfigUpdate,
    DocCheckConfirmApiResponse,
    DocCheckConfirmResponse,
    DocCheckCreate,
    DocCheckDetailApiResponse,
    DocCheckDetailResponse,
    DocCheckExecuteRequest,
    DocCheckExportApiResponse,
    DocCheckExportResponse,
    DocCheckListApiResponse,
    DocCheckProgressApiResponse,
    DocCheckProgressResponse,
    DocCheckResponse,
    DocCheckTaskApiResponse,
    DocCheckTaskResponse,
    DocCheckUpdate,
    DocCheckUploadApiResponse,
    DocCheckUploadProgressApiResponse,
    DocCheckUploadProgressResponse,
    DocCheckUploadResponse,
    MessageApiResponse,
    ProblemApiResponse,
    ProblemBatchApiResponse,
    ProblemBatchResult,
    ProblemBatchUpdate,
    ProblemListApiResponse,
    ProblemResponse,
    ProblemUpdate,
)
from app.modules.quality.qms.doc_check.service import (
    DocCheckService,
    load_upload_bytes,
    store_upload,
)
from app.modules.quality.sop_ai.models import SopAiCheckMain

logger = logging.getLogger(__name__)

router = APIRouter()

_JOB_STORE = JobStore()
_MAX_UPLOAD_BYTES = 20 * 1024 * 1024
_UPLOAD_CHUNK = 1024 * 1024

_PROGRESS_BY_STATUS: dict[str, int] = {
    "pending": 0,
    "running": 50,
    "completed": 100,
    "failed": 100,
    "cancelled": 0,
}
_STEP_BY_STATUS: dict[str, str] = {
    "pending": "等待执行",
    "running": "AI 正在审核文档",
    "completed": "审核完成",
    "failed": "校验失败，可重新执行",
    "cancelled": "任务已取消",
}


def _status_of(check: Any) -> str:
    """状态统一为小写字符串。"""
    return str(getattr(check, "status", "") or "").lower()


def _operator_of(current_user: Any) -> str | None:
    """操作人取登录态，缺省回退到姓名。"""
    return getattr(current_user, "username", None) or getattr(current_user, "name", None)


def _render_report_html(check: SopAiCheckMain, problems: list[ProblemResponse]) -> str:
    """渲染审核报告 HTML，所有字段均转义，避免文档内容注入脚本。"""
    rows = "".join(
        "<tr>"
        f"<td>{index}</td>"
        f"<td>{escape(item.problem_type or '')}</td>"
        f"<td>{escape(item.risk_level or '')}</td>"
        f"<td>{escape(item.location or '')}</td>"
        f"<td>{escape(item.description or '')}</td>"
        f"<td>{escape(item.suggestion or '')}</td>"
        f"<td>{escape(item.handle_status or '')}</td>"
        "</tr>"
        for index, item in enumerate(problems, start=1)
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<title>文档校验报告 - {escape(check.file_name or check.file_code or check.id)}</title>
<style>
body {{ font-family: sans-serif; margin: 24px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ccc; padding: 6px 8px; font-size: 13px; vertical-align: top; }}
th {{ background: #f5f5f5; }}
</style>
</head>
<body>
<h1>文档校验报告 - {escape(check.file_name or check.file_code or check.id)}</h1>
<p>文件编号：{escape(check.file_code or "-")}</p>
<p>文件类型：{escape(check.file_type or "-")}</p>
<p>校验状态：{escape(_status_of(check))}</p>
<p>问题总数：{len(problems)}（高 {check.risk_high} / 中 {check.risk_medium} / 低 {check.risk_low}）</p>
<p>总体结论：{escape(check.result_summary or "-")}</p>
<table>
<thead>
<tr><th>#</th><th>问题类型</th><th>风险等级</th><th>位置</th><th>问题描述</th><th>整改建议</th><th>处理状态</th></tr>
</thead>
<tbody>{rows}</tbody>
</table>
</body>
</html>"""


# ============ 配置 ============


@router.get("/config", response_model=DocCheckConfigListApiResponse, summary="获取文档校验配置列表")
async def list_configs(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("quality:doc-check:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    configs = await DocCheckService(db).get_configs()
    return build_response(data=[DocCheckConfigResponse.model_validate(item) for item in configs])


@router.post("/config", response_model=DocCheckConfigApiResponse, summary="新增文档校验配置")
async def create_config(
    payload: DocCheckConfigCreate,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("quality:doc-check:create")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    config = await DocCheckService(db).create_config(payload, _operator_of(current_user))
    await db.commit()
    return build_response(data=DocCheckConfigResponse.model_validate(config), message="配置创建成功")


@router.get("/config/{config_id}", response_model=DocCheckConfigApiResponse, summary="获取文档校验配置详情")
async def get_config(
    config_id: str,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("quality:doc-check:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    config = await DocCheckService(db).get_config(config_id)
    return build_response(data=DocCheckConfigResponse.model_validate(config))


@router.put("/config/{config_id}", response_model=DocCheckConfigApiResponse, summary="修改文档校验配置")
async def update_config(
    config_id: str,
    payload: DocCheckConfigUpdate,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("quality:doc-check:update")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    config = await DocCheckService(db).update_config(config_id, payload, _operator_of(current_user))
    await db.commit()
    return build_response(data=DocCheckConfigResponse.model_validate(config), message="配置修改成功")


# ============ 上传 ============


@router.post("/upload", response_model=DocCheckUploadApiResponse, summary="上传待校验文档")
async def upload_document(
    current_user: RequiredUser,
    file: UploadFile = File(..., description="待校验文档，支持 docx/pdf/txt，不超过 20MB"),
    ctx: PermissionContext = Depends(require_permission("quality:doc-check:create")),
) -> Any:
    buffer = bytearray()
    while chunk := await file.read(_UPLOAD_CHUNK):
        buffer.extend(chunk)
        if len(buffer) > _MAX_UPLOAD_BYTES:
            raise BadRequestException("文件超过 20MB 上限")
    if not buffer:
        raise BadRequestException("上传文件为空")
    doc = await store_upload(
        file_name=file.filename or "未命名文档",
        content_type=file.content_type or "application/octet-stream",
        data=bytes(buffer),
    )
    return build_response(
        data=DocCheckUploadResponse(
            file_id=doc.file_id,
            file_name=doc.file_name,
            file_size=doc.file_size,
            content_type=doc.content_type,
        ),
        message="上传成功",
    )


@router.get("/upload/{upload_id}/progress", response_model=DocCheckUploadProgressApiResponse, summary="查询上传进度")
async def get_upload_progress(
    upload_id: str,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("quality:doc-check:read")),
) -> Any:
    if await load_upload_bytes(upload_id) is None:
        raise BadRequestException("上传记录不存在或已失效")
    return build_response(data=DocCheckUploadProgressResponse(file_id=upload_id, status="completed", progress=100))


# ============ 校验任务 ============


@router.get("/check", response_model=DocCheckListApiResponse, summary="获取校验任务列表")
async def list_checks(
    current_user: RequiredUser,
    status: str | None = Query(None, description="状态过滤"),
    file_type: str | None = Query(None, description="文件类型过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    ctx: PermissionContext = Depends(require_permission("quality:doc-check:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    checks, total = await DocCheckService(db).get_checks(
        skip=(page - 1) * page_size,
        limit=page_size,
        status=status,
        file_type=file_type,
    )
    return build_response(
        data=[DocCheckResponse.model_validate(item) for item in checks],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.post("/check", response_model=DocCheckTaskApiResponse, summary="创建校验任务")
async def create_check(
    payload: DocCheckCreate,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("quality:doc-check:create")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    check = await DocCheckService(db).create_check(payload, _operator_of(current_user))
    await db.commit()
    return build_response(
        data=DocCheckTaskResponse(check_id=check.id, status=_status_of(check)),
        message="校验任务创建成功",
    )


@router.post("/batch", response_model=DocCheckBatchApiResponse, summary="批量创建校验任务")
async def create_batch(
    payload: DocCheckBatchCreate,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("quality:doc-check:create")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = DocCheckService(db)
    operator = _operator_of(current_user)
    created_ids: list[str] = []
    skipped: list[str] = []
    try:
        for file_id in dict.fromkeys(payload.file_ids):
            if await load_upload_bytes(file_id) is None:
                skipped.append(file_id)
                continue
            check = await service.create_check(
                DocCheckCreate(
                    doc_type="batch",
                    doc_title=file_id,
                    check_type=payload.check_type,
                ),
                operator,
            )
            created_ids.append(check.id)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return build_response(
        data=DocCheckBatchResponse(created=len(created_ids), skipped=skipped, check_ids=created_ids),
        message="批量任务创建完成",
    )


@router.get("/check/{check_id}", response_model=DocCheckApiResponse, summary="获取校验任务详情")
async def get_check(
    check_id: str,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("quality:doc-check:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    check = await DocCheckService(db).get_check(check_id)
    return build_response(data=DocCheckResponse.model_validate(check))


@router.put("/check/{check_id}", response_model=DocCheckApiResponse, summary="修改校验任务")
async def update_check(
    check_id: str,
    payload: DocCheckUpdate,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("quality:doc-check:update")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    check = await DocCheckService(db).update_check(check_id, payload)
    await db.commit()
    return build_response(data=DocCheckResponse.model_validate(check), message="校验任务修改成功")


@router.delete("/check/{check_id}", response_model=MessageApiResponse, summary="删除校验任务")
async def delete_check(
    check_id: str,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("quality:doc-check:delete")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    await DocCheckService(db).delete_check(check_id)
    await db.commit()
    return build_response(message="校验任务删除成功")


@router.post("/check/{check_id}/cancel", response_model=DocCheckTaskApiResponse, summary="取消校验任务")
async def cancel_check(
    check_id: str,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("quality:doc-check:cancel")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    check = await DocCheckService(db).cancel_check(check_id)
    await db.commit()
    return build_response(
        data=DocCheckTaskResponse(check_id=check_id, status=_status_of(check)),
        message="校验任务已取消",
    )


@router.post("/check/{check_id}/execute", response_model=DocCheckTaskApiResponse, summary="执行校验任务")
async def execute_check(
    check_id: str,
    payload: DocCheckExecuteRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("quality:doc-check:execute")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = DocCheckService(db)
    await service.mark_running(check_id)
    await db.commit()

    operator = _operator_of(current_user)
    file_id = payload.file_id
    doc_content = payload.doc_content

    async def _runner(_job_id: str) -> dict[str, Any]:
        async with async_session_factory() as session:
            try:
                result_status = await DocCheckService(session).execute_check(
                    check_id,
                    file_id=file_id,
                    doc_content=doc_content,
                    operator=operator,
                )
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            return {"check_id": check_id, "status": result_status}

    job_id = start_job(_JOB_STORE, "doc-check-execute", _runner)
    return build_response(
        data=DocCheckTaskResponse(check_id=check_id, status="running", job_id=job_id),
        message="校验任务已提交",
    )


@router.get("/check/{check_id}/progress", response_model=DocCheckProgressApiResponse, summary="查询校验进度")
async def get_check_progress(
    check_id: str,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("quality:doc-check:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    check = await DocCheckService(db).get_check(check_id)
    status_value = _status_of(check)
    return build_response(
        data=DocCheckProgressResponse(
            check_id=check_id,
            status=status_value,
            progress=_PROGRESS_BY_STATUS.get(status_value, 0),
            current_step=_STEP_BY_STATUS.get(status_value, "未知状态"),
        )
    )


# ============ 问题明细 ============


@router.get("/problems", response_model=ProblemListApiResponse, summary="获取问题明细列表")
async def list_problems(
    current_user: RequiredUser,
    check_id: str = Query(..., description="校验任务 ID"),
    ctx: PermissionContext = Depends(require_permission("quality:problem:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    problems = await DocCheckService(db).get_problems(check_id)
    return build_response(data=[ProblemResponse.model_validate(item) for item in problems])


@router.put("/problems/batch", response_model=ProblemBatchApiResponse, summary="批量处理问题")
async def batch_update_problems(
    payload: ProblemBatchUpdate,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("quality:problem:create")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    updated, skipped = await DocCheckService(db).batch_update_problems(
        payload.problem_ids,
        payload.handle_status,
        payload.ignore_reason,
        _operator_of(current_user),
    )
    await db.commit()
    return build_response(
        data=ProblemBatchResult(updated=updated, skipped=skipped),
        message="问题批量处理完成",
    )


@router.put("/problems/{problem_id}", response_model=ProblemApiResponse, summary="处理单个问题")
async def update_problem(
    problem_id: str,
    payload: ProblemUpdate,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("quality:problem:update")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    problem = await DocCheckService(db).update_problem(problem_id, payload, _operator_of(current_user))
    await db.commit()
    return build_response(data=ProblemResponse.model_validate(problem), message="问题处理完成")


# ============ 校验记录 ============


@router.get("/records", response_model=DocCheckListApiResponse, summary="获取校验记录列表")
async def list_records(
    current_user: RequiredUser,
    status: str | None = Query(None, description="状态过滤"),
    file_type: str | None = Query(None, description="文件类型过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    ctx: PermissionContext = Depends(require_permission("quality:record:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    checks, total = await DocCheckService(db).get_checks(
        skip=(page - 1) * page_size,
        limit=page_size,
        status=status,
        file_type=file_type,
    )
    return build_response(
        data=[DocCheckResponse.model_validate(item) for item in checks],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/records/{record_id}", response_model=DocCheckDetailApiResponse, summary="获取校验记录详情")
async def get_record(
    record_id: str,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("quality:module:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = DocCheckService(db)
    check = await service.get_check(record_id)
    problems = await service.get_problems(record_id)
    base = DocCheckResponse.model_validate(check)
    detail = DocCheckDetailResponse(
        **base.model_dump(),
        problems=[ProblemResponse.model_validate(item) for item in problems],
    )
    return build_response(data=detail)


@router.post("/records/{record_id}/confirm", response_model=DocCheckConfirmApiResponse, summary="确认校验记录通过")
async def confirm_record(
    record_id: str,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("quality:doc-check:update")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    status_value, confirmed = await DocCheckService(db).confirm_check(record_id, _operator_of(current_user))
    await db.commit()
    return build_response(
        data=DocCheckConfirmResponse(check_id=record_id, status=status_value, confirmed_problems=confirmed),
        message="校验记录已确认通过",
    )


# ============ 导出 ============


@router.get("/export/{record_id}", response_model=DocCheckExportApiResponse, summary="导出校验报告")
async def export_report(
    record_id: str,
    current_user: RequiredUser,
    export_format: str = Query("html", alias="format", description="导出格式，当前仅支持 html"),
    ctx: PermissionContext = Depends(require_permission("quality:export:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    if export_format.lower() != "html":
        raise BadRequestException("导出格式当前仅支持 html")
    service = DocCheckService(db)
    check = await service.get_check(record_id)
    file_name = f"doc-check-{check.file_code or check.id}.html"
    return build_response(
        data=DocCheckExportResponse(
            file_name=file_name,
            download_url=f"/api/v1/quality/export/{record_id}/file",
            format="html",
        )
    )


@router.get("/export/{record_id}/file", response_class=HTMLResponse, summary="下载校验报告文件")
async def download_report(
    record_id: str,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("quality:export:read")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    service = DocCheckService(db)
    check = await service.get_check(record_id)
    problems = [ProblemResponse.model_validate(item) for item in await service.get_problems(record_id)]
    html = _render_report_html(check, problems)
    return Response(
        content=html,
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="doc-check-{check.id}.html"'},
    )
