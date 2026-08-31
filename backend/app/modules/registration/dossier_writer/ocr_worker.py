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
    chapter_id: UUID | None = None,
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
                # Perform AI field extraction if this is a preview_extraction task
                if task_type == "preview_extraction" and chapter_id:
                    try:
                        from app.modules.registration.dossier_writer.ai_fill_service import AIFillService
                        from sqlalchemy import select
                        from .models import DossierChapter, ProductDossier
                        
                        # Get chapter and dossier info
                        stmt = select(DossierChapter).where(DossierChapter.id == chapter_id)
                        result = await db.execute(stmt)
                        chapter = result.scalar_one_or_none()
                        
                        if chapter:
                            pd_stmt = select(ProductDossier).where(ProductDossier.id == chapter.product_dossier_id)
                            pd_result = await db.execute(pd_stmt)
                            dossier = pd_result.scalar_one_or_none()
                            
                            if dossier:
                                # Perform AI field extraction (same as original sync flow)
                                service = AIFillService(db)
                                ai_result = await service.preview_extraction(dossier, chapter)
                                
                                # Store AI-extracted fields (not raw OCR)
                                await repo.update_status(
                                    task_id,
                                    "completed",
                                    result_data=ai_result,
                                    processed_pages=extracted.get("page_count", 0),
                                )
                                await db.commit()
                                logger.info(f"OCR task {task_id} completed with AI extraction")
                                return
                    except Exception as e:
                        logger.error(f"AI extraction failed for task {task_id}: {e}")
                        # Fall back to storing raw OCR results
                
                # Store raw OCR result (fallback)
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
