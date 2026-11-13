"""Authorization letter API routes."""

import json
import logging
from io import BytesIO
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.exceptions import BadRequestException, NotFoundException
from app.core.response import DataResponse
from app.modules.registration.schemas import AuthorizationLetterCreate
from app.modules.registration.schemas.authorization import (
    AuthorizationLetterFilterOptions,
    AuthorizationLetterListItem,
    AuthorizationLetterResponse,
    AuthorizationLetterTrailItem,
    DownloadUrlResponse,
    ProductInfo,
)
from app.modules.registration.service import AuthorizationLetterService
from app.shared.schemas import PageParams

logger = logging.getLogger(__name__)

router = APIRouter()


def get_service(session: AsyncSession = Depends(get_db)) -> AuthorizationLetterService:
    return AuthorizationLetterService(session)


@router.get("/products", response_model=DataResponse[list[ProductInfo]], summary="获取品种登记号对照表")
async def list_products(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("registration:authorization-letter:read")),
    service: AuthorizationLetterService = Depends(get_service),
) -> DataResponse[list[ProductInfo]]:
    products = service.get_product_list()
    return DataResponse[list[ProductInfo]](data=products)


@router.get(
    "/filter-options",
    response_model=DataResponse[AuthorizationLetterFilterOptions],
    summary="授权书列表筛选下拉选项",
)
async def list_filter_options(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("registration:authorization-letter:read")),
    service: AuthorizationLetterService = Depends(get_service),
) -> DataResponse[AuthorizationLetterFilterOptions]:
    """品种选项来自品种主数据（新增品种自动出现），年份按生成时间动态提取降序"""
    options = await service.get_filter_options()
    return DataResponse[AuthorizationLetterFilterOptions](data=options)


@router.get("", response_model=DataResponse[list[AuthorizationLetterListItem]], summary="授权书生成记录列表")
async def list_letters(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("registration:authorization-letter:read")),
    keyword: str | None = Query(None, description="关键词（模糊匹配：产品名称/登记号/制剂单位/制剂名称）"),
    product_name: str | None = Query(None, description="品种精确筛选"),
    year: int | None = Query(None, description="生成年份筛选"),
    page_params: PageParams = Depends(),
    service: AuthorizationLetterService = Depends(get_service),
) -> DataResponse[list[AuthorizationLetterListItem]]:
    letters, total = await service.list_letters(
        keyword=keyword,
        product_name=product_name,
        year=year,
        page=page_params.page,
        page_size=page_params.page_size,
    )
    return DataResponse[list[AuthorizationLetterListItem]](
        data=letters,
        meta={"page": page_params.page, "page_size": page_params.page_size, "total": total},
    )


@router.post(
    "/generate",
    response_model=DataResponse[AuthorizationLetterResponse],
    summary="生成授权书",
    status_code=201,
)
async def generate_letter(
    current_user: RequiredUser,
    template: UploadFile | None = None,
    ctx: PermissionContext = Depends(require_permission("registration:authorization-letter:create")),
    product_name: str = Form(..., description="产品名称"),
    registration_number: str = Form(..., description="登记号"),
    preparation_unit: str = Form(..., description="制剂单位名称"),
    preparation_name: str = Form(..., description="制剂名称"),
    administration_route: str = Form(..., description="给药途径"),
    remarks: str | None = Form(None, description="备注"),
    template_variant: str = Form("zh", description="内置模板版本：zh=中文"),
    replacements: str | None = Form(
        None,
        description='自定义模板的替换规则 JSON，格式: [{"old": "原文本", "new": "新文本"}]',
    ),
    service: AuthorizationLetterService = Depends(get_service),
) -> DataResponse[AuthorizationLetterResponse]:
    template_data: bytes | None = None
    template_file_name: str | None = None
    if template is not None:
        template_data = await template.read()
        template_file_name = template.filename or "模板.docx"

    template_placeholders = None
    if replacements:
        try:
            rules = json.loads(replacements)
            template_placeholders = {str(r["old"]): str(r["new"]) for r in rules}
        except (json.JSONDecodeError, KeyError, TypeError, AttributeError):
            raise BadRequestException(
                '替换规则格式错误，应为 JSON 数组：[{"old": "原文本", "new": "新文本"}]'
            ) from None

    data = AuthorizationLetterCreate(
        product_name=product_name,
        registration_number=registration_number,
        preparation_unit=preparation_unit,
        preparation_name=preparation_name,
        administration_route=administration_route,
        remarks=remarks,
    )

    letter = await service.generate_letter(
        data=data,
        template_data=template_data,
        template_file_name=template_file_name,
        template_variant=template_variant,
        template_placeholders=template_placeholders,
        operator_id=current_user.id,
    )
    return DataResponse[AuthorizationLetterResponse](data=letter, message="授权书生成成功", code=201)


