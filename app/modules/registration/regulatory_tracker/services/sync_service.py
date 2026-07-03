"""同步服务 - 处理采集数据入库逻辑（与 AI 分析解耦）。"""

import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tasks import spawn_task
from app.modules.registration.regulatory_tracker import repository as repo
from app.modules.registration.regulatory_tracker.crawler.cde_crawler import (
    CdeDomesticGuidelineAdapter,
)
from app.modules.registration.regulatory_tracker.crawler.nmpa_crawler import NmpaRecordAdapter
from app.modules.registration.regulatory_tracker.models import DataChannel, DataSource
from app.modules.registration.regulatory_tracker.services.ai_workflow import get_ai_workflow

logger = logging.getLogger(__name__)

# 适配器工厂：根据 source code + channel code 返回对应适配器
ADAPTER_REGISTRY = {
    ("CDE", "cde_domestic_guideline"): CdeDomesticGuidelineAdapter,
    ("NMPA", "nmpa_baxx"): NmpaRecordAdapter,
}


def _get_adapter(source: DataSource, channel: DataChannel, headless: bool = True):
    """根据数据源和栏目获取对应的爬虫适配器"""
    key = (source.code, channel.code)
    adapter_cls = ADAPTER_REGISTRY.get(key)
    if adapter_cls is None:
        raise ValueError(f"未找到适配器: source={source.code}, channel={channel.code}")
    return adapter_cls(headless=headless)


async def upsert_document(
    db: AsyncSession,
    source_id: uuid.UUID,
    channel_id: uuid.UUID,
    normalized: dict[str, Any],
) -> tuple[str, uuid.UUID]:
    """插入或更新文档。

    Returns:
        ("created", doc) | ("updated", doc_id) | ("skipped", doc_id)
    """
    document_id = normalized["document_id"]
    if not document_id:
        return ("skipped", uuid.UUID(int=0))

    existing = await repo.get_document_by_document_id(
        db, source_id, channel_id, document_id
    )

    if existing:
        # 已存在：更新 last_checked_at，标记为非新文档
        logger.debug(f"法规已存在，更新: {existing.title[:40]}...")
        await repo.update_document(
            db,
            existing.id,
            {
                "last_checked_at": datetime.now(UTC),
                "is_new": False,
                "title": normalized.get("title", existing.title),
                "publish_date": normalized.get("publish_date") or existing.publish_date,
                "status_text": normalized.get("status_text", existing.status_text),
                "classification": normalized.get(
                    "classification", existing.classification
                ),
                "raw_data": normalized.get("raw_data", existing.raw_data),
            },
        )
        return ("updated", existing.id)

    # 不存在：新增
    logger.info(f"法规入库: {normalized.get('title', '')[:40]}...")
    doc = await repo.create_document(
        db,
        {
            "source_id": source_id,
            "channel_id": channel_id,
            "document_id": document_id,
            "title": normalized.get("title", ""),
            "publish_date": normalized.get("publish_date"),
            "status_text": normalized.get("status_text"),
            "classification": normalized.get("classification"),
            "original_url": normalized.get("original_url"),
            "raw_data": normalized.get("raw_data"),
            "is_new": True,
            "first_found_at": datetime.now(UTC),
            "last_checked_at": datetime.now(UTC),
        },
    )
    await db.flush()  # 确保 doc.id 可用
    return ("created", doc)


async def sync_page_to_db(
    db: AsyncSession,
    adapter,  # CdeDomesticGuidelineAdapter | NmpaRecordAdapter
    source: DataSource,
    channel: DataChannel,
    job_id: uuid.UUID,
    page_num: int,
) -> dict:
    """同步单页数据到数据库。

    Returns:
        {"checked": int, "new": int, "updated": int, "failed": int, "new_doc_ids": list}
    """
    stats = {"checked": 0, "new": 0, "updated": 0, "failed": 0, "new_doc_ids": []}

    # 记录分页开始
    page_record = await repo.create_sync_job_page(
        db,
        {
            "sync_job_id": job_id,
            "page_number": page_num,
            "page_size": 10,
            "total_records_on_page": 0,
            "new_records": 0,
            "status": "running",
            "started_at": datetime.now(UTC),
        },
    )

    try:
        logger.info(f"开始同步第 {page_num} 页...")
        result = await adapter.sync_page(page_num)

        if not result.get("success"):
            await repo.update_sync_job_page(
                db,
                page_record.id,
                {
                    "status": "failed",
                    "finished_at": datetime.now(UTC),
                    "error_message": result.get("error", "未知错误"),
                },
            )
            return stats

        records = result.get("records", [])
        total_on_page = len(records)
        new_on_page = 0

        await repo.update_sync_job_page(
            db,
            page_record.id,
            {
                "total_records_on_page": total_on_page,
            },
        )

        for record in records:
            stats["checked"] += 1
            try:
                normalized = adapter.normalize_record(record)
                action, result = await upsert_document(
                    db, source.id, channel.id, normalized
                )
                if action == "created":
                    stats["new"] += 1
                    new_on_page += 1
                    # 收集新增文档 ID（用于后续提交 AI 分析）
                    stats["new_doc_ids"].append(result.id)
                elif action == "updated":
                    stats["updated"] += 1
            except Exception as e:
                stats["failed"] += 1
                logger.error(f"处理记录失败: {record.get('zdyzIdCODE', 'N/A')}: {e}")

        await repo.update_sync_job_page(
            db,
            page_record.id,
            {
                "new_records": new_on_page,
                "status": "synced",
                "finished_at": datetime.now(UTC),
            },
        )

    except Exception as e:
        logger.exception(f"同步第 {page_num} 页异常")
        await repo.update_sync_job_page(
            db,
            page_record.id,
            {
                "status": "failed",
                "finished_at": datetime.now(UTC),
                "error_message": str(e),
            },
        )

    return stats


