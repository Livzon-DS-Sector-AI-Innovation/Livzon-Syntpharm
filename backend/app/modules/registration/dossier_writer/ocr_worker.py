"""Background worker for OCR extraction tasks."""

import asyncio
import logging
from pathlib import Path
from uuid import UUID

from app.core.database import async_session_factory
from app.modules.registration.dossier_writer.asset_text_extractor import AssetTextExtractor
from app.modules.registration.dossier_writer.ocr_task_repository import OcrTaskRepository

logger = logging.getLogger(__name__)


async def execute_ocr_extraction(
    task_id: UUID,
    file_path: str,
    task_type: str,
):
    """执行OCR提取后台任务

    Args:
        task_id: 任务ID
        file_path: 文件路径
        task_type: 任务类型
    """
    async with async_session_factory() as db:
        repo = OcrTaskRepository(db)
        extractor = AssetTextExtractor()

        try:
            # Update status to processing
            await repo.update_status(task_id, "processing")
            await db.commit()

            # Execute OCR extraction (this is the slow operation)
            path = Path(file_path)

            # For PDFs, we can track progress by page count
            if path.suffix.lower() == ".pdf":
                from app.shared.ocr_service import count_pdf_pages

                total_pages = count_pdf_pages(path)
                await repo.update_status(
                    task_id,
                    "processing",
                    total_pages=total_pages,
                )
                await db.commit()

            # Run extraction in thread pool (still need this for CPU-bound OCR)
            extracted = await asyncio.to_thread(extractor.extract, path)

            if extracted.get("error"):
                await repo.update_status(
                    task_id,
                    "failed",
                    error_message=extracted["error"],
                )
            else:
                # Store result
                await repo.update_status(
                    task_id,
                    "completed",
                    result_data=extracted,
                    processed_pages=extracted.get("page_count", 0),
                )

            await db.commit()
            logger.info(
                f"OCR task {task_id} completed: {extracted.get('error', 'success')}",
            )

        except Exception as e:
            logger.exception(f"OCR task {task_id} failed")
            await repo.update_status(
                task_id,
                "failed",
                error_message=str(e),
            )
            await db.commit()
