"""Dossier Writer API endpoints."""

import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import async_session_factory, get_db
from app.core.deps import RequiredUser, require_route_permission
from app.core.exceptions import AppException, BadRequestException, NotFoundException
from app.core.job_store import JobStore, get_job_state_or_404, start_job
from app.core.response import build_response, error_response
from app.shared.schemas import AsyncJobAccepted, AsyncJobAcceptedResponse, AsyncJobStateResponse

from .field_models import FieldFillResult, FieldMapping
from .models import ChapterAsset, DossierChapter, ProductDossier
from .schemas import (
    AIConfirmData,
    AIConfirmRequest,
    AIConfirmResponse,
    AssetCategoryListApiResponse,
    AssetCategoryUpdateData,
    AssetCategoryUpdateRequest,
    AssetCategoryUpdateResponse,
    AssetListApiResponse,
    AssetMatchApiResponse,
    AssetResponse,
    AssetUploadBatchApiResponse,
    AssetUploadResponse,
    AssetUsageToggleData,
    AssetUsageToggleRequest,
    AssetUsageToggleResponse,
    AvailableAssetListApiResponse,
    ChapterDetailApiResponse,
    ChapterPreviewApiResponse,
    ChapterTreeApiResponse,
    ExportApiResponse,
    ExportRequest,
    FieldFillApiResponse,
    FieldMappingListApiResponse,
    FillResultListApiResponse,
    InitChapterConfigApiResponse,
    InitS7ApiResponse,
    MessageApiResponse,
    ParseResultApiResponse,
    ProductDossierApiResponse,
    ProductDossierCreate,
    ProductDossierListApiResponse,
    ProductDossierListResponse,
    ProductDossierResponse,
    ProductDossierUpdate,
    SplitConfirmData,
    SplitConfirmRequest,
    SplitConfirmResponse,
    SplitPreviewData,
    SplitPreviewRequest,
    SplitPreviewResponse,
    StringListApiResponse,
    TemplateUploadApiResponse,
)
from .service import DossierService

logger = logging.getLogger(__name__)

# 读写分离：GET 与「只读语义的 POST」（预览/解析/下载）→ registration:dossier:read；
# POST → :create，PUT/PATCH → :update，DELETE → :delete。
_DOSSIER_READ_ONLY_SUFFIXES = (
    "/preview",
    "/ai-preview",
    "/split-preview",
    "/download",
    "/docx-file",
    "/fill-results",
)


def resolve_dossier_code(method: str, path: str) -> str:
    """按方法与路径解析申报资料撰写的权限码（与 registry 绑定登记同口径）。"""
    if method.upper() in ("GET", "HEAD") or path.rstrip("/").endswith(_DOSSIER_READ_ONLY_SUFFIXES):
        return "registration:dossier:read"
    if method.upper() == "POST":
        return "registration:dossier:create"
    if method.upper() in ("PUT", "PATCH"):
        return "registration:dossier:update"
    if method.upper() == "DELETE":
        return "registration:dossier:delete"
    return "registration:dossier:read"


router = APIRouter(dependencies=[Depends(require_route_permission(resolve_dossier_code))])

# AI 预览后台任务状态表（进程内）
_dossier_job_store = JobStore()


# ====== Product Dossier ======


