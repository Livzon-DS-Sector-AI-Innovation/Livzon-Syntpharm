"""Regulatory Tracker repository layer."""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.registration.regulatory_tracker.models import (
    DataChannel,
    DataSource,
    RegulatoryDocument,
    SyncJob,
    SyncJobPage,
)

# ============ DataSource ============


async def get_data_source_by_code(db: AsyncSession, code: str) -> DataSource | None:
    """根据编码获取数据源"""
    result = await db.execute(
        select(DataSource).where(
            DataSource.code == code,
            DataSource.is_deleted == False,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def get_data_source_by_id(
    db: AsyncSession, source_id: uuid.UUID
) -> DataSource | None:
    """根据ID获取数据源"""
    result = await db.execute(
        select(DataSource).where(
            DataSource.id == source_id,
            DataSource.is_deleted == False,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


# ============ DataChannel ============


async def get_channel_by_code(
    db: AsyncSession, source_id: uuid.UUID, code: str
) -> DataChannel | None:
    """根据编码获取栏目"""
    result = await db.execute(
        select(DataChannel).where(
            DataChannel.source_id == source_id,
            DataChannel.code == code,
            DataChannel.is_deleted == False,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def get_channel_by_id(
    db: AsyncSession, channel_id: uuid.UUID
) -> DataChannel | None:
    """根据ID获取栏目"""
    result = await db.execute(
        select(DataChannel).where(
            DataChannel.id == channel_id,
            DataChannel.is_deleted == False,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


# ============ RegulatoryDocument ============


async def get_document_by_document_id(
    db: AsyncSession,
    source_id: uuid.UUID,
    channel_id: uuid.UUID,
    document_id: str,
) -> RegulatoryDocument | None:
    """根据 document_id 查询文档（去重键）"""
    result = await db.execute(
        select(RegulatoryDocument).where(
            RegulatoryDocument.source_id == source_id,
            RegulatoryDocument.channel_id == channel_id,
            RegulatoryDocument.document_id == document_id,
            RegulatoryDocument.is_deleted == False,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def create_document(db: AsyncSession, data: dict[str, Any]) -> RegulatoryDocument:
    """创建新文档"""
    doc = RegulatoryDocument(**data)
    db.add(doc)
    await db.flush()
    return doc


async def update_document(
    db: AsyncSession, doc_id: uuid.UUID, data: dict[str, Any]
) -> RegulatoryDocument | None:
    """更新文档"""
    result = await db.execute(
        select(RegulatoryDocument).where(RegulatoryDocument.id == doc_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        return None
    for key, value in data.items():
        if hasattr(doc, key):
            setattr(doc, key, value)
    await db.flush()
    return doc


async def count_documents(
    db: AsyncSession, source_id: uuid.UUID, channel_id: uuid.UUID
) -> int:
    """统计文档数量"""
    result = await db.execute(
        select(func.count(RegulatoryDocument.id)).where(
            RegulatoryDocument.source_id == source_id,
            RegulatoryDocument.channel_id == channel_id,
            RegulatoryDocument.is_deleted == False,  # noqa: E712
        )
    )
    return result.scalar() or 0


# ============ SyncJob ============


async def create_sync_job(db: AsyncSession, data: dict[str, Any]) -> SyncJob:
    """创建同步任务"""
    job = SyncJob(**data)
    db.add(job)
    await db.flush()
    return job


async def get_sync_job_by_id(db: AsyncSession, job_id: uuid.UUID) -> SyncJob | None:
    """根据ID获取同步任务"""
    result = await db.execute(select(SyncJob).where(SyncJob.id == job_id))
    return result.scalar_one_or_none()


async def update_sync_job(
    db: AsyncSession, job_id: uuid.UUID, data: dict[str, Any]
) -> SyncJob | None:
    """更新同步任务"""
    job = await get_sync_job_by_id(db, job_id)
    if not job:
        return None
    for key, value in data.items():
        if hasattr(job, key):
            setattr(job, key, value)
    await db.flush()
    return job


# ============ SyncJobPage ============


async def create_sync_job_page(db: AsyncSession, data: dict[str, Any]) -> SyncJobPage:
    """创建同步任务分页记录"""
    page = SyncJobPage(**data)
    db.add(page)
    await db.flush()
    return page


async def update_sync_job_page(
    db: AsyncSession, page_id: uuid.UUID, data: dict[str, Any]
) -> SyncJobPage | None:
    """更新同步任务分页记录"""
    result = await db.execute(select(SyncJobPage).where(SyncJobPage.id == page_id))
    page = result.scalar_one_or_none()
    if not page:
        return None
    for key, value in data.items():
        if hasattr(page, key):
            setattr(page, key, value)
    await db.flush()
    return page


# ============ API 查询方法 ============


async def get_summary_stats(db: AsyncSession) -> dict[str, Any]:
    """获取统计摘要数据"""
    from datetime import date

    # 总文档数
    total_result = await db.execute(
        select(func.count(RegulatoryDocument.id)).where(
            RegulatoryDocument.is_deleted == False  # noqa: E712
        )
    )
    total_count = total_result.scalar() or 0

    # 今日新增数
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_new_result = await db.execute(
        select(func.count(RegulatoryDocument.id)).where(
            RegulatoryDocument.is_deleted == False,  # noqa: E712
            RegulatoryDocument.first_found_at >= today_start,
        )
    )
    today_new_count = today_new_result.scalar() or 0

    # 未读新增数
    unread_result = await db.execute(
        select(func.count(RegulatoryDocument.id)).where(
            RegulatoryDocument.is_deleted == False,  # noqa: E712
            RegulatoryDocument.is_new == True,  # noqa: E712
        )
    )
    unread_new_count = unread_result.scalar() or 0

    # 最近同步任务
    last_sync_result = await db.execute(
        select(SyncJob)
        .where(SyncJob.finished_at.isnot(None))
        .order_by(SyncJob.finished_at.desc())
        .limit(1)
    )
    last_sync = last_sync_result.scalar_one_or_none()

    return {
        "totalCount": total_count,
        "todayNewCount": today_new_count,
        "unreadNewCount": unread_new_count,
        "lastSyncTime": last_sync.finished_at.isoformat()
        if last_sync and last_sync.finished_at
        else None,
        "lastSyncStatus": last_sync.status if last_sync else None,
    }


async def get_documents_with_filters(
    db: AsyncSession,
    keyword: str | None = None,
    publish_date_from: date | None = None,
    publish_date_to: date | None = None,
    status_text: str | None = None,
    classification: str | None = None,
    is_new: bool | None = None,
    impact_level: str | None = None,
    document_category: str | None = None,
    notification_required: bool | None = None,
    source_id: uuid.UUID | None = None,
    channel_id: uuid.UUID | None = None,
    first_found_from: "date | None" = None,
    first_found_to: "date | None" = None,
    regulation_type: "str | None" = None,
    sort_by: str = "publish_date",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[RegulatoryDocument], int]:
    """带筛选条件的文档列表查询（支持来源/栏目筛选和排序）"""
    query = select(RegulatoryDocument).where(
        RegulatoryDocument.is_deleted == False  # noqa: E712
    )
    count_query = select(func.count(RegulatoryDocument.id)).where(
        RegulatoryDocument.is_deleted == False  # noqa: E712
    )

    # 应用筛选条件
    if keyword:
        keyword_filter = RegulatoryDocument.title.ilike(f"%{keyword}%")
        query = query.where(keyword_filter)
        count_query = count_query.where(keyword_filter)

    if publish_date_from:
        date_filter = RegulatoryDocument.publish_date >= publish_date_from
        query = query.where(date_filter)
        count_query = count_query.where(date_filter)

    if publish_date_to:
        date_filter = RegulatoryDocument.publish_date <= publish_date_to
        query = query.where(date_filter)
        count_query = count_query.where(date_filter)

    if status_text:
        status_filter = RegulatoryDocument.status_text == status_text
        query = query.where(status_filter)
        count_query = count_query.where(status_filter)

    if classification:
        class_filter = RegulatoryDocument.classification.ilike(f"%{classification}%")
        query = query.where(class_filter)
        count_query = count_query.where(class_filter)

    if is_new is not None:
        new_filter = RegulatoryDocument.is_new == is_new
        query = query.where(new_filter)
        count_query = count_query.where(new_filter)

    if source_id is not None:
        source_filter = RegulatoryDocument.source_id == source_id
        query = query.where(source_filter)
        count_query = count_query.where(source_filter)

    if channel_id is not None:
        channel_filter = RegulatoryDocument.channel_id == channel_id
        query = query.where(channel_filter)
        count_query = count_query.where(channel_filter)

    # 首次发现日期筛选
    if first_found_from:
        ff_filter = RegulatoryDocument.first_found_at >= func.date(first_found_from)
        query = query.where(ff_filter)
        count_query = count_query.where(ff_filter)

    if first_found_to:
        ff_filter = RegulatoryDocument.first_found_at < func.date(
            first_found_to
        ) + text("INTERVAL '1 day'")
        query = query.where(ff_filter)
        count_query = count_query.where(ff_filter)

    # 法规类型筛选（基于 ai_key_points JSONB）
    if regulation_type:
        rt_filter = (
            RegulatoryDocument.ai_key_points["regulation_type"].astext
            == regulation_type
        )
        query = query.where(rt_filter)
        count_query = count_query.where(rt_filter)

    # 影响等级筛选（基于 ai_relevance_score）
    if impact_level:
        if impact_level == "unanalyzed":
            # 未分析：ai_analysis_status 为 null 或不是 completed
            unanalyzed_filter = (RegulatoryDocument.ai_analysis_status is None) | (
                RegulatoryDocument.ai_analysis_status != "completed"
            )
            query = query.where(unanalyzed_filter)
            count_query = count_query.where(unanalyzed_filter)
        elif impact_level == "high":
            level_filter = RegulatoryDocument.ai_relevance_score >= 0.80
            query = query.where(level_filter)
            count_query = count_query.where(level_filter)
        elif impact_level == "medium":
            level_filter = (RegulatoryDocument.ai_relevance_score >= 0.50) & (
                RegulatoryDocument.ai_relevance_score < 0.80
            )
            query = query.where(level_filter)
            count_query = count_query.where(level_filter)
        elif impact_level == "low":
            level_filter = (RegulatoryDocument.ai_relevance_score >= 0.20) & (
                RegulatoryDocument.ai_relevance_score < 0.50
            )
            query = query.where(level_filter)
            count_query = count_query.where(level_filter)
        elif impact_level == "none":
            level_filter = RegulatoryDocument.ai_relevance_score < 0.20
            query = query.where(level_filter)
            count_query = count_query.where(level_filter)

    # 系统分类筛选
    if document_category:
        category_filter = RegulatoryDocument.document_category == document_category
        query = query.where(category_filter)
        count_query = count_query.where(category_filter)

    # 是否需要通知筛选（基于 ai_key_points JSONB）
    if notification_required is not None:
        if notification_required:
            notif_filter = (
                RegulatoryDocument.ai_key_points["notification_required"].astext
                == "true"
            )
            query = query.where(notif_filter)
            count_query = count_query.where(notif_filter)
        else:
            notif_filter = (
                RegulatoryDocument.ai_key_points["notification_required"].astext
                == "false"
            ) | (
                RegulatoryDocument.ai_key_points["notification_required"].astext is None
            )
            query = query.where(notif_filter)
            count_query = count_query.where(notif_filter)

    # 获取总数
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 排序
    sort_column = getattr(RegulatoryDocument, sort_by, RegulatoryDocument.publish_date)
    if sort_order == "asc":
        query = query.order_by(sort_column.asc().nulls_last())
    else:
        query = query.order_by(sort_column.desc().nulls_last())

    # 分页
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    documents = list(result.scalars().all())

    return documents, total


async def get_document_by_id(
    db: AsyncSession, doc_id: uuid.UUID
) -> RegulatoryDocument | None:
    """根据 ID 获取文档"""
    result = await db.execute(
        select(RegulatoryDocument).where(
            RegulatoryDocument.id == doc_id,
            RegulatoryDocument.is_deleted == False,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def get_sync_jobs_list(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[SyncJob], int]:
    """获取同步任务列表"""
    # 获取总数
    count_result = await db.execute(select(func.count(SyncJob.id)))
    total = count_result.scalar() or 0

    # 分页查询
    offset = (page - 1) * page_size
    result = await db.execute(
        select(SyncJob)
        .order_by(SyncJob.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    jobs = list(result.scalars().all())

    return jobs, total


# ============ Dashboard 查询方法 ============


async def get_dashboard_stats(db: AsyncSession) -> dict[str, Any]:
    """获取 Dashboard 统计数据：今日新增、本周新增、未读、AI 已分析"""
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    week_start = datetime.combine(
        today - __import__("datetime").timedelta(days=6), datetime.min.time()
    )

    # 今日新增
    today_result = await db.execute(
        select(func.count(RegulatoryDocument.id)).where(
            RegulatoryDocument.is_deleted == False,  # noqa: E712
            RegulatoryDocument.first_found_at >= today_start,
        )
    )
    today_new_count = today_result.scalar() or 0

    # 本周新增
    week_result = await db.execute(
        select(func.count(RegulatoryDocument.id)).where(
            RegulatoryDocument.is_deleted == False,  # noqa: E712
            RegulatoryDocument.first_found_at >= week_start,
        )
    )
    week_new_count = week_result.scalar() or 0

    # 未读
    unread_result = await db.execute(
        select(func.count(RegulatoryDocument.id)).where(
            RegulatoryDocument.is_deleted == False,  # noqa: E712
            RegulatoryDocument.is_new == True,  # noqa: E712
        )
    )
    unread_count = unread_result.scalar() or 0

    # AI 已分析
    ai_result = await db.execute(
        select(func.count(RegulatoryDocument.id)).where(
            RegulatoryDocument.is_deleted == False,  # noqa: E712
            RegulatoryDocument.ai_analysis_status == "completed",
        )
    )
    ai_count = ai_result.scalar() or 0

    return {
        "todayNewCount": today_new_count,
        "weekNewCount": week_new_count,
        "unreadCount": unread_count,
        "aiAnalyzedCount": ai_count,
    }


async def get_7day_trend(db: AsyncSession) -> list[dict[str, Any]]:
    """获取近 7 天每日新增法规数量"""
    from datetime import timedelta

    today = date.today()
    trend = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day + timedelta(days=1), datetime.min.time())
        result = await db.execute(
            select(func.count(RegulatoryDocument.id)).where(
                RegulatoryDocument.is_deleted == False,  # noqa: E712
                RegulatoryDocument.first_found_at >= day_start,
                RegulatoryDocument.first_found_at < day_end,
            )
        )
        count = result.scalar() or 0
        trend.append({"date": day.isoformat(), "count": count})
    return trend


async def get_classification_stats(db: AsyncSession) -> dict[str, int]:
    """按分类统计法规数量"""
    result = await db.execute(
        select(RegulatoryDocument.classification, func.count(RegulatoryDocument.id))
        .where(
            RegulatoryDocument.is_deleted == False,  # noqa: E712
            RegulatoryDocument.classification.isnot(None),
        )
        .group_by(RegulatoryDocument.classification)
        .order_by(func.count(RegulatoryDocument.id).desc())
    )
    return {row[0]: row[1] for row in result.all()}


async def get_source_status(db: AsyncSession) -> list[dict[str, Any]]:
    """获取各数据源状态（含今日新增数、最近同步时间）"""

    today_start = datetime.combine(date.today(), datetime.min.time())

    # 获取所有数据源
    sources_result = await db.execute(
        select(DataSource).where(~DataSource.is_deleted).order_by(DataSource.code)  # noqa: E712
    )
    sources = sources_result.scalars().all()

    # Phase 1 已知来源 + 未来来源占位
    known_codes = {s.code for s in sources}
    future_sources = [
        {"code": "FDA", "name": "FDA"},
        {"code": "EMA", "name": "EMA"},
    ]

    status_list = []
    for source in sources:
        # 今日新增数
        new_result = await db.execute(
            select(func.count(RegulatoryDocument.id)).where(
                RegulatoryDocument.is_deleted == False,  # noqa: E712
                RegulatoryDocument.source_id == source.id,
                RegulatoryDocument.first_found_at >= today_start,
            )
        )
        today_new = new_result.scalar() or 0

        # 最近同步时间
        sync_result = await db.execute(
            select(SyncJob)
            .where(
                SyncJob.source_id == source.id,
                SyncJob.finished_at.isnot(None),
            )
            .order_by(SyncJob.finished_at.desc())
            .limit(1)
        )
        last_sync = sync_result.scalar_one_or_none()

        status_list.append(
            {
                "code": source.code,
                "name": source.name,
                "status": "active",
                "lastSyncTime": last_sync.finished_at.isoformat()
                if last_sync and last_sync.finished_at
                else None,
                "todayNewCount": today_new,
            }
        )

    # 添加未来来源占位
    for fs in future_sources:
        if fs["code"] not in known_codes:
            status_list.append(
                {
                    "code": fs["code"],
                    "name": fs["name"],
                    "status": "future",
                    "lastSyncTime": None,
                    "todayNewCount": 0,
                }
            )

    return status_list


async def get_today_new_documents(
    db: AsyncSession, limit: int = 10
) -> list[RegulatoryDocument]:
    """获取今日新增法规列表"""
    today_start = datetime.combine(date.today(), datetime.min.time())
    result = await db.execute(
        select(RegulatoryDocument)
        .where(
            RegulatoryDocument.is_deleted == False,  # noqa: E712
            RegulatoryDocument.first_found_at >= today_start,
        )
        .order_by(RegulatoryDocument.first_found_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_document_detail(
    db: AsyncSession, doc_id: uuid.UUID
) -> dict[str, Any] | None:
    """获取法规详情（含来源、栏目名称）"""
    result = await db.execute(
        select(RegulatoryDocument).where(
            RegulatoryDocument.id == doc_id,
            RegulatoryDocument.is_deleted == False,  # noqa: E712
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        return None

    # 获取来源和栏目名称
    source = await get_data_source_by_id(db, doc.source_id)
    channel = await get_channel_by_id(db, doc.channel_id)

    # 从 raw_data 提取正文和附件
    raw_data = doc.raw_data or {}
    detail_text = (
        raw_data.get("detail_text")
        or raw_data.get("contentSummary")
        or raw_data.get("summary")
        or ""
    )

    return {
        "id": str(doc.id),
        "title": doc.title,
        "publishDate": doc.publish_date.isoformat() if doc.publish_date else None,
        "statusText": doc.status_text,
        "classification": doc.classification,
        "originalUrl": doc.original_url,
        "sourceName": source.name if source else None,
        "sourceCode": source.code if source else None,
        "channelName": channel.name if channel else None,
        "aiSummary": doc.ai_summary,
        "aiKeyPoints": doc.ai_key_points,
        "aiRelevanceScore": doc.ai_relevance_score,
        "aiAnalyzedAt": doc.ai_analyzed_at.isoformat() if doc.ai_analyzed_at else None,
        "aiAnalysisStatus": doc.ai_analysis_status,
        "detailText": detail_text[:5000] if detail_text else None,
        "firstFoundAt": doc.first_found_at.isoformat() if doc.first_found_at else None,
        "lastCheckedAt": doc.last_checked_at.isoformat()
        if doc.last_checked_at
        else None,
        "documentId": doc.document_id,
        "isNew": doc.is_new,
        "isRead": doc.is_read,
        "documentCategory": doc.document_category,
    }


async def get_related_documents(
    db: AsyncSession, doc: RegulatoryDocument, limit: int = 10
) -> list[RegulatoryDocument]:
    """获取相关法规（同分类或同栏目）"""
    result = await db.execute(
        select(RegulatoryDocument)
        .where(
            RegulatoryDocument.is_deleted == False,  # noqa: E712
            RegulatoryDocument.id != doc.id,
            (
                (RegulatoryDocument.classification == doc.classification)
                | (RegulatoryDocument.channel_id == doc.channel_id)
            ),
        )
        .order_by(RegulatoryDocument.publish_date.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def batch_mark_read(db: AsyncSession, doc_ids: list[uuid.UUID]) -> int:
    """批量标记文档为已读"""
    count = 0
    for doc_id in doc_ids:
        doc = await get_document_by_id(db, doc_id)
        if doc and (doc.is_new or not doc.is_read):
            await update_document(db, doc_id, {"is_new": False, "is_read": True})
            count += 1
    return count


# ============ 影响评估相关查询 ============


async def get_impact_stats(db: AsyncSession) -> dict[str, int]:
    """获取影响等级统计。"""
    # 高影响 (score >= 0.80)
    high_result = await db.execute(
        select(func.count(RegulatoryDocument.id)).where(
            RegulatoryDocument.is_deleted == False,  # noqa: E712
            RegulatoryDocument.ai_relevance_score >= 0.80,
        )
    )
    high_count = high_result.scalar() or 0

    # 中影响 (0.50 <= score < 0.80)
    medium_result = await db.execute(
        select(func.count(RegulatoryDocument.id)).where(
            RegulatoryDocument.is_deleted == False,  # noqa: E712
            RegulatoryDocument.ai_relevance_score >= 0.50,
            RegulatoryDocument.ai_relevance_score < 0.80,
        )
    )
    medium_count = medium_result.scalar() or 0

    # 未分析
    unanalyzed_result = await db.execute(
        select(func.count(RegulatoryDocument.id)).where(
            RegulatoryDocument.is_deleted == False,  # noqa: E712
            (RegulatoryDocument.ai_analysis_status is None)
            | (RegulatoryDocument.ai_analysis_status != "completed"),
        )
    )
    unanalyzed_count = unanalyzed_result.scalar() or 0

    return {
        "high": high_count,
        "medium": medium_count,
        "unanalyzed": unanalyzed_count,
    }


async def get_priority_documents(
    db: AsyncSession, limit: int = 10
) -> list[RegulatoryDocument]:
    """获取重点关注法规（high/medium impact）。"""
    from sqlalchemy import String, cast

    result = await db.execute(
        select(RegulatoryDocument)
        .where(
            RegulatoryDocument.is_deleted == False,  # noqa: E712
            RegulatoryDocument.ai_analysis_status == "completed",
            RegulatoryDocument.ai_key_points.isnot(None),
            cast(RegulatoryDocument.ai_key_points["impact_level"], String).in_(
                ["high", "medium"]
            ),
        )
        .order_by(RegulatoryDocument.ai_relevance_score.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# ============ Dashboard V2 查询 ============


async def get_today_new_stats(db: AsyncSession) -> dict[str, int]:
    """Get today's new document counts by impact level."""
    today_start = datetime.combine(date.today(), datetime.min.time())

    # Total today new
    total_result = await db.execute(
        select(func.count(RegulatoryDocument.id)).where(
            RegulatoryDocument.is_deleted == False,  # noqa: E712
            RegulatoryDocument.first_found_at >= today_start,
        )
    )
    total = total_result.scalar() or 0

    # High impact today (attention category)
    high_result = await db.execute(
        select(func.count(RegulatoryDocument.id)).where(
            RegulatoryDocument.is_deleted == False,  # noqa: E712
            RegulatoryDocument.first_found_at >= today_start,
            RegulatoryDocument.document_category == "attention",
        )
    )
    high = high_result.scalar() or 0

    # General today (non-attention)
    general = total - high

    return {
        "total": total,
        "high": high,
        "general": general,
    }


async def get_attention_count(db: AsyncSession) -> int:
    """Get count of documents with document_category='attention'."""
    result = await db.execute(
        select(func.count(RegulatoryDocument.id)).where(
            RegulatoryDocument.is_deleted == False,  # noqa: E712
            RegulatoryDocument.document_category == "attention",
        )
    )
    return result.scalar() or 0


async def get_priority_documents_v2(
    db: AsyncSession, limit: int = 5
) -> list[RegulatoryDocument]:
    """Get top priority documents: attention category, sorted by publish date."""
    result = await db.execute(
        select(RegulatoryDocument)
        .where(
            RegulatoryDocument.is_deleted == False,  # noqa: E712
            RegulatoryDocument.document_category == "attention",
            RegulatoryDocument.ai_analysis_status == "completed",
        )
        .order_by(
            RegulatoryDocument.publish_date.desc().nullslast(),
        )
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_source_status_v2(db: AsyncSession) -> list[dict[str, Any]]:
    """Get simplified source status for dashboard."""
    sources_result = await db.execute(
        select(DataSource)
        .where(
            DataSource.is_deleted == False  # noqa: E712
        )
        .order_by(DataSource.code)
    )
    sources = sources_result.scalars().all()

    status_list = []
    for source in sources:
        # Get latest sync job
        sync_result = await db.execute(
            select(SyncJob)
            .where(
                SyncJob.source_id == source.id,
                SyncJob.finished_at.isnot(None),
            )
            .order_by(SyncJob.finished_at.desc())
            .limit(1)
        )
        last_sync = sync_result.scalar_one_or_none()

        status_list.append(
            {
                "code": source.code,
                "name": source.name,
                "lastSyncTime": last_sync.finished_at.isoformat()
                if last_sync and last_sync.finished_at
                else None,
                "lastSyncStatus": last_sync.status if last_sync else None,
            }
        )

    return status_list


async def get_week_stats(db: AsyncSession) -> dict[str, int]:
    """近 7 天新增法规统计"""
    result = await db.execute(
        text("""
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN document_category = 'attention' THEN 1 END) as high_impact
        FROM regulatory_tracker.regulatory_documents
        WHERE is_deleted = false
          AND first_found_at >= CURRENT_DATE - INTERVAL '6 days'
    """)
    )
    row = result.fetchone()
    return {"total": row[0], "high_impact": row[1]}
