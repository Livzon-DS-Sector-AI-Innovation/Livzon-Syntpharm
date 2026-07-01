"""Task7 小批量试跑：对 10 条待回填法规执行 AI 分析。

使用方法：
    cd dazah-backend
    python scripts/task7_dry_run.py
"""

import asyncio
import json
import logging
import os
import sys
import time

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

from sqlalchemy import and_, select

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

DRY_RUN_LIMIT = 10


async def dry_run():
    """对最多 10 条 ai_analysis_status IS NULL 的法规执行 AI 分析。"""
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

    results = []
    start_all = time.time()

    async with async_session_factory() as db:
        # 查询待分析文档
        stmt = (
            select(RegulatoryDocument)
            .where(
                and_(
                    not RegulatoryDocument.is_deleted,
                    RegulatoryDocument.ai_analysis_status is None,
                )
            )
            .order_by(RegulatoryDocument.first_found_at.desc())
            .limit(DRY_RUN_LIMIT)
        )

        result = await db.execute(stmt)
        documents = result.scalars().all()

        total = len(documents)
        logger.info(f"找到 {total} 条待分析文档，开始逐条分析...")

        for i, doc in enumerate(documents, 1):
            doc_start = time.time()
            logger.info(f"[{i}/{total}] 分析: {doc.title}")

            try:
                success = await analyze_and_update(db, doc)
                elapsed = time.time() - doc_start

                # 重新从 DB 读取分析结果
                await db.refresh(doc)
                results.append(
                    {
                        "index": i,
                        "id": str(doc.id),
                        "title": doc.title,
                        "success": success,
                        "elapsed_seconds": round(elapsed, 1),
                        "error": None,
                        "ai_analysis_status": doc.ai_analysis_status,
                        "document_category": doc.document_category,
                        "ai_relevance_score": float(doc.ai_relevance_score)
                        if doc.ai_relevance_score
                        else None,
                        "ai_summary_preview": (doc.ai_summary or "")[:100],
                    }
                )
                status = "✅" if success else "❌"
                logger.info(
                    f"  {status} 耗时 {elapsed:.1f}s | status={doc.ai_analysis_status} | category={doc.document_category}"
                )
            except Exception as e:
                elapsed = time.time() - doc_start
                results.append(
                    {
                        "index": i,
                        "id": str(doc.id),
                        "title": doc.title,
                        "success": False,
                        "elapsed_seconds": round(elapsed, 1),
                        "error": str(e),
                    }
                )
                logger.error(f"  ❌ 异常: {e}")

    total_elapsed = time.time() - start_all
    success_count = sum(1 for r in results if r["success"])
    failed_count = sum(1 for r in results if not r["success"])

    report = {
        "dry_run_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model": model,
        "total": total,
        "success": success_count,
        "failed": failed_count,
        "total_elapsed_seconds": round(total_elapsed, 1),
        "results": results,
    }

    report_path = os.path.join(_project_root, "task7_dry_run_results.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info("=" * 60)
    logger.info(
        f"试跑完成: 成功={success_count}, 失败={failed_count}, 总耗时={total_elapsed:.1f}s"
    )
    logger.info(f"结果已保存到: {report_path}")
    logger.info("=" * 60)

    return report


if __name__ == "__main__":
    report = asyncio.run(dry_run())
    sys.exit(0 if report and report["failed"] == 0 else 1)