@router.post("/products", response_model=ProductDossierApiResponse)
async def create_product_dossier(
    current_user: RequiredUser,
    data: ProductDossierCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """创建品种资料"""
    service = DossierService(db)
    try:
        dossier = await service.create_product_dossier(data)
        return build_response(data=ProductDossierResponse.model_validate(dossier), message="创建成功")
    except ValueError as e:
        return error_response(message=str(e), status_code=400)


@router.get("/products", response_model=ProductDossierListApiResponse)
async def list_product_dossiers(
    current_user: RequiredUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """获取品种资料列表"""
    service = DossierService(db)
    items, total = await service.list_product_dossiers(skip, limit)
    return build_response(
        data={
            "items": [ProductDossierListResponse.model_validate(i) for i in items],
            "total": total,
            "skip": skip,
            "limit": limit,
        },
        message="获取成功",
    )


@router.get("/products/{dossier_id}", response_model=ProductDossierApiResponse)
async def get_product_dossier(
    current_user: RequiredUser,
    dossier_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """获取品种资料详情"""
    service = DossierService(db)
    dossier = await service.get_product_dossier(dossier_id)
    if not dossier:
        raise NotFoundException("品种资料")
    return build_response(data=ProductDossierResponse.model_validate(dossier), message="获取成功")


@router.put("/products/{dossier_id}", response_model=ProductDossierApiResponse)
async def update_product_dossier(
    current_user: RequiredUser,
    dossier_id: UUID,
    data: ProductDossierUpdate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """更新品种资料"""
    service = DossierService(db)
    dossier = await service.update_product_dossier(dossier_id, data)
    if not dossier:
        raise NotFoundException("品种资料")
    return build_response(data=ProductDossierResponse.model_validate(dossier), message="更新成功")


@router.delete("/products/{dossier_id}", response_model=MessageApiResponse)
async def delete_product_dossier(
    current_user: RequiredUser,
    dossier_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """删除品种资料"""
    service = DossierService(db)
    success = await service.delete_product_dossier(dossier_id)
    if not success:
        raise NotFoundException("品种资料")
    return build_response(message="删除成功")


# ====== Template Upload ======


@router.post("/products/{dossier_id}/templates", response_model=TemplateUploadApiResponse)
async def upload_templates(
    current_user: RequiredUser,
    dossier_id: UUID,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """批量上传模板文件"""
    service = DossierService(db)

    results = []
    for file in files:
        # 验证文件类型
        if not file.filename or not file.filename.lower().endswith(".docx"):
            results.append(
                {
                    "filename": file.filename,
                    "status": "failed",
                    "error": "仅支持 .docx 格式文件",
                }
            )
            continue

        try:
            # 读取文件内容
            content = await file.read()
            logger.info(f"[Upload] Processing file: {file.filename}, size: {len(content)} bytes")

            # 保存模板
            template = await service.save_template_file(dossier_id, file.filename, content)
            logger.info(f"[Upload] Saved template: {template.id}, filename: {template.original_filename}")

            results.append(
                {
                    "file_id": str(template.id),
                    "filename": template.original_filename,
                    "file_path": template.file_path,
                    "file_size": str(template.file_size) if template.file_size else None,
                    "status": "success",
                }
            )
        except Exception as e:
            logger.error(f"[Upload] Failed to save {file.filename}: {e}", exc_info=True)
            results.append({"filename": file.filename, "status": "failed", "error": str(e)})

    # 更新品种状态为 template_uploaded
    await service.repo.update_product_dossier(dossier_id, parse_status="template_uploaded")
    await service.db.commit()

    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = len(results) - success_count

    # 自动触发匹配
    match_result = await service.match_assets_to_chapters(dossier_id)

    return build_response(
        data={
            "results": results,
            "success_count": success_count,
            "failed_count": failed_count,
            "matched_count": match_result.get("matched_count", 0),
            "unmatched_files": match_result.get("unmatched_files", []),
        },
        message=f"上传完成：成功 {success_count} 个，匹配 {match_result.get('matched_count', 0)} 个",
    )


# ====== Template Parsing ======


@router.post("/products/{dossier_id}/parse", response_model=ParseResultApiResponse)
async def parse_templates(
    current_user: RequiredUser,
    dossier_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """解析模板生成章节树"""
    service = DossierService(db)
    result = await service.parse_templates(dossier_id)

    if result["success"]:
        return build_response(data=result, message=result["message"])
    else:
        return error_response(message=result["message"], detail=result.get("error"))


# ====== Chapter ======


@router.get("/products/{dossier_id}/chapters", response_model=ChapterTreeApiResponse)
async def get_chapter_tree(
    current_user: RequiredUser,
    dossier_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """获取章节树"""
    service = DossierService(db)
    chapters = await service.get_chapter_tree(dossier_id)
    return build_response(data=chapters, message="获取成功")


@router.get("/chapters/{chapter_id}", response_model=ChapterDetailApiResponse)
async def get_chapter_detail(
    current_user: RequiredUser,
    chapter_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """获取章节详情"""
    service = DossierService(db)
    chapter = await service.get_chapter_detail(chapter_id)
    if not chapter:
        raise NotFoundException("章节")
    return build_response(data=chapter, message="获取成功")


# ====== Asset ======


@router.post("/chapters/{chapter_id}/assets", response_model=AssetUploadBatchApiResponse)
async def upload_asset(
    current_user: RequiredUser,
    chapter_id: UUID,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """批量上传章节素材"""
    service = DossierService(db)

    results = []
    for file in files:
        if not file.filename:
            continue
        content = await file.read()
        asset = await service.upload_chapter_asset(chapter_id, file.filename, content)
        results.append(
            AssetUploadResponse(
                id=asset.id,
                original_filename=asset.original_filename,
                file_path=asset.file_path,
                file_type=asset.file_type,
                file_size=asset.file_size,
                uploaded_at=asset.uploaded_at,
                category_id=asset.category_id,
            )
        )

    return build_response(
        data={
            "assets": [r.model_dump(mode="json") for r in results],
            "count": len(results),
        },
        message=f"成功上传 {len(results)} 个素材",
    )


@router.get("/chapters/{chapter_id}/assets", response_model=AssetListApiResponse)
async def list_assets(
    current_user: RequiredUser,
    chapter_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """获取章节自有素材列表（不含继承素材）

    如需获取包含继承素材的完整列表，请使用 /available-assets 接口。
    """
    service = DossierService(db)
    assets = await service.list_chapter_assets(chapter_id)
    return build_response(data=[AssetResponse.model_validate(a) for a in assets], message="获取成功")


@router.delete("/assets/{asset_id}", response_model=MessageApiResponse)
async def delete_asset(
    current_user: RequiredUser,
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """删除素材"""
    service = DossierService(db)
    success = await service.delete_asset(asset_id)
    if not success:
        raise NotFoundException("素材")
    return build_response(message="删除成功")


@router.patch("/assets/{asset_id}", response_model=AssetCategoryUpdateResponse)
async def update_asset_category(
    current_user: RequiredUser,
    asset_id: UUID,
    body: AssetCategoryUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> AssetCategoryUpdateResponse:
    """更新素材的分类"""
    asset = await db.get(ChapterAsset, asset_id)
    if not asset:
        raise NotFoundException("素材")

    category_id = body.category_id
    asset.category_id = category_id if category_id else None
    await db.commit()
    result = await db.execute(select(ChapterAsset).where(ChapterAsset.id == asset_id))
    asset = result.scalar_one()

    return AssetCategoryUpdateResponse(
        code=200,
        data=AssetCategoryUpdateData(
            id=str(asset.id),
            category_id=str(asset.category_id) if asset.category_id else None,
        ),
        message="分类已更新",
    )


# ====== Export ======


@router.post("/products/{dossier_id}/export", response_model=ExportApiResponse)
async def export_dossier(
    current_user: RequiredUser,
    dossier_id: UUID,
    data: ExportRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """导出品种资料"""
    service = DossierService(db)
    result = await service.export_dossier(dossier_id, data.chapter_ids)

    if result["success"]:
        return build_response(data=result, message=result["message"])
    else:
        return error_response(message=result["message"])


# 下载白名单根：导出目录默认落在 STORAGE_ROOT 下（service.storage_root），
# 兼配 UPLOAD_DIR 以兼容历史上的上传根。根目录本身不允许当白名单。
_DOWNLOAD_ROOT_SETTINGS = ("STORAGE_ROOT", "UPLOAD_DIR")


def _allowed_download_roots() -> list[Path]:
    """允许下载的根目录（绝对路径，已解析符号链接）。"""
    settings = get_settings()
    roots: list[Path] = []
    for name in _DOWNLOAD_ROOT_SETTINGS:
        raw = getattr(settings, name, None)
        if not raw:
            continue
        try:
            root = Path(raw).resolve()
        except (OSError, RuntimeError):
            continue
        if root.parent == root:  # 根目录 / 盘符根不能当白名单，否则等于放开整个文件系统
            continue
        if root not in roots:
            roots.append(root)
    return roots


def _resolve_export_file(outputs_path: str | None, filename: str) -> Path | None:
    """把导出文件名解析成白名单内的真实路径，越界返回 None。

    ``filename`` 来自 query，属外部输入：先拒绝分隔符与上跳（``../x``、``a/b``、
    ``C:\\x``），再用 ``resolve`` 消解符号链接，最后要求结果仍是 outputs 目录的
    直接子文件，并且落在 ``STORAGE_ROOT`` / ``UPLOAD_DIR`` 之内。
    """
    if not outputs_path or not filename or "\x00" in filename:
        return None
    if Path(filename).name != filename or filename in (".", ".."):
        return None
    try:
        base = Path(outputs_path).resolve()
        candidate = (base / filename).resolve()
    except (OSError, RuntimeError):
        return None
    if candidate.parent != base:
        return None
    if not any(root == base or root in base.parents for root in _allowed_download_roots()):
        return None
    if not candidate.is_file():
        return None
    return candidate


@router.get("/products/{dossier_id}/download")
async def download_exported_file(
    current_user: RequiredUser,
    dossier_id: UUID,
    filename: str = Query(..., description="文件名"),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """下载导出的文件"""
    service = DossierService(db)
    dossier = await service.repo.get_product_dossier(dossier_id)
    if not dossier:
        raise NotFoundException("品种资料")

    file_path = _resolve_export_file(dossier.outputs_path, filename)
    if file_path is None:
        raise NotFoundException("文件")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.get("/chapters/{chapter_id}/preview", response_model=ChapterPreviewApiResponse)
async def get_chapter_preview(
    current_user: RequiredUser,
    chapter_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """获取章节预览内容"""
    service = DossierService(db)
    result = await service.get_chapter_preview(chapter_id)

    if result["success"]:
        return build_response(data=result, message="获取预览成功")
    else:
        return error_response(message=result["message"])


@router.get("/chapters/{chapter_id}/docx-file")
async def get_chapter_docx_file(
    current_user: RequiredUser,
    chapter_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """获取章节的 docx 工作副本文件，用于前端 docx-preview 渲染"""
    from pathlib import Path

    chapter = await db.get(DossierChapter, chapter_id)
    if not chapter:
        raise NotFoundException("章节")

    dossier = await db.get(ProductDossier, chapter.product_dossier_id)
    if not dossier:
        raise NotFoundException("品种资料")

    if not chapter.working_file:
        raise AppException(status_code=404, message="该章节尚无工作副本文件")

    file_path = Path(dossier.working_path or "") / chapter.working_file
    if not file_path.exists():
        raise NotFoundException("工作副本文件")

    return FileResponse(
        path=str(file_path),
        filename=chapter.working_file,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@router.post("/products/{dossier_id}/match-assets", response_model=AssetMatchApiResponse)
async def match_assets_to_chapters(
    current_user: RequiredUser,
    dossier_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """智能匹配素材到章节"""
    service = DossierService(db)
    result = await service.match_assets_to_chapters(dossier_id)

    if result["success"]:
        return build_response(data=result, message=result["message"])
    else:
        return error_response(message=result["message"])


# ====== Field Mapping ======

from .field_fill_service import FieldFillService  # noqa: E402

# from .field_mapping_config import S6_FIELD_MAPPINGS  # 已废弃


@router.post("/chapters/{chapter_id}/fill-fields", response_model=FieldFillApiResponse)
async def fill_chapter_fields(
    current_user: RequiredUser,
    chapter_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """执行字段填充 - 从素材提取内容并填充到章节"""
    service = DossierService(db)
    fill_service = FieldFillService(db)

    # 获取章节信息
    chapter = await service.get_chapter_detail(chapter_id)
    if not chapter:
        raise NotFoundException("章节")

    # 获取品种信息
    dossier = await service.get_product_dossier(chapter.product_dossier_id)
    if not dossier:
        raise NotFoundException("品种资料")

    # 获取章节素材
    assets = await service.list_chapter_assets(chapter_id)

    # 获取章节模型用于填充
    ch_model = await db.get(DossierChapter, chapter_id)
    if not ch_model:
        raise NotFoundException("章节")

    # 执行填充
    result = await fill_service.fill_chapter_fields(dossier, ch_model, assets)

    return build_response(data=result, message=result["message"])


@router.get("/chapters/{chapter_code}/field-mappings", response_model=FieldMappingListApiResponse)
async def get_field_mappings(
    current_user: RequiredUser,
    chapter_code: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """获取章节的字段映射配置"""
    fill_service = FieldFillService(db)
    mappings = await fill_service.get_field_mappings(chapter_code)

    return build_response(
        data=[
            {
                "id": str(m.id),
                "field_name": m.field_name,
                "field_type": m.field_type,
                "location_type": m.location_type,
                "location_hint": m.location_hint,
                "extraction_prompt": m.extraction_prompt,
                "source_type": m.source_type,
                "source_category": m.source_category,
                "fixed_value": m.fixed_value,
                "appendix_slot": m.appendix_slot,
                "sort_order": m.sort_order,
                "is_required": m.is_required,
            }
            for m in mappings
        ],
        message="获取成功",
    )


@router.post("/field-mappings/init-s6", response_model=InitChapterConfigApiResponse)
async def init_s6_field_mappings(
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """初始化 S.6 包装系统的字段映射配置（从数据库 seed 数据）"""
    from .service import DossierService

    service = DossierService(db)
    result = await service.init_chapter_ai_config("3.2.S.6")
    return build_response(data=result, message=result["message"])


@router.post("/field-mappings/init-s7", response_model=InitS7ApiResponse)
async def init_s7_field_mappings(
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """初始化 S.7 稳定性模块的字段映射配置（从 seed_data_s7.py）

    初始化 S.7.1、S.7.2、S.7.3 三个子章节的：
    - asset_categories（素材分类）
    - field_mappings（字段映射）
    """
    from .service import DossierService

    service = DossierService(db)

    # 初始化三个子章节
    results = []
    for chapter_code in ["3.2.S.7.1", "3.2.S.7.2", "3.2.S.7.3"]:
        result = await service.init_chapter_ai_config(chapter_code)
        results.append(
            {
                "chapter_code": chapter_code,
                "success": result["success"],
                "message": result["message"],
            }
        )

    return build_response(data={"chapters": results}, message="S.7 稳定性模块初始化完成")


@router.get("/chapters/{chapter_id}/fill-results", response_model=FillResultListApiResponse)
async def get_fill_results(
    current_user: RequiredUser,
    chapter_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """获取章节的填充结果"""

    stmt = (
        select(FieldFillResult)
        .where(
            FieldFillResult.chapter_id == chapter_id,
            ~FieldFillResult.is_deleted,
        )
        .order_by(FieldFillResult.created_at.desc())
    )

    result = await db.execute(stmt)
    fills = list(result.scalars().all())

    return build_response(
        data=[
            {
                "id": str(f.id),
                "field_name": f.field_name,
                "filled_value": f.filled_value,
                "fill_method": f.fill_method,
                "status": f.status,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in fills
        ],
        message="获取成功",
    )


# ====== AI Fill Service ======


@router.post("/chapters/{chapter_id}/ai-preview", response_model=AsyncJobAcceptedResponse)
async def ai_preview_extraction(
    current_user: RequiredUser,
    chapter_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """提交 AI 智能解析预览后台任务（逐类目 LLM 调用 >5s）。

    轮询 GET /dossier-writer/jobs/{job_id}；`result` 为原 AiPreviewData 载荷。
    """
    from .ai_fill_service import AIFillService
    from .models import DossierChapter, ProductDossier

    # 校验章节与品种存在（快速失败），后台任务里重新加加载
    ch_stmt = select(DossierChapter).where(DossierChapter.id == chapter_id)
    ch_result = await db.execute(ch_stmt)
    chapter = ch_result.scalar_one_or_none()
    if not chapter:
        return error_response(message="章节不存在", status_code=404)

    pd_stmt = select(ProductDossier).where(ProductDossier.id == chapter.product_dossier_id)
    pd_result = await db.execute(pd_stmt)
    if not pd_result.scalar_one_or_none():
        return error_response(message="品种资料不存在", status_code=404)

    async def _run(_job: str) -> dict[str, Any]:
        async with async_session_factory() as job_db:
            job_ch_result = await job_db.execute(ch_stmt)
            job_chapter = job_ch_result.scalar_one_or_none()
            if not job_chapter:
                raise RuntimeError("章节不存在")
            job_pd_result = await job_db.execute(pd_stmt)
            job_dossier = job_pd_result.scalar_one_or_none()
            if not job_dossier:
                raise RuntimeError("品种资料不存在")
            service = AIFillService(job_db)
            return await service.preview_extraction(job_dossier, job_chapter)

    job_id = start_job(_dossier_job_store, "dossier-ai-preview", _run)
    return AsyncJobAcceptedResponse(data=AsyncJobAccepted(job_id=job_id))


@router.get("/jobs/{job_id}", response_model=AsyncJobStateResponse)
async def get_dossier_job_status(
    current_user: RequiredUser,
    job_id: str,
) -> AsyncJobStateResponse:
    """查询 AI 预览后台任务状态（404 = 查不到，前端按兜底态处理）。"""
    return AsyncJobStateResponse(data=get_job_state_or_404(_dossier_job_store, job_id))


@router.post("/chapters/{chapter_id}/ai-confirm", response_model=AIConfirmResponse)
async def ai_confirm_and_fill(
    current_user: RequiredUser,
    chapter_id: UUID,
    data: AIConfirmRequest,
    db: AsyncSession = Depends(get_db),
) -> AIConfirmResponse:
    """AI 填充确认：用户确认后写入文档"""
    from .ai_fill_service import AIFillService
    from .models import DossierChapter, ProductDossier

    # 获取章节和品种信息
    ch_stmt = select(DossierChapter).where(DossierChapter.id == chapter_id)
    ch_result = await db.execute(ch_stmt)
    chapter = ch_result.scalar_one_or_none()

    if not chapter:
        raise NotFoundException("章节")

    pd_stmt = select(ProductDossier).where(ProductDossier.id == chapter.product_dossier_id)
    pd_result = await db.execute(pd_stmt)
    dossier = pd_result.scalar_one_or_none()

    if not dossier:
        raise NotFoundException("品种资料")

    user_confirmed_fields = data.fields

    service = AIFillService(db)
    result = await service.confirm_and_fill(dossier, chapter, user_confirmed_fields)

    return AIConfirmResponse(
        code=200,
        data=AIConfirmData.model_validate(result),
        message=result.get("message", "完成"),
    )


@router.get("/chapters/{chapter_code}/asset-categories", response_model=AssetCategoryListApiResponse)
async def get_asset_categories(
    current_user: RequiredUser,
    chapter_code: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """获取章节的素材分类列表"""
    from .ai_fill_service import AIFillService

    service = AIFillService(db)
    categories = await service.get_asset_categories(chapter_code)

    return build_response(data=categories, message="获取成功")


@router.post("/assets/{asset_id}/split-preview", response_model=SplitPreviewResponse)
async def split_preview(
    current_user: RequiredUser,
    asset_id: UUID,
    data: SplitPreviewRequest,
    db: AsyncSession = Depends(get_db),
) -> SplitPreviewResponse:
    """AI 拆分预览：识别多页 PDF 每页的类型"""
    from .ai_fill_service import AIFillService
    from .models import ChapterAsset

    stmt = select(ChapterAsset).where(ChapterAsset.id == asset_id)
    db_result = await db.execute(stmt)
    asset = db_result.scalar_one_or_none()

    if not asset:
        raise NotFoundException("素材")

    available_appendix_slots = data.available_appendix_slots

    service = AIFillService(db)
    result = await service.preview_page_splits(asset, available_appendix_slots)

    if not result["success"]:
        raise AppException(status_code=500, message=result["message"])

    return SplitPreviewResponse(
        code=200,
        data=SplitPreviewData.model_validate(result),
        message=result["message"],
    )


@router.post("/chapters/{chapter_id}/split-confirm", response_model=SplitConfirmResponse)
async def split_confirm_and_insert(
    current_user: RequiredUser,
    chapter_id: UUID,
    data: SplitConfirmRequest,
    db: AsyncSession = Depends(get_db),
) -> SplitConfirmResponse:
    """AI 拆分确认：将各页转为图片插入模板"""
    from .ai_fill_service import AIFillService
    from .models import DossierChapter, ProductDossier

    ch_stmt = select(DossierChapter).where(DossierChapter.id == chapter_id)
    ch_result = await db.execute(ch_stmt)
    chapter = ch_result.scalar_one_or_none()

    if not chapter:
        raise NotFoundException("章节")

    pd_stmt = select(ProductDossier).where(ProductDossier.id == chapter.product_dossier_id)
    pd_result = await db.execute(pd_stmt)
    dossier = pd_result.scalar_one_or_none()

    if not dossier:
        raise NotFoundException("品种资料")

    splits = data.splits

    service = AIFillService(db)
    result = await service.confirm_page_splits_and_insert(dossier, chapter, splits)

    if not result["success"]:
        raise AppException(status_code=500, message=result["message"])

    return SplitConfirmResponse(
        code=200,
        data=SplitConfirmData.model_validate(result),
        message=result["message"],
    )


@router.get("/chapters/{chapter_code}/appendix-slots", response_model=StringListApiResponse)
async def get_appendix_slots(
    current_user: RequiredUser,
    chapter_code: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """获取章节的所有附录位置（从 FieldMapping 汇总）"""
    from sqlalchemy import and_, select

    stmt = select(FieldMapping).where(
        and_(
            FieldMapping.chapter_code == chapter_code,
            FieldMapping.appendix_slot.isnot(None),
            ~FieldMapping.is_deleted,
        )
    )
    result = await db.execute(stmt)
    mappings = result.scalars().all()

    slots = sorted(set(m.appendix_slot for m in mappings if m.appendix_slot))
    return build_response(data=slots, message="获取成功")


# ====== Asset Usage (素材使用管理) ======


@router.get("/chapters/{chapter_id}/available-assets", response_model=AvailableAssetListApiResponse)
async def list_available_assets(
    current_user: RequiredUser,
    chapter_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """获取章节的可用素材列表（自有 + 继承自父级）及使用状态

    返回每个素材的：
    - 基本信息（id, filename, file_type 等）
    - is_inherited: 是否继承自父级章节
    - is_selected: 是否已选择用于本章节
    - parent_chapter_code: 继承来源的章节编号（仅继承素材有）
    """
    service = DossierService(db)
    available = await service.get_available_assets(chapter_id)

    result = []
    for item in available:
        asset = item["asset"]
        result.append(
            {
                "id": str(asset.id),
                "chapter_id": str(asset.chapter_id),
                "original_filename": asset.original_filename,
                "file_path": asset.file_path,
                "file_type": asset.file_type,
                "file_size": asset.file_size,
                "uploaded_at": asset.uploaded_at.isoformat() if asset.uploaded_at else None,
                "category_id": str(asset.category_id) if asset.category_id else None,
                "is_inherited": item["is_inherited"],
                "is_selected": item["is_selected"],
                "parent_chapter_code": item["parent_chapter_code"],
            }
        )

    return build_response(data=result, message="获取成功")


@router.patch("/chapters/{chapter_id}/asset-usages/{asset_id}", response_model=AssetUsageToggleResponse)
async def toggle_asset_usage(
    current_user: RequiredUser,
    chapter_id: UUID,
    asset_id: UUID,
    body: AssetUsageToggleRequest,
    db: AsyncSession = Depends(get_db),
) -> AssetUsageToggleResponse:
    """切换素材的使用状态（勾选/取消勾选）

    body: {"is_selected": true/false}
    """
    service = DossierService(db)
    try:
        result = await service.toggle_asset_usage(chapter_id, asset_id, body.is_selected)
        return AssetUsageToggleResponse(
            code=200,
            data=AssetUsageToggleData.model_validate(result),
            message="更新成功",
        )
    except ValueError as e:
        raise BadRequestException(str(e))


@router.get("/chapters/{chapter_id}/selected-assets", response_model=AssetListApiResponse)
async def list_selected_assets(
    current_user: RequiredUser,
    chapter_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """获取章节已选择使用的素材列表（is_selected=true）

    用于章节更新、AI 填充等操作前查看将要使用的素材。
    """
    service = DossierService(db)
    assets = await service.get_selected_assets_for_chapter(chapter_id)
    return build_response(data=[AssetResponse.model_validate(a) for a in assets], message="获取成功")
