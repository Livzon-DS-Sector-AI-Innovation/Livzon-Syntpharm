"""交付物模板 API：Word 母本上传、版本留档、下载、回滚与填充示例稿。

路由仍挂在 /api/v1/research/doc-gen/deliverable-templates/* 下：前端调用与
存量权限绑定都以该前缀为准，改名会同时打断两者，收益不足。
除「填充示例稿」（按已保存的填充项在母本上写标记）外，本模块不做文档生成。
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.exceptions import NotFoundException
from app.core.response import build_response
from app.modules.research.doc_template import service
from app.modules.research.doc_template.schemas import (
    DocGenBatchUploadResponse,
    DocGenOperationResponse,
    DocGenTemplateFileResponse,
    DocGenTemplateSampleResponse,
    DocGenTemplateSlotsReparseRequest,
    DocGenTemplateSlotsReparseResponse,
    DocGenTemplateSlotsResponse,
    DocGenTemplateSlotsSaveRequest,
    DocGenTemplateSlotsSaveResponse,
    DocGenTemplateVersionListResponse,
    DocGenTemplateVersionRestoreResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/deliverable-templates/batch-upload",
    summary="批量上传 Word 模板",
    response_model=DocGenBatchUploadResponse,
    status_code=201,
)
async def batch_upload_templates(
    current_user: RequiredUser,
    files: list[UploadFile] = File(..., description="Word 模板文件（.docx / .dotx / .doc）"),
    stage: str = Form("", description="所属阶段，可以不填"),
    deliverable_type: str = Form("", description="交付文档类型，可以不填"),
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
    summary="上传 Word 模板文件",
    response_model=DocGenTemplateFileResponse,
)
async def upload_template_file(
    template_id: UUID,
    current_user: RequiredUser,
    file: UploadFile = File(..., description="Word 模板文件（.docx / .dotx / .doc）"),
    change_note: str = Form("", description="这个版本改了什么，可以不填"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """给已存在的交付物模板挂载/替换 Word 模板原件，并自动留档为一个新版本。

    上传不会自动启用模板：由用户确认母本无误后手动开启。
    """
    from app.modules.research.models import RdDeliverableTemplate

    template = await db.get(RdDeliverableTemplate, template_id)
    if template is None or template.is_deleted:
        raise NotFoundException("模板")
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
        message="上传成功，已经存成一个新版本",
    )


@router.get("/deliverable-templates/{template_id}/download", summary="下载 Word 模板文件")
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
    summary="交付文档模板的版本历史",
    response_model=DocGenTemplateVersionListResponse,
)
async def list_template_versions(
    template_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """模板的留档版本（新版本在前），据此可下载或回滚任一个历史版本。"""
    return build_response(data=await service.list_template_versions(db, template_id))


@router.get(
    "/deliverable-templates/{template_id}/versions/{version_id}/download",
    summary="下载历史版本的 Word 文件",
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
    summary="恢复到指定历史版本",
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
        message=f"已经恢复到 v{result['from_version_no']}，并另存为 v{result['version_no']}",
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
    return build_response(message="这条历史记录已删除")


@router.post(
    "/deliverable-templates/{template_id}/sample",
    summary="生成填充示例稿",
    response_model=DocGenTemplateSampleResponse,
)
async def generate_template_sample(
    template_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:deliverable-template:update")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """按已保存的填充项在母本上就地标注，生成一份可预览/下载的示例稿。

    示例稿单独留档为一个版本（不成为当前母本），据此可对照每处该填什么、填在哪。
    """
    data = await service.generate_sample_document(db, template_id, current_user.id if current_user else None)
    await db.commit()
    message = f"已生成填充示例稿 v{data['version_no']}，共标注 {data['slot_count']} 项"
    if data["skipped_count"]:
        message += f"；{data['skipped_count']} 项未启用或未绑定位置，已跳过"
    if data["unresolved_count"]:
        message += f"；{data['unresolved_count']} 项在母本里找不到位置，未标注"
    return build_response(data=data, message=message)


@router.get(
    "/deliverable-templates/{template_id}/slots",
    summary="交付文档模板的填充项设置",
    response_model=DocGenTemplateSlotsResponse,
)
async def get_template_slots(
    template_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:deliverable-template:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """返回槽位清单与母本候选位置；只读文件，不触发模型识别。"""
    return build_response(data=await service.template_slots_payload(db, template_id))


@router.put(
    "/deliverable-templates/{template_id}/slots",
    summary="保存填充项设置",
    response_model=DocGenTemplateSlotsSaveResponse,
)
async def save_template_slots(
    template_id: UUID,
    payload: DocGenTemplateSlotsSaveRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:deliverable-template:update")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """全量覆盖槽位结构（人工增删改）；锚点必须在当前母本里，换版后须先重新识别。"""
    data = await service.save_template_slots(
        db,
        template_id,
        [item.model_dump() for item in payload.slots],
        payload.token,
        current_user.id if current_user else None,
    )
    await db.commit()
    return build_response(data=data, message="填充项已保存，下次生成文档时生效")


@router.post(
    "/deliverable-templates/{template_id}/slots/reparse",
    summary="重新分析模板结构",
    response_model=DocGenTemplateSlotsReparseResponse,
)
async def reparse_template_slots(
    template_id: UUID,
    payload: DocGenTemplateSlotsReparseRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:deliverable-template:update")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """强制重解析并按位置合并：人工改过的字段保留，只补 AI 新识别的位置。"""
    data = await service.reparse_template_slots(
        db,
        template_id,
        payload.token,
        current_user.id if current_user else None,
    )
    await db.commit()
    stats = data["stats"]
    return build_response(
        data=data,
        message=f"分析完成：新增 {stats['added']} 项、保留 {stats['kept']} 项、去掉 {stats['removed']} 项",
    )


def _sse(payload: dict[str, Any]) -> str:
    """SSE 帧：统一把事件塞进 data 的 JSON 里，前端只认 ``type`` 字段。"""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post(
    "/deliverable-templates/{template_id}/slots/reparse/stream",
    summary="重新分析模板结构（流式）",
    response_model=None,
)
async def reparse_template_slots_stream(
    template_id: UUID,
    payload: DocGenTemplateSlotsReparseRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("research:deliverable-template:update")),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """重解析并边分析边推事件：阶段、思考增量、最终合并结果。

    同步版 ``/slots/reparse`` 保留不动（脚本与老前端仍可用）；两个入口共用
    ``service`` 里的同一套校验与合并逻辑，区别只是等待过程是否可见。
    """
    user_id = current_user.id if current_user else None

    async def event_stream() -> AsyncIterator[str]:
        started = time.perf_counter()
        # 先发一帧：浏览器拿到首字节才会把「正在连接」变成「正在分析」
        yield _sse({"type": "phase", "phase": "start", "message": "已接收请求，正在准备分析", "elapsed_ms": 0})
        try:
            async for event in service.reparse_template_slots_stream(db, template_id, payload.token, user_id):
                if "elapsed_ms" not in event:
                    event = {**event, "elapsed_ms": int((time.perf_counter() - started) * 1000)}
                yield _sse(event)
        except Exception as exc:  # noqa: BLE001 - 已发响应头，只能用事件告知失败
            logger.exception("template slots reparse stream failed", extra={"template_id": str(template_id)})
            detail = getattr(exc, "detail", None) or str(exc) or "分析失败，请稍后重试"
            yield _sse(
                {
                    "type": "error",
                    "message": str(detail),
                    "elapsed_ms": int((time.perf_counter() - started) * 1000),
                }
            )
            return
        yield _sse({"type": "done", "elapsed_ms": int((time.perf_counter() - started) * 1000)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            # 让 nginx 不要缓冲：否则思考增量会攒到结束才一次性吐出来
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


def _attachment(data: bytes, filename: str, mime: str) -> Response:
    """附件响应：中文文件名走 RFC 5987，避免乱码或响应头非法。"""
    quoted = quote(filename, safe="")
    fallback = "".join(ch if ch.isascii() and (ch.isalnum() or ch in "._-") else "_" for ch in filename)
    disposition = f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quoted}"
    return Response(content=data, media_type=mime, headers={"Content-Disposition": disposition})
