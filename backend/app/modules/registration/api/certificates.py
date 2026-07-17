"""Registration certificate API endpoints."""

import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import success_response
from app.modules.registration.schemas.certificate import (
    CertificateCreate,
    CertificateResponse,
    CertificateUpdate,
)
from app.modules.registration.service import certificate as cert_service

router = APIRouter()


@router.get("/", summary="获取注册证书列表")
async def list_certificates(
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    certs = await cert_service.get_certificates(db)
    data = [CertificateResponse.model_validate(c) for c in certs]
    return success_response(data=data)


@router.post("/", summary="创建注册证书")
async def create_certificate(
    data: CertificateCreate,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    cert = await cert_service.create_certificate(db, data)
    return success_response(data=CertificateResponse.model_validate(cert))


@router.get("/{certificate_id}", summary="获取注册证书详情")
async def get_certificate(
    certificate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    cert = await cert_service.get_certificate(db, certificate_id)
    return success_response(data=CertificateResponse.model_validate(cert))


@router.put("/{certificate_id}", summary="更新注册证书")
async def update_certificate(
    certificate_id: uuid.UUID,
    data: CertificateUpdate,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    cert = await cert_service.update_certificate(db, certificate_id, data)
    return success_response(data=CertificateResponse.model_validate(cert))


@router.delete("/{certificate_id}", summary="删除注册证书")
async def delete_certificate(
    certificate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    await cert_service.delete_certificate(db, certificate_id)
    return success_response(message="删除成功")
