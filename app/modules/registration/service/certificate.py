"""Registration certificate service."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.registration.models.certificate import RegistrationCertificate
from app.modules.registration.schemas.certificate import (
    CertificateCreate,
    CertificateUpdate,
)


async def get_certificates(db: AsyncSession) -> list[RegistrationCertificate]:
    stmt = (
        select(RegistrationCertificate)
        .where(not RegistrationCertificate.is_deleted)
        .order_by(RegistrationCertificate.updated_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_certificate(
    db: AsyncSession, certificate_id: uuid.UUID
) -> RegistrationCertificate:
    stmt = select(RegistrationCertificate).where(
        RegistrationCertificate.id == certificate_id,
        not RegistrationCertificate.is_deleted,
    )
    result = await db.execute(stmt)
    cert = result.scalar_one_or_none()
    if not cert:
        raise ValueError("证书不存在")
    return cert


async def create_certificate(
    db: AsyncSession, data: CertificateCreate
) -> RegistrationCertificate:
    cert = RegistrationCertificate(**data.model_dump(exclude_unset=True))
    db.add(cert)
    await db.commit()
    await db.refresh(cert)
    return cert


async def update_certificate(
    db: AsyncSession, certificate_id: uuid.UUID, data: CertificateUpdate
) -> RegistrationCertificate:
    cert = await get_certificate(db, certificate_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(cert, field, value)
    await db.commit()
    await db.refresh(cert)
    return cert


async def delete_certificate(db: AsyncSession, certificate_id: uuid.UUID) -> None:
    cert = await get_certificate(db, certificate_id)
    cert.is_deleted = True
    await db.commit()
