"""历史译文记录：落库幂等、分页搜索、软删后不可见。"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.registration.docx_translator.models import DocxTranslationFile
from app.modules.registration.docx_translator.repository import DocxTranslationFileRepository


def _row(job_ref: str = "job-1", object_key: str | None = None, **overrides: object) -> DocxTranslationFile:
    data: dict[str, object] = {
        "id": uuid.uuid4(),
        "job_ref": job_ref,
        "source_filename": "批生产记录.docx",
        "output_filename": "批生产记录_bi.docx",
        "output_kind": "bilingual",
        "object_key": object_key or f"docx_translations/20261118/{job_ref}/0_bi.docx",
        "file_size": 2048,
        "source_lang": "zh",
        "target_lang": "en",
        "mode": "both",
        "success_rate": 98.5,
        "translated_units": 20,
        "total_units": 20,
        "warnings": [],
    }
    data.update(overrides)
    return DocxTranslationFile(**data)


async def test_create_many_is_idempotent(db_session: AsyncSession) -> None:
    repo = DocxTranslationFileRepository(db_session)
    row = _row(job_ref=f"job-{uuid.uuid4().hex[:6]}")

    await repo.create_many([row])
    # 同一 (job_ref, object_key) 重放不应产生第二行
    await repo.create_many([_row(job_ref=row.job_ref, object_key=row.object_key)])

    rows, total = await repo.list_files(keyword=None, page=1, page_size=200)
    matched = [item for item in rows if item.job_ref == row.job_ref]
    assert len(matched) == 1
    assert total >= 1


async def test_list_files_supports_keyword_and_paging(db_session: AsyncSession) -> None:
    repo = DocxTranslationFileRepository(db_session)
    job_ref = f"job-{uuid.uuid4().hex[:6]}"
    await repo.create_many(
        [
            _row(job_ref=job_ref, source_filename="阿立哌唑批记录.docx", object_key=f"{job_ref}/a_bi.docx"),
            _row(
                job_ref=job_ref,
                source_filename="头孢曲松钠回复函.docx",
                object_key=f"{job_ref}/b_bi.docx",
                output_filename="头孢曲松钠回复函_en.docx",
                output_kind="translated",
            ),
        ]
    )

    rows, total = await repo.list_files(keyword="阿立哌唑", page=1, page_size=10)
    assert total == 1
    assert rows[0].source_filename == "阿立哌唑批记录.docx"

    page_one, total_all = await repo.list_files(keyword=None, page=1, page_size=1)
    assert len(page_one) == 1
    assert total_all >= 2


async def test_soft_delete_hides_record(db_session: AsyncSession) -> None:
    repo = DocxTranslationFileRepository(db_session)
    row = _row(job_ref=f"job-{uuid.uuid4().hex[:6]}")
    await repo.create_many([row])

    loaded = await repo.get(row.id)
    assert loaded is not None

    await repo.soft_delete(loaded)
    assert await repo.get(row.id) is None

    rows, _total = await repo.list_files(keyword=str(row.id), page=1, page_size=10)
    assert all(item.id != row.id for item in rows)


async def test_get_unknown_returns_none(db_session: AsyncSession) -> None:
    repo = DocxTranslationFileRepository(db_session)
    assert await repo.get(uuid.uuid4()) is None
