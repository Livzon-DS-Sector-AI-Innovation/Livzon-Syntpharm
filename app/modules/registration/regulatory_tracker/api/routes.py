"""Regulatory Tracker API routes V4 - 系统分类支持。"""

import uuid
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.core.response import error_response, success_response
from app.modules.registration.regulatory_tracker import repository as repo
from app.modules.registration.regulatory_tracker.schemas import (
    BatchReadRequest,
    SyncTriggerRequest,
)
from app.modules.registration.regulatory_tracker.services.classification_service import (
    get_category_display_name,
)
from app.modules.registration.regulatory_tracker.utils.excel_export import generate_regulatory_excel

router = APIRouter()


def _extract_impact_data(doc) -> dict:
    """从文档中提取影响评估数据。"""
    from app.modules.registration.regulatory_tracker.services.ai_analysis_service import (
        score_to_impact_level,
    )

    key_points = doc.ai_key_points or {}
    score = doc.ai_relevance_score or 0.0

    if isinstance(key_points, dict):
        # 优先使用 key_points 中的 impact_level，否则根据 score 计算
        impact_level = key_points.get("impact_level") or score_to_impact_level(score)
        return {
            "impact_level": impact_level,
            "impact_score": score,
            "lifecycle_impacts": key_points.get("lifecycle_impacts", []),
            "departments": key_points.get("departments", []),
            "ctd_sections": key_points.get("ctd_sections", []),
            "recommended_actions": key_points.get("recommended_actions", []),
            "notification_required": key_points.get("notification_required", False),
        }

    # 旧数据格式或无结构化数据
    return {
        "impact_level": score_to_impact_level(score) if score > 0 else "low",
        "impact_score": score,
        "lifecycle_impacts": [],
        "departments": [],
        "ctd_sections": [],
        "recommended_actions": [],
        "notification_required": False,
    }


# ============ Dashboard ============


