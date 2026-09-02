# mypy: ignore-errors
"""Safety API — knowledge endpoints."""

import os
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.core.response import ApiResponse  # type: ignore[attr-defined]
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
    return ApiResponse(
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
    return ApiResponse(data=SafetyKnowledgeArticleResponse.model_validate(item))


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
        return ApiResponse(code=404, message="文章不存在")
    return ApiResponse(data=SafetyKnowledgeArticleResponse.model_validate(item))


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
        return ApiResponse(code=404, message="文章不存在")
    await db.commit()
    return ApiResponse(data=SafetyKnowledgeArticleResponse.model_validate(item))


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
        return ApiResponse(code=404, message="文章不存在")
    await db.commit()
    return ApiResponse(message="删除成功")


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
        return ApiResponse(code=400, message="无法发布，当前状态不允许")
    await db.commit()
    return ApiResponse(data=SafetyKnowledgeArticleResponse.model_validate(item))


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
        return ApiResponse(code=400, message="无法归档，当前状态不允许")
    await db.commit()
    return ApiResponse(data=SafetyKnowledgeArticleResponse.model_validate(item))


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

    from app.modules.safety.repository import SafetyRepository

    repo = SafetyRepository(db)
    item = await repo.update_knowledge_article(
        article_id,
        {
            "attachment_path": stored_path,
            "attachment_original_name": file.filename or "unknown",
        },
    )
    if not item:
        return ApiResponse(code=404, message="文章不存在")
    await db.commit()
    return ApiResponse(data=SafetyKnowledgeArticleResponse.model_validate(item))


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
    return ApiResponse(
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
    return ApiResponse(
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
    return ApiResponse(
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
    return ApiResponse(data=[_node_to_dict(n) for n in items])


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
    return ApiResponse(
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
    return ApiResponse(data=result)
