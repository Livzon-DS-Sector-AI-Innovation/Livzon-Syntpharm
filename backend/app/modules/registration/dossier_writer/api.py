"""Dossier Writer API endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.core.response import ApiResponse, build_response, error_response, success_response

from .field_models import FieldFillResult, FieldMapping
from .models import ChapterAsset, DossierChapter, ProductDossier
from .schemas import (
    AIConfirmRequest,
    AIConfirmResponse,
    AssetCategoryUpdateRequest,
    AssetCategoryUpdateResponse,
    AssetResponse,
    AssetUploadResponse,
    AssetUsageToggleRequest,
    AssetUsageToggleResponse,
    ExportRequest,
    ProductDossierCreate,
    ProductDossierListResponse,
    ProductDossierResponse,
    ProductDossierUpdate,
    SplitConfirmRequest,
    SplitConfirmResponse,
    SplitPreviewRequest,
)
from .service import DossierService

logger = logging.getLogger(__name__)

router = APIRouter()


# ====== Product Dossier ======


@router.post("/products", response_model=dict)
async def create_product_dossier(
    current_user: CurrentUser,
    data: ProductDossierCreate,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """创建品种资料"""
    service = DossierService(db)
    try:
        dossier = await service.create_product_dossier(data)
        return success_response(data=ProductDossierResponse.model_validate(dossier), message="创建成功")
    except ValueError as e:
        return error_response(message=str(e), status_code=400)


@router.get("/products", response_model=dict)
async def list_product_dossiers(
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """获取品种资料列表"""
    service = DossierService(db)
    items, total = await service.list_product_dossiers(skip, limit)
    return success_response(
        data={
            "items": [ProductDossierListResponse.model_validate(i) for i in items],
            "total": total,
            "skip": skip,
            "limit": limit,
        },
        message="获取成功",
    )


@router.get("/products/{dossier_id}", response_model=dict)
async def get_product_dossier(
    current_user: CurrentUser,
    dossier_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """获取品种资料详情"""
    service = DossierService(db)
    dossier = await service.get_product_dossier(dossier_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="品种资料不存在")
    return success_response(data=ProductDossierResponse.model_validate(dossier), message="获取成功")


@router.put("/products/{dossier_id}", response_model=dict)
async def update_product_dossier(
    current_user: CurrentUser,
    dossier_id: UUID,
    data: ProductDossierUpdate,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """更新品种资料"""
    service = DossierService(db)
    dossier = await service.update_product_dossier(dossier_id, data)
    if not dossier:
        raise HTTPException(status_code=404, detail="品种资料不存在")
    return success_response(data=ProductDossierResponse.model_validate(dossier), message="更新成功")


@router.delete("/products/{dossier_id}", response_model=dict)
async def delete_product_dossier(
    current_user: CurrentUser,
    dossier_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """删除品种资料"""
    service = DossierService(db)
    success = await service.delete_product_dossier(dossier_id)
    if not success:
        raise HTTPException(status_code=404, detail="品种资料不存在")
    return success_response(message="删除成功")


# ====== Template Upload ======


@router.post("/products/{dossier_id}/templates", response_model=dict)
async def upload_templates(
    current_user: CurrentUser,
    dossier_id: UUID,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
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

    return success_response(
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


@router.post("/products/{dossier_id}/parse", response_model=dict)
async def parse_templates(
    current_user: CurrentUser,
    dossier_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """解析模板生成章节树"""
    service = DossierService(db)
    result = await service.parse_templates(dossier_id)

    if result["success"]:
        return success_response(data=result, message=result["message"])
    else:
        return error_response(message=result["message"], detail=result.get("error"))


# ====== Chapter ======


@router.get("/products/{dossier_id}/chapters", response_model=dict)
async def get_chapter_tree(
    current_user: CurrentUser,
    dossier_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """获取章节树"""
    service = DossierService(db)
    chapters = await service.get_chapter_tree(dossier_id)
    return success_response(data=chapters, message="获取成功")


@router.get("/chapters/{chapter_id}", response_model=dict)
async def get_chapter_detail(
    current_user: CurrentUser,
    chapter_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """获取章节详情"""
    service = DossierService(db)
    chapter = await service.get_chapter_detail(chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    return success_response(data=chapter, message="获取成功")


# ====== Asset ======


@router.post("/chapters/{chapter_id}/assets", response_model=dict)
async def upload_asset(
    current_user: CurrentUser,
    chapter_id: UUID,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
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

    return success_response(
        data={
            "assets": [r.model_dump(mode="json") for r in results],
            "count": len(results),
        },
        message=f"成功上传 {len(results)} 个素材",
    )


@router.get("/chapters/{chapter_id}/assets", response_model=dict)
async def list_assets(
    current_user: CurrentUser,
    chapter_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """获取章节自有素材列表（不含继承素材）

    如需获取包含继承素材的完整列表，请使用 /available-assets 接口。
    """
    service = DossierService(db)
    assets = await service.list_chapter_assets(chapter_id)
    return success_response(data=[AssetResponse.model_validate(a) for a in assets], message="获取成功")


@router.delete("/assets/{asset_id}", response_model=dict)
async def delete_asset(
    current_user: CurrentUser,
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """删除素材"""
    service = DossierService(db)
    success = await service.delete_asset(asset_id)
    if not success:
        raise HTTPException(status_code=404, detail="素材不存在")
    return success_response(message="删除成功")


@router.patch("/assets/{asset_id}", response_model=AssetCategoryUpdateResponse)
async def update_asset_category(
    current_user: CurrentUser,
    asset_id: UUID,
    body: AssetCategoryUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """更新素材的分类"""
    asset = await db.get(ChapterAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="素材不存在")

    category_id = body.category_id
    asset.category_id = category_id if category_id else None
    await db.commit()
    result = await db.execute(select(ChapterAsset).where(ChapterAsset.id == asset_id))
    asset = result.scalar_one()

    return build_response(
        data={
            "id": str(asset.id),
            "category_id": str(asset.category_id) if asset.category_id else None,
        },
        message="分类已更新",
    )


# ====== Export ======


@router.post("/products/{dossier_id}/export", response_model=dict)
async def export_dossier(
    current_user: CurrentUser,
    dossier_id: UUID,
    data: ExportRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """导出品种资料"""
    service = DossierService(db)
    result = await service.export_dossier(dossier_id, data.chapter_ids)

    if result["success"]:
        return success_response(data=result, message=result["message"])
    else:
        return error_response(message=result["message"])


@router.get("/products/{dossier_id}/download")
async def download_exported_file(
    current_user: CurrentUser,
    dossier_id: UUID,
    filename: str = Query(..., description="文件名"),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """下载导出的文件"""
    service = DossierService(db)
    dossier = await service.repo.get_product_dossier(dossier_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="品种资料不存在")

    from pathlib import Path

    file_path = Path(dossier.outputs_path or "") / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.get("/chapters/{chapter_id}/preview", response_model=dict)
async def get_chapter_preview(
    current_user: CurrentUser,
    chapter_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """获取章节预览内容"""
    service = DossierService(db)
    result = await service.get_chapter_preview(chapter_id)

    if result["success"]:
        return success_response(data=result, message="获取预览成功")
    else:
        return error_response(message=result["message"])


@router.get("/chapters/{chapter_id}/docx-file")
async def get_chapter_docx_file(
    current_user: CurrentUser,
    chapter_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """获取章节的 docx 工作副本文件，用于前端 docx-preview 渲染"""
    from pathlib import Path

    chapter = await db.get(DossierChapter, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    dossier = await db.get(ProductDossier, chapter.product_dossier_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="品种资料不存在")

    if not chapter.working_file:
        raise HTTPException(status_code=404, detail="该章节尚无工作副本文件")

    file_path = Path(dossier.working_path or "") / chapter.working_file
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="工作副本文件不存在")

    return FileResponse(
        path=str(file_path),
        filename=chapter.working_file,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@router.post("/products/{dossier_id}/match-assets", response_model=dict)
async def match_assets_to_chapters(
    current_user: CurrentUser,
    dossier_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """智能匹配素材到章节"""
    service = DossierService(db)
    result = await service.match_assets_to_chapters(dossier_id)

    if result["success"]:
        return success_response(data=result, message=result["message"])
    else:
        return error_response(message=result["message"])


# ====== Field Mapping ======

from .field_fill_service import FieldFillService  # noqa: E402

# from .field_mapping_config import S6_FIELD_MAPPINGS  # 已废弃


@router.post("/chapters/{chapter_id}/fill-fields", response_model=dict)
async def fill_chapter_fields(
    current_user: CurrentUser,
    chapter_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """执行字段填充 - 从素材提取内容并填充到章节"""
    service = DossierService(db)
    fill_service = FieldFillService(db)

    # 获取章节信息
    chapter = await service.get_chapter_detail(chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    # 获取品种信息
    dossier = await service.get_product_dossier(chapter.product_dossier_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="品种资料不存在")

    # 获取章节素材
    assets = await service.list_chapter_assets(chapter_id)

    # 获取章节模型用于填充
    ch_model = await db.get(DossierChapter, chapter_id)
    if not ch_model:
        raise HTTPException(status_code=404, detail="章节不存在")

    # 执行填充
    result = await fill_service.fill_chapter_fields(dossier, ch_model, assets)

    return success_response(data=result, message=result["message"])


@router.get("/chapters/{chapter_code}/field-mappings", response_model=dict)
async def get_field_mappings(
    current_user: CurrentUser,
    chapter_code: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """获取章节的字段映射配置"""
    fill_service = FieldFillService(db)
    mappings = await fill_service.get_field_mappings(chapter_code)

    return success_response(
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


@router.post("/field-mappings/init-s6", response_model=dict)
async def init_s6_field_mappings(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """初始化 S.6 包装系统的字段映射配置（从数据库 seed 数据）"""
    from .service import DossierService

    service = DossierService(db)
    result = await service.init_chapter_ai_config("3.2.S.6")
    return success_response(data=result, message=result["message"])


@router.post("/field-mappings/init-s7", response_model=dict)
async def init_s7_field_mappings(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
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

    return success_response(data={"chapters": results}, message="S.7 稳定性模块初始化完成")


@router.get("/chapters/{chapter_id}/fill-results", response_model=dict)
async def get_fill_results(
    current_user: CurrentUser,
    chapter_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
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

    return success_response(
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


@router.post("/chapters/{chapter_id}/ai-preview", response_model=dict)
async def ai_preview_extraction(
    current_user: CurrentUser,
    chapter_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """启动AI智能解析预览任务（异步）"""
    from .models import DossierChapter
    from .ocr_task_repository import OcrTaskRepository
    from .service import DossierService

    # 获取章节
    ch_stmt = select(DossierChapter).where(DossierChapter.id == chapter_id)
    ch_result = await db.execute(ch_stmt)
    chapter = ch_result.scalar_one_or_none()

    if not chapter:
        return error_response(message="章节不存在", status_code=404)

    # 获取章节素材
    service = DossierService(db)
    assets = await service.list_chapter_assets(chapter_id)

    if not assets:
        return error_response(message="请先上传素材", status_code=400)

    # 为每个素材创建OCR任务
    repo = OcrTaskRepository(db)
    task_ids = []

    for asset in assets:
        task = await repo.create_task(
            asset_id=asset.id,
            chapter_id=chapter_id,
            task_type="preview_extraction",
        )
        task_ids.append(str(task.id))

        # 使用 FastAPI BackgroundTasks 调度后台任务
        from .ocr_worker import execute_ocr_extraction

        background_tasks.add_task(
            execute_ocr_extraction,
            task_id=task.id,
            file_path=asset.file_path,
            task_type="preview_extraction",
            chapter_id=chapter_id,
        )

    await db.commit()

    return success_response(
        data={
            "task_ids": task_ids,
            "status": "pending",
            "message": f"已启动 {len(task_ids)} 个OCR提取任务",
        },
        message="任务已启动，请轮询查询结果",
    )





@router.get("/ocr-tasks/{task_id}", response_model=dict)
async def get_ocr_task_status(
    current_user: CurrentUser,
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """查询OCR任务状态和结果"""
    from .ocr_task_repository import OcrTaskRepository

    repo = OcrTaskRepository(db)
    task = await repo.get_task(task_id)

    if not task:
        return error_response(message="任务不存在", status_code=404)

    response_data = {
        "id": str(task.id),
        "asset_id": str(task.asset_id),
        "task_type": task.task_type,
        "status": task.status,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "total_pages": task.total_pages,
        "processed_pages": task.processed_pages,
        "error_message": task.error_message,
    }

    # Include result only if completed
    if task.status == "completed" and task.result_data:
        response_data["result"] = task.result_data

    # Calculate progress percentage
    if task.total_pages and task.total_pages > 0:
        response_data["progress"] = round(
            (task.processed_pages / task.total_pages) * 100, 2
        )

    return success_response(data=response_data)


@router.post("/chapters/{chapter_id}/ai-confirm", response_model=AIConfirmResponse)
async def ai_confirm_and_fill(
    current_user: CurrentUser,
    chapter_id: UUID,
    data: AIConfirmRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """AI 填充确认：用户确认后写入文档"""
    from .ai_fill_service import AIFillService
    from .models import DossierChapter, ProductDossier

    # 获取章节和品种信息
    ch_stmt = select(DossierChapter).where(DossierChapter.id == chapter_id)
    ch_result = await db.execute(ch_stmt)
    chapter = ch_result.scalar_one_or_none()

    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    pd_stmt = select(ProductDossier).where(ProductDossier.id == chapter.product_dossier_id)
    pd_result = await db.execute(pd_stmt)
    dossier = pd_result.scalar_one_or_none()

    if not dossier:
        raise HTTPException(status_code=404, detail="品种资料不存在")

    user_confirmed_fields = data.fields

    service = AIFillService(db)
    result = await service.confirm_and_fill(dossier, chapter, user_confirmed_fields)

    return build_response(data=result, message=result.get("message", "完成"))


@router.get("/chapters/{chapter_code}/asset-categories", response_model=dict)
async def get_asset_categories(
    current_user: CurrentUser,
    chapter_code: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """获取章节的素材分类列表"""
    from .ai_fill_service import AIFillService

    service = AIFillService(db)
    categories = await service.get_asset_categories(chapter_code)

    return success_response(data=categories, message="获取成功")


@router.post("/assets/{asset_id}/split-preview", response_model=dict)
async def split_preview(
    current_user: CurrentUser,
    asset_id: UUID,
    data: SplitPreviewRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """启动AI拆分预览任务（异步）"""
    from .models import ChapterAsset
    from .ocr_task_repository import OcrTaskRepository

    stmt = select(ChapterAsset).where(ChapterAsset.id == asset_id)
    db_result = await db.execute(stmt)
    asset = db_result.scalar_one_or_none()

    if not asset:
        return error_response(message="素材不存在", status_code=404)

    # Check if it's a PDF
    from pathlib import Path
    if Path(asset.file_path).suffix.lower() != ".pdf":
        return error_response(message="仅支持 PDF 文件的页拆分", status_code=400)

    # Create OCR task
    repo = OcrTaskRepository(db)
    task = await repo.create_task(
        asset_id=asset.id,
        chapter_id=asset.chapter_id,
        task_type="split_preview",
    )

    # Schedule background task
    from .ocr_worker import execute_ocr_extraction

    background_tasks.add_task(
        execute_ocr_extraction,
        task_id=task.id,
        file_path=asset.file_path,
        task_type="split_preview",
        chapter_id=asset.chapter_id,
    )

    await db.commit()

    return success_response(
        data={
            "task_id": str(task.id),
            "status": "pending",
            "message": "已启动OCR提取任务，请轮询查询结果后进行拆分",
        },
        message="任务已启动",
    )



@router.post("/chapters/{chapter_id}/split-confirm", response_model=SplitConfirmResponse)
async def split_confirm_and_insert(
    current_user: CurrentUser,
    chapter_id: UUID,
    data: SplitConfirmRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """AI 拆分确认：将各页转为图片插入模板"""
    from .ai_fill_service import AIFillService
    from .models import DossierChapter, ProductDossier

    ch_stmt = select(DossierChapter).where(DossierChapter.id == chapter_id)
    ch_result = await db.execute(ch_stmt)
    chapter = ch_result.scalar_one_or_none()

    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    pd_stmt = select(ProductDossier).where(ProductDossier.id == chapter.product_dossier_id)
    pd_result = await db.execute(pd_stmt)
    dossier = pd_result.scalar_one_or_none()

    if not dossier:
        raise HTTPException(status_code=404, detail="品种资料不存在")

    splits = data.splits

    service = AIFillService(db)
    result = await service.confirm_page_splits_and_insert(dossier, chapter, splits)

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])

    return build_response(data=result, message=result["message"])


@router.get("/chapters/{chapter_code}/appendix-slots", response_model=dict)
async def get_appendix_slots(
    current_user: CurrentUser,
    chapter_code: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
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
    return success_response(data=slots, message="获取成功")


# ====== Asset Usage (素材使用管理) ======


@router.get("/chapters/{chapter_id}/available-assets", response_model=dict)
async def list_available_assets(
    current_user: CurrentUser,
    chapter_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
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

    return success_response(data=result, message="获取成功")


@router.patch("/chapters/{chapter_id}/asset-usages/{asset_id}", response_model=AssetUsageToggleResponse)
async def toggle_asset_usage(
    current_user: CurrentUser,
    chapter_id: UUID,
    asset_id: UUID,
    body: AssetUsageToggleRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """切换素材的使用状态（勾选/取消勾选）

    body: {"is_selected": true/false}
    """
    service = DossierService(db)
    try:
        result = await service.toggle_asset_usage(chapter_id, asset_id, body.is_selected)
        return build_response(data=result, message="更新成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/chapters/{chapter_id}/selected-assets", response_model=dict)
async def list_selected_assets(
    current_user: CurrentUser,
    chapter_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """获取章节已选择使用的素材列表（is_selected=true）

    用于章节更新、AI 填充等操作前查看将要使用的素材。
    """
    service = DossierService(db)
    assets = await service.get_selected_assets_for_chapter(chapter_id)
    return success_response(data=[AssetResponse.model_validate(a) for a in assets], message="获取成功")
