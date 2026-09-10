# mypy: ignore-errors
"""Safety API — knowledge endpoints."""

import os
import uuid
from datetime import datetime
import logging
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.core.response import ApiResponse, build_response  # type: ignore[attr-defined]
from app.core.storage import is_enabled as minio_enabled
from app.core.storage import upload_object
from app.modules.safety.schemas import (
    SafetyKnowledgeArticleCreate,
    SafetyKnowledgeArticleResponse,
    SafetyKnowledgeArticleUpdate,
)
from app.modules.safety.service import (
    KnowledgeService,
)

logger = logging.getLogger(__name__)

knowledge_router = APIRouter()


@knowledge_router.get("/knowledge-articles", response_model=ApiResponse, summary="获取安全知识库文章列表")
async def handler(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    category: str | None = None,
    status: str | None = None,
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """获取安全知识库文章列表"""
    service = KnowledgeService(db)
    skip = (page - 1) * page_size
    items, total = await service.get_articles(skip, page_size, category, status, keyword)
    return build_response(
        data=[SafetyKnowledgeArticleResponse.model_validate(a) for a in items],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@knowledge_router.post(  # type: ignore[no-redef]
    "/knowledge-articles", response_model=ApiResponse, summary="创建安全知识库文章"
)
async def handler(  # noqa: F811
    data: SafetyKnowledgeArticleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """创建安全知识库文章"""
    service = KnowledgeService(db)
    item = await service.create_article(data)
    await db.commit()
    return build_response(data=SafetyKnowledgeArticleResponse.model_validate(item))


@knowledge_router.get(  # type: ignore[no-redef]
    "/knowledge-articles/{article_id}",
    response_model=ApiResponse,
    summary="获取安全知识库文章详情",
)
async def handler(  # noqa: F811
    article_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """获取安全知识库文章详情"""
    service = KnowledgeService(db)
    item = await service.get_article(article_id)
    if not item:
        return build_response(code=404, message="文章不存在")
    return build_response(data=SafetyKnowledgeArticleResponse.model_validate(item))


@knowledge_router.put(  # type: ignore[no-redef]
    "/knowledge-articles/{article_id}",
    response_model=ApiResponse,
    summary="更新安全知识库文章",
)
async def handler(  # noqa: F811
    article_id: uuid.UUID,
    data: SafetyKnowledgeArticleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """更新安全知识库文章"""
    service = KnowledgeService(db)
    item = await service.update_article(article_id, data)
    if not item:
        return build_response(code=404, message="文章不存在")
    await db.commit()
    return build_response(data=SafetyKnowledgeArticleResponse.model_validate(item))


@knowledge_router.delete(  # type: ignore[no-redef]
    "/knowledge-articles/{article_id}",
    response_model=ApiResponse,
    summary="删除安全知识库文章",
)
async def handler(  # noqa: F811
    article_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """删除安全知识库文章"""
    service = KnowledgeService(db)
    result = await service.delete_article(article_id)
    if not result:
        return build_response(code=404, message="文章不存在")
    await db.commit()
    return build_response(message="删除成功")


@knowledge_router.post(  # type: ignore[no-redef]
    "/knowledge-articles/{article_id}/publish",
    response_model=ApiResponse,
    summary="发布知识库文章",
)
async def handler(  # noqa: F811
    article_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """发布文章（草稿→已发布）"""
    service = KnowledgeService(db)
    item = await service.publish_article(article_id)
    if not item:
        return build_response(code=400, message="无法发布，当前状态不允许")
    await db.commit()
    return build_response(data=SafetyKnowledgeArticleResponse.model_validate(item))


@knowledge_router.post(  # type: ignore[no-redef]
    "/knowledge-articles/{article_id}/archive",
    response_model=ApiResponse,
    summary="归档知识库文章",
)
async def handler(  # noqa: F811
    article_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """归档文章（已发布→已归档）"""
    service = KnowledgeService(db)
    item = await service.archive_article(article_id)
    if not item:
        return build_response(code=400, message="无法归档，当前状态不允许")
    await db.commit()
    return build_response(data=SafetyKnowledgeArticleResponse.model_validate(item))


@knowledge_router.post(  # type: ignore[no-redef]
    "/knowledge-articles/{article_id}/upload",
    response_model=ApiResponse,
    summary="上传知识库文章附件",
)
async def handler(  # noqa: F811
    article_id: uuid.UUID,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """上传知识库文章附件"""

    file_ext = os.path.splitext(file.filename or ".bin")[1]
    safe_name = f"{article_id}_{int(datetime.now().timestamp())}{file_ext}"
    content = await file.read()

    if minio_enabled():
        object_key = f"knowledge/{safe_name}"
        upload_object(
            "safety",
            object_key,
            content,
            len(content),
            file.content_type or "application/octet-stream",
        )
        stored_path = object_key
    else:
        upload_dir = os.path.join("uploads", "safety", "knowledge")
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, safe_name)
        with open(file_path, "wb") as f:
            f.write(content)
        stored_path = file_path

    service = KnowledgeService(db)
    item = await repo.update_knowledge_article(
        article_id,
        {
            "attachment_path": stored_path,
            "attachment_original_name": file.filename or "unknown",
        },
    )
    if not item:
        return build_response(code=404, message="文章不存在")
    await db.commit()
    return build_response(data=SafetyKnowledgeArticleResponse.model_validate(item))


# ── 知识图谱端点 ──────────────────────────────────────────


def _node_to_dict(n) -> dict:
    """节点 ORM → dict"""
    return {
        "id": str(n.id),
        "name": n.name,
        "node_type": n.node_type,
        "aliases": n.aliases,
        "article_id": str(n.article_id) if n.article_id else None,
        "entity_type": n.entity_type,
        "ai_summary": n.ai_summary,
        "confidence": n.confidence,
        "status": n.status,
        "merged_into_id": str(n.merged_into_id) if n.merged_into_id else None,
        "metadata": n.extra_metadata,
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "updated_at": n.updated_at.isoformat() if n.updated_at else None,
    }


def _edge_to_dict(e) -> dict:
    """边 ORM → dict"""
    return {
        "id": str(e.id),
        "source_node_id": str(e.source_node_id),
        "target_node_id": str(e.target_node_id),
        "relation_type": e.relation_type,
        "description": e.description,
        "evidence_text": e.evidence_text,
        "confidence": e.confidence,
        "status": e.status,
        "metadata": e.extra_metadata,
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "updated_at": e.updated_at.isoformat() if e.updated_at else None,
    }


@knowledge_router.get(
    "/knowledge-graph/full-graph",
    response_model=ApiResponse,
    summary="获取完整知识图谱",
)
async def get_full_graph(
    node_types: str | None = None,
    relation_types: str | None = None,
    max_nodes: int = Query(500, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:
    """获取完整知识图谱数据"""
    from app.modules.safety.service import KnowledgeGraphService

    service = KnowledgeGraphService(db)
    data = await service.get_full_graph(node_types, relation_types, max_nodes)
    return build_response(
        data={
            "nodes": [_node_to_dict(n) for n in data["nodes"]],
            "edges": [_edge_to_dict(e) for e in data["edges"]],
            "stats": data["stats"],
        }
    )


@knowledge_router.get(
    "/knowledge-graph/nodes",
    response_model=ApiResponse,
    summary="获取图谱节点列表",
)
async def get_graph_nodes(
    node_type: str | None = None,
    entity_type: str | None = None,
    status: str | None = None,
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:
    """获取图谱节点列表"""
    from app.modules.safety.service import KnowledgeGraphService

    service = KnowledgeGraphService(db)
    offset = (page - 1) * page_size
    items, total = await service.get_nodes(node_type, entity_type, status, keyword, offset, page_size)
    return build_response(
        data=[_node_to_dict(n) for n in items],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@knowledge_router.get(
    "/knowledge-graph/edges",
    response_model=ApiResponse,
    summary="获取图谱边列表",
)
async def get_graph_edges(
    relation_type: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:
    """获取图谱边列表"""
    from app.modules.safety.service import KnowledgeGraphService

    service = KnowledgeGraphService(db)
    offset = (page - 1) * page_size
    items, total = await service.get_edges(relation_type, status, offset, page_size)
    return build_response(
        data=[_edge_to_dict(e) for e in items],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@knowledge_router.get(
    "/knowledge-graph/search",
    response_model=ApiResponse,
    summary="搜索图谱节点",
)
async def search_graph_nodes(
    query: str = Query(..., min_length=1),
    node_types: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:
    """搜索图谱节点"""
    from app.modules.safety.service import KnowledgeGraphService

    service = KnowledgeGraphService(db)
    items = await service.search_nodes(query, node_types)
    return build_response(data=[_node_to_dict(n) for n in items])


@knowledge_router.get(
    "/knowledge-graph/expand",
    response_model=ApiResponse,
    summary="展开节点邻居",
)
async def expand_graph_node(
    node_id: uuid.UUID,
    hops: int = Query(1, ge=1, le=3),
    relation_types: str | None = None,
    max_nodes: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:
    """展开指定节点的邻居节点"""
    from app.modules.safety.service import KnowledgeGraphService

    service = KnowledgeGraphService(db)
    data = await service.expand_node(node_id, hops, relation_types, max_nodes)
    return build_response(
        data={
            "nodes": [_node_to_dict(n) for n in data["nodes"]],
            "edges": [_edge_to_dict(e) for e in data["edges"]],
            "stats": data["stats"],
        }
    )


@knowledge_router.post(
    "/knowledge-graph/generate",
    response_model=ApiResponse,
    summary="AI 生成知识图谱",
)
async def generate_graph(
    document_ids: list[uuid.UUID] | None = None,
    force_rebuild: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:
    """从知识库文章 AI 生成知识图谱"""
    from app.modules.safety.service import KnowledgeGraphService

    service = KnowledgeGraphService(db)
    result = await service.generate_graph(document_ids, force_rebuild)
    await db.commit()
    return build_response(data=result)


@knowledge_router.post(  # type: ignore[no-redef]
    "/knowledge-articles/batch-import",
    response_model=ApiResponse,
    summary="批量导入知识库文章",
)
async def handler(  # noqa: F811
    files: list[UploadFile] = File(...),
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """批量导入知识库文章"""
    from app.modules.safety.service.document_parser import parse_document

    if not files:
        return build_response(code=400, message="未选择文件")

    if len(files) > 20:
        return build_response(code=400, message="单次最多导入 20 个文件")

    service = KnowledgeService(db)
    repo = service.repo
    results = []
    success_count = 0
    error_count = 0

    for file in files:
        try:
            # 读取文件内容
            content = await file.read()
            filename = file.filename or "unknown"

            # 检查文件大小（最大 50MB）
            if len(content) > 50 * 1024 * 1024:
                results.append(
                    {
                        "filename": filename,
                        "status": "error",
                        "message": "文件过大（超过 50MB）",
                    }
                )
                error_count += 1
                continue

            # 解析文档
            parsed = await parse_document(filename, content)

            # 使用用户指定的分类，或使用推断的分类
            final_category = category if category else parsed["category"]

            # 检查是否已存在同名文章
            existing = await repo.get_knowledge_article_by_title(parsed["title"])
            if existing:
                results.append(
                    {
                        "filename": filename,
                        "status": "skipped",
                        "message": f"已存在同名文章: {parsed['title']}",
                    }
                )
                error_count += 1
                continue

            # 创建文章
            article_data = {
                "title": parsed["title"],
                "summary": parsed["summary"],
                "content": parsed["content"],
                "category": final_category,
                "tags": parsed["tags"],
                "status": "draft",
            }
            article = await repo.create_knowledge_article(article_data)

            # 保存附件
            file_ext = os.path.splitext(filename)[1]
            safe_name = f"{article.id}_{int(datetime.now().timestamp())}{file_ext}"

            if minio_enabled():
                object_key = f"knowledge/{safe_name}"
                upload_object(
                    "safety",
                    object_key,
                    content,
                    len(content),
                    file.content_type or "application/octet-stream",
                )
                stored_path = object_key
            else:
                upload_dir = os.path.join("uploads", "safety", "knowledge")
                os.makedirs(upload_dir, exist_ok=True)
                file_path = os.path.join(upload_dir, safe_name)
                with open(file_path, "wb") as f:
                    f.write(content)
                stored_path = file_path

            # 更新文章的附件信息
            await repo.update_knowledge_article(
                article.id,
                {
                    "attachment_path": stored_path,
                    "attachment_original_name": filename,
                },
            )

            results.append(
                {
                    "filename": filename,
                    "status": "success",
                    "article_id": str(article.id),
                    "title": parsed["title"],
                    "category": final_category,
                }
            )
            success_count += 1

        except Exception as e:
            results.append(
                {
                    "filename": file.filename or "unknown",
                    "status": "error",
                    "message": str(e),
                }
            )
            error_count += 1

    await db.commit()

    return build_response(
        data={
            "results": results,
            "summary": {
                "total": len(files),
                "success": success_count,
                "error": error_count,
            },
        },
        message=f"导入完成：成功 {success_count} 篇，失败 {error_count} 篇",
    )


@knowledge_router.post(
    "/knowledge-articles/{article_id}/generate-card",
    response_model=ApiResponse,
    summary="生成知识卡片",
)
async def generate_card(
    article_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:
    """使用 AI 从文章内容生成结构化知识卡片（委托给 KnowledgeService）
    
    TODO(H7): Consider async task pattern for large documents.
    """
    service = KnowledgeService(db)
    try:
        result = await service.generate_card(article_id)
        await db.commit()
        card = result.get("card", result)
        # 如果生成了知识卡片，更新文章字段
        if "card" in result:
            await service.update_article(article_id, type("U", (), {"model_dump": lambda self: {"knowledge_card": card}})())
            await db.commit()
        return build_response(data=card, message=result.get("message", "知识卡片生成成功"))
    except ValueError as e:
        return build_response(code=400, message=str(e))
    except Exception:
        logger.exception("知识卡片生成失败: article_id=%s", article_id)
        return build_response(code=500, message="知识卡片生成失败")


@knowledge_router.post(
    "/knowledge-articles/{article_id}/generate-ppt",
    response_model=ApiResponse,
    summary="生成 PPT",
)
async def generate_ppt(
    article_id: uuid.UUID,
    data: dict[str, Any] = Body(default_factory=dict),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:
    """使用 AI 从文章内容生成 PPT（.pptx 文件）
    
    TODO(H7): This operation can take >5s. Consider converting to async task + polling:
    1. Accept request → create task record → return task_id immediately
    2. Background worker generates PPT
    3. Client polls /tasks/{task_id}/status for completion
    """
    from app.modules.safety.service.ppt_generator import PptGeneratorService

    template = data.get("template", "training") if data else "training"
    style = data.get("style", "professional") if data else "professional"

    try:
        ppt_service = PptGeneratorService(db)
        result = await ppt_service.generate(article_id, template=template, style=style)
        await db.commit()
        return build_response(data=result, message=result["message"])
    except ValueError as e:
        return build_response(code=400, message=str(e))
    except Exception:
        logger.exception("PPT 生成失败: article_id=%s", article_id)
        return build_response(code=500, message="PPT 生成失败")


@knowledge_router.get(
    "/knowledge-articles/{article_id}/ppt-history",
    response_model=ApiResponse,
    summary="获取 PPT 生成历史",
)
async def get_ppt_history(
    article_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:
    """查询某文章的 PPT 生成历史记录（委托给 KnowledgeService）"""
    service = KnowledgeService(db)
    skip = (page - 1) * page_size
    items, total = await service.get_ppt_history(article_id, skip, page_size)

    records = []
    for item in items:
        records.append(
            {
                "id": str(item.id),
                "file_name": item.file_name,
                "template": item.template,
                "style": item.style,
                "page_count": item.page_count,
                "download_url": item.object_key,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
        )

    return build_response(data={"records": records, "total": total})


@knowledge_router.post(
    "/knowledge-articles/{article_id}/generate-summary",
    response_model=ApiResponse,
    summary="生成摘要",
)
async def generate_summary(
    article_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:
    """使用 AI 从文章内容生成摘要（委托给 KnowledgeService）
    
    TODO(H7): Consider async task pattern for large documents.
    """
    service = KnowledgeService(db)
    try:
        result = await service.generate_summary(article_id)
        await db.commit()
        return build_response(data=result, message=result.get("message", "摘要生成成功"))
    except ValueError as e:
        return build_response(code=400, message=str(e))
    except Exception:
        logger.exception("摘要生成失败: article_id=%s", article_id)
        return build_response(code=500, message="摘要生成失败")
