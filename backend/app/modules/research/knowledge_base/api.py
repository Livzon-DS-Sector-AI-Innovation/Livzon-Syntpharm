"""项目知识库 API：/api/v1/research/knowledge-bases/*

读接口默认回源 RAGFlow 对账（解析进度只能由 RAGFlow 给出）；
写接口全部要求登录，失败即报错，不做静默吞异常。
"""

from __future__ import annotations

import io
import logging
from typing import Any
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import RequiredUser
from app.core.response import build_response
from app.modules.research.knowledge_base import service
from app.modules.research.knowledge_base.schemas import (
    KbChunkListResponse,
    KbDocumentListResponse,
    KbLimitsResponse,
    KbUploadResponse,
    KnowledgeBaseCreateRequest,
    KnowledgeBaseDataResponse,
    KnowledgeBaseListResponse,
    KnowledgeBaseOperationResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/limits", summary="知识库上传限制", response_model=KbLimitsResponse)
async def read_limits(current_user: RequiredUser) -> Any:
    """前端据此做提交前校验，并可提前提示「知识库服务未配置」。"""
    return build_response(data=await service.limits())


@router.get("", summary="知识库列表", response_model=KnowledgeBaseListResponse)
async def list_knowledge_bases(
    current_user: RequiredUser,
    project_id: UUID | None = Query(None, description="按研发项目过滤"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """传 project_id 时通常返回 0 或 1 条：用于新建报告页判断项目是否已挂知识库。"""
    rows = await service.list_knowledge_bases(db, project_id=project_id)
    data = [service.knowledge_base_payload(kb, project_name=name) for kb, name in rows]
    return build_response(data=data)


@router.post("", summary="为项目新建知识库", response_model=KnowledgeBaseDataResponse, status_code=201)
async def create_knowledge_base(
    payload: KnowledgeBaseCreateRequest,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """在 RAGFlow 建数据集并落本地映射；一个项目至多一个有效知识库。"""
    kb = await service.create_knowledge_base(
        db,
        project_id=payload.project_id,
        name=payload.name,
        description=payload.description,
        embedding_model=payload.embedding_model,
        chunk_method=payload.chunk_method,
        user_id=current_user.id if current_user else None,
    )
    project_name = (await service.list_knowledge_bases(db, project_id=kb.project_id))[:1]
    await db.commit()
    logger.info("知识库创建完成", extra={"kb_id": str(kb.id), "module_name": "research"})
    return build_response(
        data=service.knowledge_base_payload(kb, project_name=project_name[0][1] if project_name else ""),
        message="知识库已创建",
    )


@router.get("/{kb_id}", summary="知识库详情", response_model=KnowledgeBaseDataResponse)
async def read_knowledge_base(
    kb_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """详情含文档计数；文档列表另走 /documents。"""
    kb = await service.get_knowledge_base(db, kb_id)
    await service.sync_documents(db, kb)
    project_name = (await service.list_knowledge_bases(db, project_id=kb.project_id))[:1]
    documents = await service.load_documents(db, kb.id)
    await db.commit()
    return build_response(
        data=service.knowledge_base_payload(
            kb, project_name=project_name[0][1] if project_name else "", documents=documents
        )
    )


@router.delete("/{kb_id}", summary="删除知识库", response_model=KnowledgeBaseOperationResponse)
async def delete_knowledge_base(
    kb_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """同时删除远端数据集；远端失败不阻断本地清理。"""
    await service.delete_knowledge_base(db, kb_id, user_id=current_user.id if current_user else None)
    await db.commit()
    return build_response(message="知识库已删除")


@router.get("/{kb_id}/documents", summary="文档列表（含解析进度）", response_model=KbDocumentListResponse)
async def list_documents(
    kb_id: UUID,
    current_user: RequiredUser,
    refresh: bool = Query(True, description="是否回源 RAGFlow 刷新解析进度"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """前端轮询此端点展示解析进度；refresh=false 时只读本地镜像（离线也不报错）。"""
    kb = await service.get_knowledge_base(db, kb_id)
    rows = await service.sync_documents(db, kb) if refresh else await service.load_documents(db, kb.id)
    data = [service.document_payload(row) for row in rows]
    await db.commit()
    return build_response(data=data)


@router.post("/{kb_id}/documents", summary="上传资料并触发解析", response_model=KbUploadResponse)
async def upload_documents(
    kb_id: UUID,
    current_user: RequiredUser,
    files: list[UploadFile] = File(..., description="资料文件（可多个）"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """上传后立即触发 RAGFlow 解析；单份失败不影响其余文件，跳过原因逐条返回。"""
    kb = await service.get_knowledge_base(db, kb_id)
    uploaded, skipped, documents = await service.upload_documents(
        db, kb, list(files), user_id=current_user.id if current_user else None
    )
    await db.commit()
    message = f"已上传 {len(uploaded)} 份资料并开始解析" if uploaded else "没有文件被上传"
    if skipped:
        message += f"，{len(skipped)} 份被跳过"
    logger.info(
        "知识库资料上传完成",
        extra={"kb_id": str(kb.id), "uploaded": len(uploaded), "skipped": len(skipped), "module_name": "research"},
    )
    return build_response(
        data={
            "uploaded": uploaded,
            "skipped": skipped,
            "documents": [service.document_payload(row) for row in documents],
        },
        message=message,
    )


@router.delete("/{kb_id}/documents/{document_row_id}", summary="删除文档", response_model=KbDocumentListResponse)
async def delete_document(
    kb_id: UUID,
    document_row_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """从知识库移除一份文档（远端删除成功后才删本地记录）。"""
    kb = await service.get_knowledge_base(db, kb_id)
    rows = await service.delete_document(db, kb, document_row_id, user_id=current_user.id if current_user else None)
    await db.commit()
    return build_response(data=[service.document_payload(row) for row in rows], message="文档已删除")


@router.post(
    "/{kb_id}/documents/{document_row_id}/reparse", summary="重新解析文档", response_model=KbDocumentListResponse
)
async def reparse_document(
    kb_id: UUID,
    document_row_id: UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """清空旧切片后重跑解析，用于解析失败或资料已更新的场景。"""
    kb = await service.get_knowledge_base(db, kb_id)
    rows = await service.reparse_document(db, kb, document_row_id)
    await db.commit()
    return build_response(data=[service.document_payload(row) for row in rows], message="已重新提交解析")


@router.get("/{kb_id}/documents/{document_row_id}/download", summary="下载资料原件")
async def download_document(
    kb_id: UUID,
    document_row_id: UUID,
    current_user: RequiredUser,
    inline: bool = Query(False, description="true 时以 inline 返回，供浏览器内直接打开预览"),
    as_pdf: bool = Query(False, description="true 时把 Office 文档转成 PDF 返回（浏览器无法原生渲染 .doc/.xls/.ppt）"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """流式回源 RAGFlow 的资料原件（下载用原件字节；预览可要求转 PDF）。

    文件本体只存在知识库服务，本地不落副本，故每次实时取；
    因此本端点不套统一响应信封，直接返回字节流（与其它模块的文件下载一致）。
    """
    kb = await service.get_knowledge_base(db, kb_id)
    row = await service.get_document(db, kb.id, document_row_id)
    content, content_type = await service.document_file(kb, row, as_pdf=as_pdf)
    filename = row.file_name or str(document_row_id)
    # ASCII 回退名给老客户端，中文名走 RFC 5987 的 filename*
    ascii_name = filename.encode("ascii", "ignore").decode().strip() or "document"
    disposition = "inline" if inline else "attachment"
    return StreamingResponse(
        io.BytesIO(content),
        media_type=content_type,
        headers={
            "Content-Disposition": f"{disposition}; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}",
            "Content-Length": str(len(content)),
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/{kb_id}/images/{image_id}", summary="切片关联图片")
async def read_document_image(
    kb_id: UUID,
    image_id: str,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """代理知识库服务里的切片图片（PDF 页图 / 图注配图）。

    前端用 ``<img>`` 直接引用本地址：同源请求会带上 auth_token Cookie，
    后端鉴权本身就支持 Cookie，因此不需要前端再转成 blob。
    """
    kb = await service.get_knowledge_base(db, kb_id)
    content, content_type = await service.document_image(kb, image_id)
    return StreamingResponse(
        io.BytesIO(content),
        media_type=content_type,
        headers={
            # 图片按 image_id 不可变：允许浏览器私有缓存，翻页时不重复回源
            "Cache-Control": "private, max-age=3600",
            "Content-Length": str(len(content)),
        },
    )


@router.get(
    "/{kb_id}/documents/{document_row_id}/chunks",
    summary="解析切片（预览解析内容）",
    response_model=KbChunkListResponse,
)
async def list_document_chunks(
    kb_id: UUID,
    document_row_id: UUID,
    current_user: RequiredUser,
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(50, ge=1, le=200, description="每页切片数"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """docx / xls 等浏览器无法直接渲染，预览时用切片看解析结果。"""
    kb = await service.get_knowledge_base(db, kb_id)
    row = await service.get_document(db, kb.id, document_row_id)
    data = await service.document_chunks(kb, row, page=page, page_size=page_size)
    return build_response(data=data)
