"""交付物模板 API：Word 母本上传、版本留档、下载与回滚。

路由仍挂在 /api/v1/research/doc-gen/deliverable-templates/* 下：前端调用与
存量权限绑定都以该前缀为准，改名会同时打断两者，收益不足。
本模块不提供任何文档生成能力。
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import RequiredUser
from app.core.exceptions import NotFoundException
from app.core.response import build_response
from app.modules.research.doc_template import service
from app.modules.research.doc_template.schemas import (
    DocGenBatchUploadResponse,
    DocGenOperationResponse,
    DocGenTemplateFileResponse,
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
    files: list[UploadFile] = File(..., description="Word 模板文件（docx/dotx/doc）"),
    stage: str = Form("", description="所属阶段，可空"),
    deliverable_type: str = Form("", description="交付物类型，可空"),
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

    上传不会自动启用模板：由用户确认母本无误后手动开启。
    """
    from app.modules.research.models import RdDocGenTemplate

    template = await db.get(RdDocGenTemplate, template_id)
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
    """模板的留档版本（新版本在前），据此可下载或回滚任一个历史版本。"""
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


def _attachment(data: bytes, filename: str, mime: str) -> Response:
    """附件响应：中文文件名走 RFC 5987，避免乱码或响应头非法。"""
    quoted = quote(filename, safe="")
    fallback = "".join(ch if ch.isascii() and (ch.isalnum() or ch in "._-") else "_" for ch in filename)
    disposition = f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quoted}"
    return Response(content=data, media_type=mime, headers={"Content-Disposition": disposition})
