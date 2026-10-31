"""Supplementary reply API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Form, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.exceptions import NotFoundException
from app.core.response import DataResponse
from app.modules.registration.schemas.authorization import (
    DownloadUrlResponse,
    SupplementaryReplyListItem,
    SupplementaryReplyResponse,
)
from app.modules.registration.service import SupplementaryReplyService
from app.shared.schemas import PageParams

router = APIRouter()


def get_service(session: AsyncSession = Depends(get_db)) -> SupplementaryReplyService:
    return SupplementaryReplyService(session)


@router.post("/generate", summary="生成发补回复文档")
async def post(
    current_user: RequiredUser,
    notice: UploadFile,
    ctx: PermissionContext = Depends(require_permission("registration:supplementary-reply:create")),
    template: UploadFile | None = None,
    drug_name: str | None = Form(None, description="药品名称（可选，默认从PDF提取）"),
    registration_number: str | None = Form(None, description="登记号（可选）"),
    acceptance_number: str | None = Form(None, description="受理号（可选）"),
    company_name: str | None = Form(None, description="申请人/公司名称（可选）"),
    remarks: str | None = Form(None, description="备注"),
    service: SupplementaryReplyService = Depends(get_service),
) -> DataResponse[SupplementaryReplyResponse]:
    notice_data = await notice.read()
    notice_file_name = notice.filename or "CDE通知函.pdf"

    template_data = None
    template_file_name = None
    if template:
        template_data = await template.read()
        template_file_name = template.filename

    reply = await service.generate_reply(
        notice_data=notice_data,
        notice_file_name=notice_file_name,
        template_data=template_data,
        template_file_name=template_file_name,
        drug_name_override=drug_name,
        registration_number_override=registration_number,
        acceptance_number_override=acceptance_number,
        company_name_override=company_name,
        remarks=remarks,
    )
    return DataResponse[SupplementaryReplyResponse](
        data=reply,
        message="发补回复文档生成成功",
        code=201,
    )


@router.get("", summary="发补回复记录列表")
async def get(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("registration:supplementary-reply:read")),
    drug_name: str | None = Query(None, description="药品名称搜索"),
    page_params: PageParams = Depends(),
    service: SupplementaryReplyService = Depends(get_service),
) -> DataResponse[list[SupplementaryReplyListItem]]:
    replies, total = await service.list_replies(
        drug_name=drug_name,
        page=page_params.page,
        page_size=page_params.page_size,
    )
    return DataResponse[list[SupplementaryReplyListItem]](
        data=replies,
        meta={"page": page_params.page, "page_size": page_params.page_size, "total": total},
    )


@router.get("/{reply_id}", summary="发补回复记录详情")  # type: ignore[no-redef]
async def get(  # noqa: F811
    current_user: RequiredUser,
    reply_id: UUID,
    ctx: PermissionContext = Depends(require_permission("registration:supplementary-reply:read")),
    service: SupplementaryReplyService = Depends(get_service),
) -> DataResponse[SupplementaryReplyResponse]:
    reply = await service.get_reply(reply_id)
    return DataResponse[SupplementaryReplyResponse](data=reply)


@router.get("/{reply_id}/download-url", summary="获取发补回复文件下载URL")  # type: ignore[no-redef]
async def get(  # noqa: F811
    current_user: RequiredUser,
    reply_id: UUID,
    ctx: PermissionContext = Depends(require_permission("registration:supplementary-reply:read")),
    service: SupplementaryReplyService = Depends(get_service),
) -> DataResponse[DownloadUrlResponse]:
    reply_model = await service.repo.get_by_id(reply_id)
    if not reply_model:
        raise NotFoundException("发补回复记录", str(reply_id))

    file_path = service.get_output_file_path(reply_model)
    if not file_path.exists():
        raise NotFoundException("发补回复文件")

    return DataResponse[DownloadUrlResponse](
        data=DownloadUrlResponse(url=f"/api/v1/registration/supplementary-replies/{reply_id}/download")
    )


@router.get("/{reply_id}/download", summary="下载生成的发补回复文件")  # type: ignore[no-redef]
async def get(  # noqa: F811
    current_user: RequiredUser,
    reply_id: UUID,
    ctx: PermissionContext = Depends(require_permission("registration:supplementary-reply:read")),
    service: SupplementaryReplyService = Depends(get_service),
) -> FileResponse:
    reply_model = await service.repo.get_by_id(reply_id)
    if not reply_model:
        raise NotFoundException("发补回复记录", str(reply_id))

    file_path = service.get_output_file_path(reply_model)
    if not file_path.exists():
        raise NotFoundException("发补回复文件")

    return FileResponse(
        path=str(file_path),
        filename=reply_model.output_file_name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.delete("/{reply_id}", summary="删除发补回复记录")
async def delete(
    current_user: RequiredUser,
    reply_id: UUID,
    ctx: PermissionContext = Depends(require_permission("registration:supplementary-reply:delete")),
    service: SupplementaryReplyService = Depends(get_service),
) -> DataResponse[None]:
    await service.delete_reply(reply_id)
    return DataResponse[None](message="发补回复记录删除成功")