async def run_sync_job(
    db: AsyncSession,
    source: DataSource,
    channel: DataChannel,
    job_type: str,
    start_page: int = 1,
    end_page: int | None = None,
    headless: bool = True,
) -> dict[str, Any]:
    """执行同步任务（与 AI 分析解耦）。

    同步完成后，将新增文档提交到 AI 工作流进行后台分析。
    同步任务本身不等待 AI 分析完成。

    Args:
        db: 数据库会话
        source: 数据源
        channel: 栏目
        job_type: 任务类型 (backfill/daily_sync/manual_sync/test)
        start_page: 起始页码
        end_page: 结束页码（None 表示全部）
        headless: 是否无头模式

    Returns:
        同步结果摘要
    """
    sync_start_time = time.time()
    logger.info(f"===== 同步任务开始: {source.code}/{channel.code} =====")

    # 创建同步任务
    job = await repo.create_sync_job(
        db,
        {
            "source_id": source.id,
            "channel_id": channel.id,
            "job_type": job_type,
            "status": "running",
            "started_at": datetime.now(UTC),
        },
    )

    total_stats = {"checked": 0, "new": 0, "updated": 0, "failed": 0}
    new_doc_ids = []  # 收集所有新增文档 ID
    error_message = None

    try:
        adapter = _get_adapter(source, channel, headless=headless)
        async with adapter as adapter_ctx:
            # 如果 end_page 为 None，先获取总页数
            if end_page is None:
                total_pages = await adapter_ctx.get_total_pages()
                if total_pages is None:
                    raise RuntimeError("无法获取总页数")
                end_page = total_pages
                await repo.update_sync_job(db, job.id, {"total_pages": end_page})

            # 逐页同步
            for page_num in range(start_page, end_page + 1):
                logger.info(f"同步第 {page_num}/{end_page} 页...")
                stats = await sync_page_to_db(
                    db, adapter_ctx, source, channel, job.id, page_num
                )
                total_stats["checked"] += stats["checked"]
                total_stats["new"] += stats["new"]
                total_stats["updated"] += stats["updated"]
                total_stats["failed"] += stats["failed"]
                new_doc_ids.extend(stats.get("new_doc_ids", []))

                # 每页提交一次
                await db.commit()

        # 确定最终状态
        if total_stats["failed"] > 0 and total_stats["checked"] > 0:
            status = "partial_failed"
        elif total_stats["checked"] == 0:
            status = "failed"
            error_message = "未检查到任何记录"
        else:
            status = "success"

    except Exception as e:
        logger.exception("同步任务异常")
        status = "failed"
        error_message = str(e)

    # 更新任务状态
    await repo.update_sync_job(
        db,
        job.id,
        {
            "status": status,
            "finished_at": datetime.now(UTC),
            "checked_count": total_stats["checked"],
            "new_count": total_stats["new"],
            "updated_count": total_stats["updated"],
            "error_message": error_message,
        },
    )
    await db.commit()

    sync_elapsed = time.time() - sync_start_time
    logger.info(
        f"数据同步完成: 检查={total_stats['checked']} 新增={total_stats['new']} "
        f"更新={total_stats['updated']} 失败={total_stats['failed']} 耗时={sync_elapsed:.1f}s"
    )

    # ===== 提交 AI 分析（后台异步，不阻塞同步任务） =====
    if new_doc_ids and status == "success":
        logger.info(f"提交 {len(new_doc_ids)} 条新增法规到 AI 工作流")
        try:
            workflow = get_ai_workflow()
            # 注意：这里不 await，让 AI 分析在后台执行
            # 在实际部署中，这应该是一个独立的后台任务或队列
            spawn_task(workflow.submit_documents(new_doc_ids), name="submit-documents")
        except Exception as e:
            logger.error(f"提交 AI 工作流失败: {e}", exc_info=True)

    logger.info(
        f"===== 同步任务完成: {source.code}/{channel.code} | "
        f"耗时={sync_elapsed:.1f}s | 新增={total_stats['new']} ====="
    )

    return {
        "job_id": str(job.id),
        "status": status,
        "checked": total_stats["checked"],
        "new": total_stats["new"],
        "updated": total_stats["updated"],
        "failed": total_stats["failed"],
        "error": error_message,
        "new_doc_ids": new_doc_ids,
    }
