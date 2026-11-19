"""过期任务清理：保留天数、对象删除失败容错、批上限。"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.modules.registration.docx_translator.models import DocxTranslationFile, DocxTranslationTask
from app.modules.registration.docx_translator.retention import cleanup_expired


def _task(job_ref: str, created_at: datetime) -> DocxTranslationTask:
    return DocxTranslationTask(
        id=uuid.uuid4(),
        job_ref=job_ref,
        status="done",
        source_count=1,
        success_count=1,
        fail_count=0,
        first_source_filename="批记录.docx",
        source_lang="zh",
        target_lang="en",
        mode="bilingual",
        batch_size=30,
        elapsed_seconds=12,
        source_keys=[
            {
                "filename": "批记录.docx",
                "object_key": f"docx_translations/20260101/{job_ref}/source/0_批记录.docx",
                "size": 100,
            }
        ],
        created_at=created_at,
    )


def _file(task: DocxTranslationTask) -> DocxTranslationFile:
    return DocxTranslationFile(
        id=uuid.uuid4(),
        task_id=task.id,
        job_ref=task.job_ref,
        source_filename=task.first_source_filename,
        output_filename="批记录_bi.docx",
        output_kind="bilingual",
        object_key=f"docx_translations/20260101/{task.job_ref}/0_bi.docx",
        file_size=1024,
        source_lang="zh",
        target_lang="en",
        mode="bilingual",
        success_rate=99.0,
        translated_units=10,
        total_units=10,
        warnings=[],
        success=True,
        created_at=task.created_at,
    )


async def test_cleanup_removes_expired_only(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    removed: list[str] = []
    monkeypatch.setattr(storage, "is_enabled", lambda: True)
    monkeypatch.setattr(storage, "delete_object", lambda _module, key: removed.append(key))

    now = datetime.now(UTC)
    old = _task(f"old-{uuid.uuid4().hex[:6]}", now - timedelta(days=40))
    fresh = _task(f"new-{uuid.uuid4().hex[:6]}", now - timedelta(days=3))
    db_session.add_all([old, fresh, _file(old), _file(fresh)])
    await db_session.commit()

    stats = await cleanup_expired(db_session, days=30, now=now)

    assert stats["scanned"] >= 1
    assert stats["deleted"] >= 1
    await db_session.refresh(old)
    await db_session.refresh(fresh)
    assert old.is_deleted is True
    assert fresh.is_deleted is False
    assert any(old.job_ref in key for key in removed)


async def test_cleanup_short_circuits_when_disabled(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(storage, "is_enabled", lambda: True)

    stats = await cleanup_expired(db_session, days=0, now=datetime.now(UTC))
    assert stats == {"scanned": 0, "deleted": 0, "objects_failed": 0}


async def test_cleanup_tolerates_object_delete_failure(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(_module: str, _key: str) -> None:
        raise RuntimeError("minio down")

    monkeypatch.setattr(storage, "is_enabled", lambda: True)
    monkeypatch.setattr(storage, "delete_object", boom)

    now = datetime.now(UTC)
    task = _task(f"fail-{uuid.uuid4().hex[:6]}", now - timedelta(days=90))
    db_session.add_all([task, _file(task)])
    await db_session.commit()

    stats = await cleanup_expired(db_session, days=30, now=now)

    # 对象删除失败只告警：记录照常软删，任务不再被扫到
    assert stats["deleted"] >= 1
    await db_session.refresh(task)
    assert task.is_deleted is True


async def test_cleanup_respects_batch_limit(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(storage, "is_enabled", lambda: True)
    monkeypatch.setattr(storage, "delete_object", lambda _module, _key: None)

    now = datetime.now(UTC)
    for index in range(3):
        db_session.add(_task(f"batch-{index}-{uuid.uuid4().hex[:6]}", now - timedelta(days=60)))
    await db_session.commit()

    stats = await cleanup_expired(db_session, days=30, now=now, batch_limit=2)
    assert stats["scanned"] == 2
    assert stats["deleted"] == 2
