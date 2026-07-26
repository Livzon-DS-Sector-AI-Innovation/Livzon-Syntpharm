# mypy: ignore-errors
from __future__ import annotations

import uuid
from datetime import date, datetime

import pytest

from app.modules.quality.label_verification.service import LabelVerificationService
from app.modules.quality.label_verification.schemas import LabelVerificationCreate


@pytest.fixture
def verification_data():
    vk = uuid.uuid4().hex
    return LabelVerificationCreate(
        batch_number=f"BATCH-{uuid.uuid4().hex[:8]}",
        product_name="阿莫西林胶囊",
        production_date=date(2026, 7, 1),
        expiry_date=date(2028, 6, 30),
        total_barrels=10,
        standard_barrels=9,
        remainder_barrel=1,
        standard_weight=25.0,
        remainder_weight=2.5,
        total_weight=227.5,
        check_batch_number=True,
        check_production_date=True,
        check_expiry_date=True,
        check_standard_barrels=True,
        check_remainder_barrel=True,
        check_total_weight=True,
        check_all_barrels_identified=True,
        check_exception_handled=False,
        result_summary="所有标签信息完整，通过复核",
        verification_date=date(2026, 7, 25),
        verification_time=datetime(2026, 7, 25, 14, 30),
        video_file_key=f"video-{vk}.mp4",
    )


@pytest.mark.asyncio
async def test_create_verification(db_session, verification_data):
    svc = LabelVerificationService(session=db_session)
    result = await svc.create_verification(verification_data)
    assert result.batch_number == verification_data.batch_number


@pytest.mark.asyncio
async def test_get_verification(db_session, verification_data):
    svc = LabelVerificationService(session=db_session)
    created = await svc.create_verification(verification_data)
    result = await svc.get_verification(created.id)
    assert result.id == created.id


@pytest.mark.asyncio
async def test_get_verification_not_found(db_session):
    from app.core.exceptions import NotFoundException

    svc = LabelVerificationService(session=db_session)
    with pytest.raises(NotFoundException):
        await svc.get_verification(uuid.uuid4())


@pytest.mark.asyncio
async def test_create_duplicate_video_is_idempotent(db_session, verification_data):
    svc = LabelVerificationService(session=db_session)
    first = await svc.create_verification(verification_data)
    second = await svc.create_verification(verification_data)
    assert second.id == first.id


@pytest.mark.asyncio
async def test_list_verifications(db_session, verification_data):
    svc = LabelVerificationService(session=db_session)
    await svc.create_verification(verification_data)
    items, total = await svc.list_verifications(page=1, page_size=20)
    assert total >= 1


@pytest.mark.asyncio
async def test_delete_verification(db_session, verification_data):
    from app.core.exceptions import NotFoundException

    svc = LabelVerificationService(session=db_session)
    created = await svc.create_verification(verification_data)
    await svc.delete_verification(created.id)
    with pytest.raises(NotFoundException):
        await svc.get_verification(created.id)
