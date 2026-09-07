# mypy: ignore-errors
"""Safety API — knowledge endpoints."""

import os
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, Query, UploadFile, File
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
    from app.modules.safety.repository import SafetyRepository
    
    if not files:
        return ApiResponse(code=400, message="未选择文件")
    
    if len(files) > 20:
        return ApiResponse(code=400, message="单次最多导入 20 个文件")
    
    repo = SafetyRepository(db)
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
                results.append({
                    "filename": filename,
                    "status": "error",
                    "message": "文件过大（超过 50MB）",
                })
                error_count += 1
                continue
            
            # 解析文档
            parsed = await parse_document(filename, content)
            
            # 使用用户指定的分类，或使用推断的分类
            final_category = category if category else parsed["category"]
            
            # 检查是否已存在同名文章
            existing = await repo.get_knowledge_article_by_title(parsed["title"])
            if existing:
                results.append({
                    "filename": filename,
                    "status": "skipped",
                    "message": f"已存在同名文章: {parsed['title']}",
                })
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
            
            results.append({
                "filename": filename,
                "status": "success",
                "article_id": str(article.id),
                "title": parsed["title"],
                "category": final_category,
            })
            success_count += 1
            
        except Exception as e:
            results.append({
                "filename": file.filename or "unknown",
                "status": "error",
                "message": str(e),
            })
            error_count += 1
    
    await db.commit()
    
    return ApiResponse(
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
    """使用 AI 从文章内容生成结构化知识卡片"""
    from app.modules.safety.repository import SafetyRepository
    from app.platform.integrations.ai.client import AIService
    from app.core.config import get_settings
    
    repo = SafetyRepository(db)
    article = await repo.get_knowledge_article_by_id(article_id)
    if not article:
        return ApiResponse(code=404, message="文章不存在")
    
    if not article.content:
        return ApiResponse(code=400, message="文章内容为空，无法生成知识卡片")
    
    # 获取 AI 服务配置
    settings = get_settings()
    api_key = settings.LLM_API_KEY or settings.AI_API_KEY
    base_url = settings.LLM_BASE_URL or settings.AI_BASE_URL
    
    if not api_key:
        # 降级方案：使用简单规则提取
        card = {
            "document_title": article.title,
            "document_category": article.category,
            "priority": "P1",
            "hazard_type_definitions": None,
            "hazard_category_criteria": None,
            "hazard_level_criteria": None,
            "key_defect_examples": None,
            "rectification_requirements": None,
            "legal_basis_clauses": None,
        }
        await repo.update_knowledge_article(article_id, {"knowledge_card": card})
        await db.commit()
        return ApiResponse(data=card, message="AI 服务未配置，已生成空知识卡片（请配置 LLM_API_KEY 后重新生成）")
    
    ai_service = AIService(
        api_key=api_key,
        base_url=base_url,
        model="deepseek-chat",
    )
    
    # 构建 prompt
    prompt = f"""请从以下法规文档内容中提取结构化知识卡片。

文档标题：{article.title}
文档分类：{article.category}

文档内容：
{article.content[:3000] if article.content else ""}

请以 JSON 格式返回以下字段：
{{
  "document_title": "文档标题",
  "document_category": "文档分类",
  "priority": "P0 或 P1 或 P2",
  "hazard_type_definitions": "隐患分类定义（人/物/环/管）",
  "hazard_category_criteria": "隐患类别判定标准",
  "hazard_level_criteria": "隐患级别分级标准",
  "key_defect_examples": "典型缺陷示例",
  "rectification_requirements": "整改措施要求",
  "legal_basis_clauses": "可引用的法律依据条文"
}}

如果某些字段在文档中没有相关内容，请返回 null。"""
    
    try:
        response = await ai_service.chat_parsed(
            messages=[{"role": "user", "content": prompt}],
            expected_keys=["document_title", "document_category", "priority"],
        )
        
        # 更新文章的知识卡片字段
        await repo.update_knowledge_article(
            article_id,
            {"knowledge_card": response},
        )
        await db.commit()
        
        return ApiResponse(
            data=response,
            message="知识卡片生成成功",
        )
    except Exception as e:
        return ApiResponse(code=500, message=f"知识卡片生成失败：{str(e)}")



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
    """使用 AI 从文章内容生成 PPT（.pptx 文件）"""
    from app.modules.safety.service.ppt_generator import PptGeneratorService

    template = "training"
    style = "professional"
    if data:
        template = data.get("template", "training")
        style = data.get("style", "professional")

    try:
        service = PptGeneratorService(db)
        result = await service.generate(article_id, template=template, style=style)
        await db.commit()
        return ApiResponse(data=result, message=result["message"])
    except ValueError as e:
        return ApiResponse(code=400, message=str(e))
    except Exception as e:
        return ApiResponse(code=500, message=f"PPT 生成失败：{str(e)}")


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
    """查询某文章的 PPT 生成历史记录"""
    from app.modules.safety.repository import SafetyRepository

    repo = SafetyRepository(db)
    skip = (page - 1) * page_size
    items, total = await repo.get_ppt_generation_records(article_id, skip, page_size)

    records = []
    for item in items:
        records.append({
            "id": str(item.id),
            "file_name": item.file_name,
            "template": item.template,
            "style": item.style,
            "page_count": item.page_count,
            "download_url": item.object_key,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        })

    return ApiResponse(data={"records": records, "total": total})


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
    """使用 AI 从文章内容生成摘要"""
    from app.modules.safety.repository import SafetyRepository
    from app.platform.integrations.ai.client import AIService
    from app.core.config import get_settings
    
    repo = SafetyRepository(db)
    article = await repo.get_knowledge_article_by_id(article_id)
    if not article:
        return ApiResponse(code=404, message="文章不存在")
    
    if not article.content:
        return ApiResponse(code=400, message="文章内容为空，无法生成摘要")
    
    # 获取 AI 服务配置
    settings = get_settings()
    api_key = settings.LLM_API_KEY or settings.AI_API_KEY
    base_url = settings.LLM_BASE_URL or settings.AI_BASE_URL
    
    if not api_key:
        # 降级方案：提取前 500 字符作为摘要
        summary = article.content[:500]
        # 按句号/分号截断
        for sep in ['。', '；', ';', '.', '\n']:
            last_sep = summary.rfind(sep)
            if last_sep > 100:
                summary = summary[:last_sep + 1]
                break
        if len(article.content) > 500:
            summary += "..."
        
        await repo.update_knowledge_article(article_id, {"summary": summary})
        await db.commit()
        return ApiResponse(data={"summary": summary, "message": "AI 服务未配置，已生成基础摘要"}, message="摘要生成成功")
    
    ai_service = AIService(
        api_key=api_key,
        base_url=base_url,
        model="deepseek-chat",
    )
    
    # 构建 prompt
    prompt = f"""请为以下法规文档生成结构化摘要。

文档标题：{article.title}
文档分类：{article.category}

文档内容：
{article.content[:3000] if article.content else ""}

请生成 200-500 字的摘要，包含：
1. 文档的核心目的和适用范围
2. 主要内容和关键条款
3. 重要要求和注意事项

直接返回摘要文本，不需要 JSON 格式。"""
    
    try:
        summary = await ai_service.chat(
            messages=[{"role": "user", "content": prompt}],
            response_format="text",
        )
        
        # 更新文章的摘要字段
        await repo.update_knowledge_article(article_id, {"summary": summary})
        await db.commit()
        
        return ApiResponse(
            data={"summary": summary, "message": "摘要生成成功"},
            message="摘要生成成功",
        )
    except Exception as e:
        return ApiResponse(code=500, message=f"摘要生成失败：{str(e)}")