@router.get("/regulatory-tracker/dashboard", summary="Dashboard 工作台数据")
async def get_dashboard(current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """
    返回 Dashboard 工作台数据：
    - 今日新增统计（总数、高影响数、一般法规数）
    - 重点关注数量
    - 近 7 天动态（总数、高影响数）
    - 数据源状态
    - 今日值得关注（最多 5 条 attention 法规）
    - 近 7 天趋势（二级信息）
    - 分类统计（二级信息）
    """
    # 核心数据
    today_stats = await repo.get_today_new_stats(db)
    attention_count = await repo.get_attention_count(db)
    week_stats = await repo.get_week_stats(db)
    source_status = await repo.get_source_status_v2(db)
    priority_docs = await repo.get_priority_documents_v2(db, limit=10)

    # 二级信息
    trend = await repo.get_7day_trend(db)
    classification = await repo.get_classification_stats(db)

    # 格式化今日值得关注法规
    priority_documents = []
    for doc in priority_docs:
        source = await repo.get_data_source_by_id(db, doc.source_id)
        impact_data = _extract_impact_data(doc)

        # 从 ai_key_points 提取法规类型
        key_points = doc.ai_key_points or {}
        regulation_type = (
            key_points.get("regulation_type", "")
            if isinstance(key_points, dict)
            else ""
        )

        priority_documents.append(
            {
                "id": str(doc.id),
                "title": doc.title,
                "sourceName": source.name if source else None,
                "regulationType": regulation_type,
                "publishDate": doc.publish_date.isoformat()
                if doc.publish_date
                else None,
                "aiSummary": doc.ai_summary,
                "aiRelevanceScore": doc.ai_relevance_score,
                "aiKeyPoints": doc.ai_key_points,
                "documentCategory": doc.document_category,
                "documentCategoryName": get_category_display_name(
                    doc.document_category or "general"
                ),
                "originalUrl": doc.original_url,
                "impactLevel": impact_data["impact_level"],
            }
        )

    return {
        "code": 200,
        "message": "success",
        "data": {
            # 四张卡片
            "todayNewCount": today_stats["total"],
            "todayNewHighImpact": today_stats["high"],
            "todayNewGeneralCount": today_stats["general"],
            "attentionCount": attention_count,
            "weekTotal": week_stats["total"],
            "weekHighImpact": week_stats["high_impact"],
            "sourceStatus": source_status,
            # 今日值得关注
            "priorityDocuments": priority_documents,
            # 二级信息
            "trend7Days": trend,
            "byClassification": classification,
        },
    }


# ============ 法规文档统计摘要 ============


@router.get("/regulatory-tracker/summary", summary="法规追踪统计摘要")
async def get_summary(current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    stats = await repo.get_summary_stats(db)
    return {
        "code": 200,
        "message": "success",
        "data": stats,
    }


# ============ 法规文档列表 ============


@router.get("/regulatory-documents", summary="法规文档列表")
async def list_documents(
    current_user: CurrentUser,
    keyword: str | None = Query(None, description="关键词搜索"),
    publishDateFrom: date | None = Query(None, description="发布日期起始"),
    publishDateTo: date | None = Query(None, description="发布日期结束"),
    statusText: str | None = Query(None, description="状态筛选"),
    classification: str | None = Query(None, description="分类筛选"),
    isNew: bool | None = Query(None, description="是否新增"),
    impactLevel: str | None = Query(
        None, description="影响等级筛选: high/medium/low/none/unanalyzed"
    ),
    documentCategory: str | None = Query(
        None, description="系统分类筛选: attention/general/archive/failed"
    ),
    notificationRequired: bool | None = Query(None, description="是否需要通知"),
    sourceId: uuid.UUID | None = Query(None, description="数据源 ID"),
    channelId: uuid.UUID | None = Query(None, description="栏目 ID"),
    firstFoundFrom: date | None = Query(None, description="首次发现日期起始"),
    firstFoundTo: date | None = Query(None, description="首次发现日期截止"),
    regulationType: str | None = Query(None, description="法规类型筛选"),
    sortBy: str = Query("publish_date", description="排序字段"),
    sortOrder: str = Query("desc", description="排序方向"),
    page: int = Query(1, ge=1, description="页码"),
    pageSize: int = Query(20, ge=1, le=100, description="每页条数"),
    db: AsyncSession = Depends(get_db),
):
    """获取法规文档列表，支持多种筛选条件、排序和分页。"""
    documents, total = await repo.get_documents_with_filters(
        db=db,
        keyword=keyword,
        publish_date_from=publishDateFrom,
        publish_date_to=publishDateTo,
        status_text=statusText,
        classification=classification,
        is_new=isNew,
        impact_level=impactLevel,
        document_category=documentCategory,
        notification_required=notificationRequired,
        source_id=sourceId,
        channel_id=channelId,
        first_found_from=firstFoundFrom,
        first_found_to=firstFoundTo,
        regulation_type=regulationType,
        sort_by=sortBy,
        sort_order=sortOrder,
        page=page,
        page_size=pageSize,
    )

    items = []
    for doc in documents:
        impact_data = _extract_impact_data(doc)
        items.append(
            {
                "id": str(doc.id),
                "sourceId": str(doc.source_id),
                "channelId": str(doc.channel_id),
                "documentId": doc.document_id,
                "title": doc.title,
                "publishDate": doc.publish_date.isoformat()
                if doc.publish_date
                else None,
                "statusText": doc.status_text,
                "classification": doc.classification,
                "originalUrl": doc.original_url,
                "isNew": doc.is_new,
                "isRead": doc.is_read,
                "firstFoundAt": doc.first_found_at.isoformat()
                if doc.first_found_at
                else None,
                "lastCheckedAt": doc.last_checked_at.isoformat()
                if doc.last_checked_at
                else None,
                "createdAt": doc.created_at.isoformat() if doc.created_at else None,
                "aiSummary": doc.ai_summary,
                "aiKeyPoints": doc.ai_key_points,
                "aiRelevanceScore": doc.ai_relevance_score,
                "aiAnalyzedAt": doc.ai_analyzed_at.isoformat()
                if doc.ai_analyzed_at
                else None,
                "aiAnalysisStatus": doc.ai_analysis_status,
                "impact_level": impact_data["impact_level"],
                "impact_score": impact_data["impact_score"],
                "notification_required": impact_data["notification_required"],
                "documentCategory": doc.document_category,
                "documentCategoryName": get_category_display_name(
                    doc.document_category or "general"
                ),
            }
        )

    return {
        "code": 200,
        "message": "success",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "pageSize": pageSize,
            "totalPages": (total + pageSize - 1) // pageSize if pageSize > 0 else 0,
        },
    }


# ============ 法规文档详情 ============


@router.get("/regulatory-documents/{doc_id}/detail", summary="法规文档详情")
async def get_document_detail(
    current_user: CurrentUser, doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    """获取法规文档详情，包含来源和栏目名称。"""
    doc_detail = await repo.get_document_detail(db, doc_id)
    if not doc_detail:
        return error_response("文档不存在", status_code=404)

    # 获取相关法规
    doc = await repo.get_document_by_id(db, doc_id)
    related_docs = []
    if doc:
        related = await repo.get_related_documents(db, doc, limit=5)
        related_docs = [
            {
                "id": str(r.id),
                "title": r.title,
                "publishDate": r.publish_date.isoformat() if r.publish_date else None,
                "classification": r.classification,
            }
            for r in related
        ]

    doc_detail["relatedDocuments"] = related_docs

    # 添加系统分类显示名称
    doc_detail["documentCategoryName"] = get_category_display_name(
        doc_detail.get("documentCategory") or "general"
    )

    return success_response(doc_detail)


# ============ 法规文档导出 ============


@router.get("/regulatory-documents/export", summary="导出法规文档为 Excel")
async def export_documents(
    current_user: CurrentUser,
    format: str = Query("xlsx", description="导出格式: xlsx"),
    keyword: str | None = Query(None),
    publishDateFrom: date | None = Query(None),
    publishDateTo: date | None = Query(None),
    statusText: str | None = Query(None),
    classification: str | None = Query(None),
    isNew: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """导出法规文档为 Excel 文件。"""
    documents, _ = await repo.get_documents_with_filters(
        db=db,
        keyword=keyword,
        publish_date_from=publishDateFrom,
        publish_date_to=publishDateTo,
        status_text=statusText,
        classification=classification,
        is_new=isNew,
        page=1,
        page_size=10000,  # 导出全部
    )

    if format == "xlsx":
        excel_file = await generate_regulatory_excel(documents)
        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=regulatory_documents.xlsx"
            },
        )
    else:
        return error_response("不支持的导出格式", status_code=400)


# ============ 标记文档为已读 ============


@router.patch("/regulatory-documents/{doc_id}/read", summary="标记文档为已读")
async def mark_document_read(
    current_user: CurrentUser, doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    """标记单个文档为已读"""
    doc = await repo.get_document_by_id(db, doc_id)
    if not doc:
        return error_response("文档不存在", status_code=404)

    await repo.update_document(db, doc_id, {"is_new": False, "is_read": True})
    await db.commit()
    return success_response({"id": str(doc_id), "marked": True})


@router.post("/regulatory-documents/batch-read", summary="批量标记文档已读")
async def batch_mark_read(
    current_user: CurrentUser,
    request: BatchReadRequest,
    db: AsyncSession = Depends(get_db),
):
    """批量标记文档为已读"""
    count = await repo.batch_mark_read(db, request.documentIds)
    await db.commit()
    return success_response({"updatedCount": count})


# ============ 同步任务触发 ============


@router.post("/sync-jobs/trigger", summary="手动触发同步任务")
async def trigger_sync_job(
    current_user: CurrentUser,
    request: SyncTriggerRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """手动触发数据源同步任务（后台异步执行，含自动 AI 分析）"""
    source = await repo.get_data_source_by_code(db, request.sourceCode)
    if not source:
        return error_response(f"数据源 {request.sourceCode} 不存在", status_code=404)

    channel = await repo.get_channel_by_code(db, source.id, request.channelCode)
    if not channel:
        return error_response(f"栏目 {request.channelCode} 不存在", status_code=404)

    if not source.enabled or not channel.enabled:
        return error_response("数据源或栏目已禁用", status_code=400)

    # 创建同步任务记录
    job = await repo.create_sync_job(
        db,
        {
            "source_id": source.id,
            "channel_id": channel.id,
            "job_type": "manual_sync",
            "status": "pending",
        },
    )
    await db.commit()

    # 后台执行同步（不阻塞响应）
    # AI 分析现在在 sync_service 中自动执行
    from app.modules.registration.regulatory_tracker.services.sync_service import run_sync_job

    async def _run_sync(current_user: CurrentUser):
        from app.core.database import async_session_factory

        async with async_session_factory() as session:
            await run_sync_job(
                db=session,
                source=source,
                channel=channel,
                job_type="manual_sync",
                start_page=request.startPage,
                end_page=request.endPage,
            )

    background_tasks.add_task(_run_sync)

    return {
        "code": 200,
        "message": "同步任务已创建（将自动分析新增法规）",
        "data": {
            "jobId": str(job.id),
            "status": "pending",
            "sourceCode": request.sourceCode,
            "channelCode": request.channelCode,
        },
    }


# ============ 同步任务列表 ============


@router.get("/sync-jobs", summary="同步任务列表")
async def list_sync_jobs(
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取同步任务日志列表"""
    jobs, total = await repo.get_sync_jobs_list(db=db, page=page, page_size=pageSize)

    items = []
    for job in jobs:
        items.append(
            {
                "id": str(job.id),
                "sourceId": str(job.source_id),
                "channelId": str(job.channel_id),
                "jobType": job.job_type,
                "startedAt": job.started_at.isoformat() if job.started_at else None,
                "finishedAt": job.finished_at.isoformat() if job.finished_at else None,
                "status": job.status,
                "totalPages": job.total_pages,
                "checkedCount": job.checked_count,
                "newCount": job.new_count,
                "updatedCount": job.updated_count,
                "errorMessage": job.error_message,
                "createdAt": job.created_at.isoformat() if job.created_at else None,
            }
        )

    return {
        "code": 200,
        "message": "success",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "pageSize": pageSize,
            "totalPages": (total + pageSize - 1) // pageSize if pageSize > 0 else 0,
        },
    }
