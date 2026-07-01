"""Task7 全量 AI 回填：对所有待回填法规执行 AI 分析。

使用方法：
    cd dazah-backend
    python scripts/task7_full_backfill.py [--batch-size 20] [--dry-run]

支持断点续跑：中断后重新运行即可，已完成的文档会自动跳过。
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
from datetime import UTC, datetime

# 先加载 .env.development 到 os.environ
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_env_file = os.path.join(_project_root, ".env.development")
if os.path.exists(_env_file):
    with open(_env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

sys.path.insert(0, _project_root)

import argparse

from sqlalchemy import and_, func, select

from app.core.database import async_session_factory
from app.modules.regulatory_tracker.models.regulatory_document import RegulatoryDocument
from app.modules.regulatory_tracker.services.ai_analysis_service import (
    analyze_and_update,
)
from app.platform.identity.models import User  # noqa: F401

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# 全局停止标志
_stop_requested = False


def _signal_handler(signum, frame):
    global _stop_requested
    logger.warning(f"收到信号 {signum}，将在当前文档完成后优雅停止...")
    _stop_requested = True


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


async def get_pending_count(db) -> int:
    """获取待分析文档数量。"""
    stmt = (
        select(func.count())
        .select_from(RegulatoryDocument)
        .where(
            and_(
                not RegulatoryDocument.is_deleted,
                RegulatoryDocument.ai_analysis_status is None,
            )
        )
    )
    result = await db.execute(stmt)
    return result.scalar()


async def get_pending_documents(db, batch_size: int):
    """获取一批待分析文档。"""
    stmt = (
        select(RegulatoryDocument)
        .where(
            and_(
                not RegulatoryDocument.is_deleted,
                RegulatoryDocument.ai_analysis_status is None,
            )
        )
        .order_by(RegulatoryDocument.first_found_at.desc())
        .limit(batch_size)
    )

    result = await db.execute(stmt)
    return result.scalars().all()


async def full_backfill(batch_size: int = 20, dry_run: bool = False):
    """全量 AI 回填。"""
    # 验证 LLM 配置
    api_key = os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL")
    base_url = os.getenv("LLM_BASE_URL")
    logger.info(
        f"LLM 配置: model={model}, base_url={base_url}, api_key={'***' + api_key[-6:] if api_key else 'MISSING'}"
    )

    if not api_key:
        logger.error("LLM_API_KEY 未设置！")
        return None

    progress_file = os.path.join(_project_root, "task7_backfill_progress.json")

    # 加载已有进度
    overall_start = time.time()
    total_success = 0
    total_failed = 0
    total_skipped = 0

    if os.path.exists(progress_file):
        with open(progress_file) as f:
            prev = json.load(f)
            total_success = prev.get("total_success", 0)
            total_failed = prev.get("total_failed", 0)
            total_skipped = prev.get("total_skipped", 0)
            logger.info(
                f"恢复进度: 已完成={total_success}, 失败={total_failed}, 跳过={total_skipped}"
            )

    if dry_run:
        logger.info("=== DRY RUN 模式：仅统计待处理数量，不执行分析 ===")
        async with async_session_factory() as db:
            pending = await get_pending_count(db)
            logger.info(f"待分析文档数: {pending}")
        return {"pending": pending}

    batch_num = 0

    while not _stop_requested:
        batch_num += 1
        batch_start = time.time()
        batch_success = 0
        batch_failed = 0

        async with async_session_factory() as db:
            pending_count = await get_pending_count(db)
            if pending_count == 0:
                logger.info("✅ 所有文档已处理完成！")
                break

            logger.info(
                f"--- 批次 {batch_num} | 剩余 {pending_count} 条 | 累计成功={total_success} 失败={total_failed} ---"
            )

            documents = await get_pending_documents(db, batch_size)
            if not documents:
                logger.info("没有更多待处理文档")
                break

            for i, doc in enumerate(documents, 1):
                if _stop_requested:
                    logger.warning("停止请求已收到，优雅退出...")
                    break

                doc_start = time.time()
                doc_num = total_success + total_failed + total_skipped + i
                logger.info(
                    f"[{doc_num}] ({i}/{len(documents)}) 分析: {doc.title[:50]}..."
                )

                try:
                    success = await analyze_and_update(db, doc)
                    elapsed = time.time() - doc_start

                    if success:
                        batch_success += 1
                        total_success += 1
                        logger.info(f"  ✅ 耗时 {elapsed:.1f}s")
                    else:
                        batch_failed += 1
                        total_failed += 1
                        logger.warning(f"  ❌ 失败 耗时 {elapsed:.1f}s")
                except Exception as e:
                    batch_failed += 1
                    total_failed += 1
                    elapsed = time.time() - doc_start
                    logger.error(f"  ❌ 异常: {e} 耗时 {elapsed:.1f}s")

            # 保存进度
            progress = {
                "last_updated": datetime.now(UTC).isoformat(),
                "model": model,
                "batch_num": batch_num,
                "total_success": total_success,
                "total_failed": total_failed,
                "total_skipped": total_skipped,
                "remaining_after_batch": pending_count - len(documents),
                "elapsed_seconds": round(time.time() - overall_start, 1),
                "batch_elapsed_seconds": round(time.time() - batch_start, 1),
            }
            with open(progress_file, "w", encoding="utf-8") as f:
                json.dump(progress, f, ensure_ascii=False, indent=2)

            batch_elapsed = time.time() - batch_start
            avg_per_doc = batch_elapsed / max(len(documents), 1)
            remaining = pending_count - len(documents)
            eta_hours = (remaining * avg_per_doc) / 3600

            logger.info(
                f"批次 {batch_num} 完成: 成功={batch_success} 失败={batch_failed} "
                f"耗时={batch_elapsed:.0f}s 平均={avg_per_doc:.1f}s/条 "
                f"ETA={eta_hours:.1f}h"
            )

    # 最终报告
    total_elapsed = time.time() - overall_start
    report = {
        "completed_at": datetime.now(UTC).isoformat(),
        "model": model,
        "total_success": total_success,
        "total_failed": total_failed,
        "total_skipped": total_skipped,
        "total_elapsed_seconds": round(total_elapsed, 1),
        "stopped_by_signal": _stop_requested,
    }

    report_path = os.path.join(_project_root, "task7_backfill_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info("=" * 60)
    logger.info(
        f"全量回填结束: 成功={total_success} 失败={total_failed} 跳过={total_skipped}"
    )
    logger.info(f"总耗时: {total_elapsed:.0f}s ({total_elapsed / 3600:.1f}h)")
    if _stop_requested:
        logger.info("（因停止信号退出，重新运行即可续跑）")
    logger.info(f"报告: {report_path}")
    logger.info("=" * 60)

    return report


def main():
    parser = argparse.ArgumentParser(description="Task7 全量 AI 回填")
    parser.add_argument(
        "--batch-size", type=int, default=20, help="每批处理数量 (default: 20)"
    )
    parser.add_argument("--dry-run", action="store_true", help="仅统计，不执行分析")
    args = parser.parse_args()

    report = asyncio.run(
        full_backfill(batch_size=args.batch_size, dry_run=args.dry_run)
    )
    sys.exit(0 if report else 1)


if __name__ == "__main__":
    main()
