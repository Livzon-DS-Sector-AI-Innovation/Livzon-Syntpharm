# mypy: ignore-errors
"""OCR async task tests."""

from __future__ import annotations

from app.modules.registration.dossier_writer.models import OcrExtractionTask
from app.modules.registration.dossier_writer.ocr_task_repository import OcrTaskRepository


async def test_ocr_task_repository_create(db_session, sample_asset):
    """Test creating an OCR task."""
    repo = OcrTaskRepository(db_session)

    task = await repo.create_task(
        asset_id=sample_asset.id,
        chapter_id=sample_asset.chapter_id,
        task_type="preview_extraction",
    )

    assert task is not None
    assert task.asset_id == sample_asset.id
    assert task.task_type == "preview_extraction"
    assert task.status == "pending"
    assert task.started_at is None
    assert task.completed_at is None


async def test_ocr_task_repository_update_status(db_session, sample_asset):
    """Test updating OCR task status through lifecycle."""
    repo = OcrTaskRepository(db_session)

    # Create task
    task = await repo.create_task(
        asset_id=sample_asset.id,
        chapter_id=None,
        task_type="split_preview",
    )

    # Update to processing
    task = await repo.update_status(task.id, "processing")
    assert task.status == "processing"
    assert task.started_at is not None

    # Update with progress
    task = await repo.update_status(task.id, "processing", total_pages=10, processed_pages=5)
    assert task.total_pages == 10
    assert task.processed_pages == 5

    # Update to completed
    task = await repo.update_status(
        task.id,
        "completed",
        result_data={"text": "extracted text", "page_count": 10},
        processed_pages=10,
    )
    assert task.status == "completed"
    assert task.completed_at is not None
    assert task.result_data is not None


async def test_ocr_task_repository_get_task(db_session, sample_asset):
    """Test retrieving an OCR task by ID."""
    repo = OcrTaskRepository(db_session)

    task = await repo.create_task(
        asset_id=sample_asset.id,
        chapter_id=sample_asset.chapter_id,
        task_type="preview_extraction",
    )

    retrieved = await repo.get_task(task.id)
    assert retrieved is not None
    assert retrieved.id == task.id
    assert retrieved.asset_id == sample_asset.id


async def test_ocr_task_repository_list_by_asset(db_session, sample_asset):
    """Test listing tasks for an asset."""
    repo = OcrTaskRepository(db_session)

    # Create multiple tasks
    await repo.create_task(sample_asset.id, sample_asset.chapter_id, "preview_extraction")
    await repo.create_task(sample_asset.id, sample_asset.chapter_id, "split_preview")

    tasks = await repo.list_tasks_by_asset(sample_asset.id, limit=10)
    assert len(tasks) == 2
    # Should be ordered by created_at desc
    assert tasks[0].created_at >= tasks[1].created_at


async def test_ocr_task_model_fields(db_session, sample_asset):
    """Test OcrExtractionTask model has all required fields."""
    task = OcrExtractionTask(
        asset_id=sample_asset.id,
        chapter_id=sample_asset.chapter_id,
        task_type="preview_extraction",
        status="pending",
    )

    # Check all fields exist
    assert hasattr(task, 'asset_id')
    assert hasattr(task, 'chapter_id')
    assert hasattr(task, 'task_type')
    assert hasattr(task, 'status')
    assert hasattr(task, 'started_at')
    assert hasattr(task, 'completed_at')
    assert hasattr(task, 'result_data')
    assert hasattr(task, 'error_message')
    assert hasattr(task, 'total_pages')
    assert hasattr(task, 'processed_pages')


async def test_ocr_task_error_handling(db_session, sample_asset):
    """Test task failure scenario."""
    repo = OcrTaskRepository(db_session)

    task = await repo.create_task(
        asset_id=sample_asset.id,
        chapter_id=None,
        task_type="preview_extraction",
    )

    # Simulate failure
    task = await repo.update_status(
        task.id,
        "failed",
        error_message="OCR subprocess timed out after 300 seconds",
    )

    assert task.status == "failed"
    assert task.error_message is not None
    assert "timed out" in task.error_message
    assert task.completed_at is not None