@router.get("/{letter_id}", response_model=DataResponse[AuthorizationLetterResponse], summary="授权书记录详情")
async def get_letter(
    current_user: RequiredUser,
    letter_id: UUID,
    ctx: PermissionContext = Depends(require_permission("registration:authorization-letter:read")),
    service: AuthorizationLetterService = Depends(get_service),
) -> DataResponse[AuthorizationLetterResponse]:
    letter = await service.get_letter(letter_id)
    return DataResponse[AuthorizationLetterResponse](data=letter)


@router.get(
    "/{letter_id}/trails",
    response_model=DataResponse[list[AuthorizationLetterTrailItem]],
    summary="授权书留痕记录（生成/下载，只增不删）",
)
async def list_letter_trails(
    current_user: RequiredUser,
    letter_id: UUID,
    ctx: PermissionContext = Depends(require_permission("registration:authorization-letter:read")),
    service: AuthorizationLetterService = Depends(get_service),
) -> DataResponse[list[AuthorizationLetterTrailItem]]:
    trails = await service.list_trails(letter_id)
    return DataResponse[list[AuthorizationLetterTrailItem]](data=trails)


@router.get(
    "/{letter_id}/download-url",
    response_model=DataResponse[DownloadUrlResponse],
    summary="获取授权书文件下载URL",
)
async def get_letter_download_url(
    current_user: RequiredUser,
    letter_id: UUID,
    ctx: PermissionContext = Depends(require_permission("registration:authorization-letter:read")),
    service: AuthorizationLetterService = Depends(get_service),
) -> DataResponse[DownloadUrlResponse]:
    letter_model = await service.repo.get_by_id(letter_id)
    if not letter_model:
        raise NotFoundException("授权书记录", str(letter_id))

    return DataResponse[DownloadUrlResponse](
        data=DownloadUrlResponse(url=f"/api/v1/registration/authorization-letters/{letter_id}/download")
    )


@router.get("/{letter_id}/download", summary="下载生成的授权书文件")
async def download_letter(
    current_user: RequiredUser,
    letter_id: UUID,
    ctx: PermissionContext = Depends(require_permission("registration:authorization-letter:read")),
    service: AuthorizationLetterService = Depends(get_service),
) -> StreamingResponse:
    # 下载即留痕：先写入记录（不存在则 404，不落留痕），由请求结束统一提交
    letter_model = await service.record_download(letter_id, operator_id=current_user.id)

    content, media_type = service.load_output_file(letter_model)
    filename = letter_model.output_file_name
    return StreamingResponse(
        BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.delete("/{letter_id}", response_model=DataResponse[None], summary="删除授权书记录")
async def delete_letter(
    current_user: RequiredUser,
    letter_id: UUID,
    ctx: PermissionContext = Depends(require_permission("registration:authorization-letter:delete")),
    service: AuthorizationLetterService = Depends(get_service),
) -> DataResponse[None]:
    await service.delete_letter(letter_id)
    return DataResponse[None](message="授权书记录删除成功")
