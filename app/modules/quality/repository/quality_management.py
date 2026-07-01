"""Quality management database queries."""

import uuid
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quality.models import (
    CAPA,
    AttachmentReview,
    DepartmentContact,
    DepartmentWeeklyConfirmation,
    Deviation,
)


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# Deviation repository
async def exists_by_deviation_code(
    db: AsyncSession, deviation_code: str, exclude_id: uuid.UUID | None = None
) -> bool:
    query = select(Deviation.id).where(
        Deviation.deviation_code == deviation_code,
        not Deviation.is_deleted,
    )
    if exclude_id:
        query = query.where(Deviation.id != exclude_id)
    result = await db.execute(query.limit(1))
    return result.scalar_one_or_none() is not None


async def create_deviation(db: AsyncSession, data: dict[str, Any]) -> Deviation:
    deviation = Deviation(**data)
    db.add(deviation)
    await db.flush()
    return deviation


async def get_deviation_by_id(
    db: AsyncSession, deviation_id: uuid.UUID
) -> Deviation | None:
    result = await db.execute(
        select(Deviation).where(
            Deviation.id == deviation_id,
            not Deviation.is_deleted,
        )
    )
    return result.scalar_one_or_none()


async def get_deviations(
    db: AsyncSession,
    status: str | None = None,
    level: str | None = None,
    department: str | None = None,
    keyword: str | None = None,
    reporter_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Deviation], int]:
    query = select(Deviation).where(not Deviation.is_deleted)
    count_query = (
        select(func.count()).select_from(Deviation).where(not Deviation.is_deleted)
    )

    filters = []
    if status:
        filters.append(Deviation.status == status)
    if level:
        filters.append(Deviation.level == level)
    if department:
        filters.append(Deviation.department == department)
    if reporter_id:
        filters.append(Deviation.reporter_id == reporter_id)
    if keyword:
        pattern = f"%{_escape_like(keyword)}%"
        filters.append(
            or_(
                Deviation.deviation_code.ilike(pattern),
                Deviation.title.ilike(pattern),
            )
        )

    for filter_condition in filters:
        query = query.where(filter_condition)
        count_query = count_query.where(filter_condition)

    total = (await db.execute(count_query)).scalar_one()

    query = (
        query.order_by(Deviation.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    return result.scalars().all(), total


async def update_deviation(
    db: AsyncSession, deviation: Deviation, data: dict[str, Any]
) -> Deviation:
    for key, value in data.items():
        setattr(deviation, key, value)
    await db.flush()
    return deviation


async def delete_deviation(db: AsyncSession, deviation: Deviation) -> None:
    deviation.is_deleted = True
    await db.flush()


# CAPA repository
async def exists_by_capa_code(
    db: AsyncSession, capa_code: str, exclude_id: uuid.UUID | None = None
) -> bool:
    query = select(CAPA.id).where(
        CAPA.capa_code == capa_code,
        not CAPA.is_deleted,
    )
    if exclude_id:
        query = query.where(CAPA.id != exclude_id)
    result = await db.execute(query.limit(1))
    return result.scalar_one_or_none() is not None


async def create_capa(db: AsyncSession, data: dict[str, Any]) -> CAPA:
    capa = CAPA(**data)
    db.add(capa)
    await db.flush()
    return capa


async def get_capa_by_id(db: AsyncSession, capa_id: uuid.UUID) -> CAPA | None:
    result = await db.execute(
        select(CAPA).where(CAPA.id == capa_id, not CAPA.is_deleted)
    )
    return result.scalar_one_or_none()


async def get_capas(
    db: AsyncSession,
    status: str | None = None,
    source: str | None = None,
    category: str | None = None,
    deviation_id: uuid.UUID | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[CAPA], int]:
    query = select(CAPA).where(not CAPA.is_deleted)
    count_query = select(func.count()).select_from(CAPA).where(not CAPA.is_deleted)

    filters = []
    if status:
        filters.append(CAPA.status == status)
    if source:
        filters.append(CAPA.source == source)
    if category:
        filters.append(CAPA.category == category)
    if deviation_id:
        filters.append(CAPA.deviation_id == deviation_id)
    if keyword:
        pattern = f"%{_escape_like(keyword)}%"
        filters.append(or_(CAPA.capa_code.ilike(pattern), CAPA.title.ilike(pattern)))

    for filter_condition in filters:
        query = query.where(filter_condition)
        count_query = count_query.where(filter_condition)

    total = (await db.execute(count_query)).scalar_one()

    query = (
        query.order_by(CAPA.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    return result.scalars().all(), total


async def update_capa(db: AsyncSession, capa: CAPA, data: dict[str, Any]) -> CAPA:
    for key, value in data.items():
        setattr(capa, key, value)
    await db.flush()
    return capa


async def delete_capa(db: AsyncSession, capa: CAPA) -> None:
    capa.is_deleted = True
    await db.flush()


# Department Contact repository
async def get_department_contact_by_id(
    db: AsyncSession, contact_id: uuid.UUID
) -> DepartmentContact | None:
    result = await db.execute(
        select(DepartmentContact).where(
            DepartmentContact.id == contact_id,
            not DepartmentContact.is_deleted,
        )
    )
    return result.scalar_one_or_none()


async def get_department_contact_by_department(
    db: AsyncSession, department: str
) -> DepartmentContact | None:
    result = await db.execute(
        select(DepartmentContact).where(
            DepartmentContact.department == department,
            not DepartmentContact.is_deleted,
        )
    )
    return result.scalar_one_or_none()


async def get_department_contacts(
    db: AsyncSession, page: int = 1, page_size: int = 20
) -> tuple[list[DepartmentContact], int]:
    query = select(DepartmentContact).where(not DepartmentContact.is_deleted)
    count_query = (
        select(func.count())
        .select_from(DepartmentContact)
        .where(not DepartmentContact.is_deleted)
    )

    total = (await db.execute(count_query)).scalar_one()

    query = (
        query.order_by(DepartmentContact.department)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    return result.scalars().all(), total


async def create_department_contact(
    db: AsyncSession, data: dict[str, Any]
) -> DepartmentContact:
    contact = DepartmentContact(**data)
    db.add(contact)
    await db.flush()
    return contact


async def update_department_contact(
    db: AsyncSession, contact: DepartmentContact, data: dict[str, Any]
) -> DepartmentContact:
    for key, value in data.items():
        setattr(contact, key, value)
    await db.flush()
    return contact


async def delete_department_contact(
    db: AsyncSession, contact: DepartmentContact
) -> None:
    contact.is_deleted = True
    await db.flush()


# Department Weekly Confirmation repository
async def get_weekly_confirmation_by_id(
    db: AsyncSession, confirmation_id: uuid.UUID
) -> DepartmentWeeklyConfirmation | None:
    result = await db.execute(
        select(DepartmentWeeklyConfirmation).where(
            DepartmentWeeklyConfirmation.id == confirmation_id,
            not DepartmentWeeklyConfirmation.is_deleted,
        )
    )
    return result.scalar_one_or_none()


async def get_weekly_confirmation_by_department_week(
    db: AsyncSession, department: str, week_key: str
) -> DepartmentWeeklyConfirmation | None:
    result = await db.execute(
        select(DepartmentWeeklyConfirmation).where(
            DepartmentWeeklyConfirmation.department == department,
            DepartmentWeeklyConfirmation.week_key == week_key,
            not DepartmentWeeklyConfirmation.is_deleted,
        )
    )
    return result.scalar_one_or_none()


async def get_weekly_confirmations(
    db: AsyncSession,
    department: str | None = None,
    week_key: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[DepartmentWeeklyConfirmation], int]:
    query = select(DepartmentWeeklyConfirmation).where(
        not DepartmentWeeklyConfirmation.is_deleted
    )
    count_query = (
        select(func.count())
        .select_from(DepartmentWeeklyConfirmation)
        .where(not DepartmentWeeklyConfirmation.is_deleted)
    )

    if department:
        query = query.where(DepartmentWeeklyConfirmation.department == department)
        count_query = count_query.where(
            DepartmentWeeklyConfirmation.department == department
        )
    if week_key:
        query = query.where(DepartmentWeeklyConfirmation.week_key == week_key)
        count_query = count_query.where(
            DepartmentWeeklyConfirmation.week_key == week_key
        )

    total = (await db.execute(count_query)).scalar_one()

    query = (
        query.order_by(DepartmentWeeklyConfirmation.confirmed_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    return result.scalars().all(), total


async def create_weekly_confirmation(
    db: AsyncSession, data: dict[str, Any]
) -> DepartmentWeeklyConfirmation:
    confirmation = DepartmentWeeklyConfirmation(**data)
    db.add(confirmation)
    await db.flush()
    return confirmation


async def update_weekly_confirmation(
    db: AsyncSession,
    confirmation: DepartmentWeeklyConfirmation,
    data: dict[str, Any],
) -> DepartmentWeeklyConfirmation:
    for key, value in data.items():
        setattr(confirmation, key, value)
    await db.flush()
    return confirmation


async def delete_weekly_confirmation(
    db: AsyncSession, confirmation: DepartmentWeeklyConfirmation
) -> None:
    confirmation.is_deleted = True
    await db.flush()


# Attachment Review repository
async def get_attachment_review_by_id(
    db: AsyncSession, review_id: uuid.UUID
) -> AttachmentReview | None:
    result = await db.execute(
        select(AttachmentReview).where(
            AttachmentReview.id == review_id,
            not AttachmentReview.is_deleted,
        )
    )
    return result.scalar_one_or_none()


async def get_attachment_reviews(
    db: AsyncSession,
    deviation_id: uuid.UUID | None = None,
    capa_id: uuid.UUID | None = None,
    attachment_url: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[AttachmentReview], int]:
    query = select(AttachmentReview).where(not AttachmentReview.is_deleted)
    count_query = (
        select(func.count())
        .select_from(AttachmentReview)
        .where(not AttachmentReview.is_deleted)
    )

    if deviation_id:
        query = query.where(AttachmentReview.deviation_id == deviation_id)
        count_query = count_query.where(AttachmentReview.deviation_id == deviation_id)
    if capa_id:
        query = query.where(AttachmentReview.capa_id == capa_id)
        count_query = count_query.where(AttachmentReview.capa_id == capa_id)
    if attachment_url:
        query = query.where(AttachmentReview.attachment_url == attachment_url)
        count_query = count_query.where(
            AttachmentReview.attachment_url == attachment_url
        )

    total = (await db.execute(count_query)).scalar_one()

    query = (
        query.order_by(AttachmentReview.review_time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    return result.scalars().all(), total


async def create_attachment_review(
    db: AsyncSession, data: dict[str, Any]
) -> AttachmentReview:
    review = AttachmentReview(**data)
    db.add(review)
    await db.flush()
    return review


async def update_attachment_review(
    db: AsyncSession, review: AttachmentReview, data: dict[str, Any]
) -> AttachmentReview:
    for key, value in data.items():
        setattr(review, key, value)
    await db.flush()
    return review


async def delete_attachment_review(db: AsyncSession, review: AttachmentReview) -> None:
    review.is_deleted = True
    await db.flush()
