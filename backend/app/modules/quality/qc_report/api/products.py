"""品种、检验项目与双文件导入接口。"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory, get_db
from app.core.deps import RequiredUser
from app.core.exceptions import AppException, NotFoundException
from app.modules.quality.qc_report.repository import get_product
from app.modules.quality.qc_report.schemas import (
    QcDeleteApiResponse,
    QcDeleteResponse,
    QcImportCommitApiResponse,
    QcImportPreviewApiResponse,
    QcItemApiResponse,
    QcItemListApiResponse,
    QcItemUpdate,
    QcProductApiResponse,
    QcProductCreate,
    QcProductListApiResponse,
    QcProductUpdate,
    QcRejudgeApiResponse,
)
from app.modules.quality.qc_report.service import import_service
from app.modules.quality.qc_report.service import product as product_service

logger = logging.getLogger(__name__)

router = APIRouter()


async def _read_file_pair(
    standard_file: UploadFile,
    result_file: UploadFile,
) -> tuple[bytes, str, bytes, str]:
    """按后缀识别两个文件，放错框也能自动纠正。"""
    first_name = (standard_file.filename or "").lower()
    second_name = (result_file.filename or "").lower()

    first_bytes = await standard_file.read()
    second_bytes = await result_file.read()

    if first_name.endswith(".xlsx") and second_name.endswith(".docx"):
        first_bytes, second_bytes = second_bytes, first_bytes
        first_name, second_name = second_name, first_name

    if not first_name.endswith(".docx"):
        raise AppException(status_code=400, message="标准表需要是 Word 文档（.docx）")
    if not second_name.endswith(".xlsx"):
        raise AppException(status_code=400, message="结果表需要是 Excel 文件（.xlsx）")

    return (
        first_bytes,
        standard_file.filename or "标准表.docx",
        second_bytes,
        result_file.filename or "结果表.xlsx",
    )


# ── 品种 ────────────────────────────────────────────────
@router.get("/products", response_model=QcProductListApiResponse, summary="品种列表（含批次统计）")
async def list_products_api(
    current_user: RequiredUser,
    keyword: str | None = Query(default=None, description="品种名称或缩写"),
    category: str | None = Query(default=None, description="物料分类"),
    top_level: str | None = Query(default=None, description="最高等级筛选"),
    db: AsyncSession = Depends(get_db),
) -> QcProductListApiResponse:
    items = await product_service.list_products_with_stats(db, keyword=keyword, category=category, top_level=top_level)
    return QcProductListApiResponse(data=items)


@router.post("/products", response_model=QcProductApiResponse, summary="新建品种（不含文件）")
async def create_product_api(
    current_user: RequiredUser,
    data: QcProductCreate,
    db: AsyncSession = Depends(get_db),
) -> QcProductApiResponse:
    created = await product_service.create_product(db, data, current_user.id)
    await db.commit()
    return QcProductApiResponse(data=created)


@router.get("/products/{product_id}", response_model=QcProductApiResponse, summary="品种详情")
async def get_product_api(
    current_user: RequiredUser,
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> QcProductApiResponse:
    product = await get_product(db, product_id)
    if product is None:
        raise NotFoundException("品种", str(product_id))
    return QcProductApiResponse(data=product_service.to_product_response(product))


@router.put("/products/{product_id}", response_model=QcProductApiResponse, summary="修改品种")
async def update_product_api(
    current_user: RequiredUser,
    product_id: uuid.UUID,
    data: QcProductUpdate,
    db: AsyncSession = Depends(get_db),
) -> QcProductApiResponse:
    updated = await product_service.update_product(db, product_id, data, current_user.id)
    await db.commit()
    return QcProductApiResponse(data=updated)


@router.delete("/products/{product_id}", response_model=QcDeleteApiResponse, summary="删除品种（软删）")
async def delete_product_api(
    current_user: RequiredUser,
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> QcDeleteApiResponse:
    await product_service.delete_product(db, product_id, current_user.id)
    await db.commit()
    return QcDeleteApiResponse(data=QcDeleteResponse(id=product_id))


# ── 检验项目 ────────────────────────────────────────────
@router.get("/products/{product_id}/items", response_model=QcItemListApiResponse, summary="检验项目清单")
async def list_items_api(
    current_user: RequiredUser,
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> QcItemListApiResponse:
    items = await product_service.get_items(db, product_id)
    return QcItemListApiResponse(data=items)


@router.put("/items/{item_id}", response_model=QcItemApiResponse, summary="修改项目标准或 3σ")
async def update_item_api(
    current_user: RequiredUser,
    item_id: uuid.UUID,
    data: QcItemUpdate,
    db: AsyncSession = Depends(get_db),
) -> QcItemApiResponse:
    updated = await product_service.update_item(db, item_id, data, current_user.id)
    await db.commit()
    return QcItemApiResponse(data=updated)


@router.post("/products/{product_id}/rejudge", response_model=QcRejudgeApiResponse, summary="标准变更后重算全部批次")
async def rejudge_api(
    current_user: RequiredUser,
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> QcRejudgeApiResponse:
    result = await product_service.rejudge_product(db, product_id, current_user.id)
    await db.commit()
    return QcRejudgeApiResponse(data=result)


# ── 导入 ────────────────────────────────────────────────
@router.post("/import/preview", response_model=QcImportPreviewApiResponse, summary="解析两个文件并预览")
async def preview_import_api(
    current_user: RequiredUser,
    standard_file: UploadFile = File(..., description="标准表（docx）"),
    result_file: UploadFile = File(..., description="结果表（xlsx）"),
    product_id: uuid.UUID | None = Form(default=None, description="再次导入时传入已有品种，复用历史映射"),
    manual_mapping: str | None = Form(default=None, description='本次人工指定的对应关系 JSON：{"项目名": "列字母"}'),
    db: AsyncSession = Depends(get_db),
) -> QcImportPreviewApiResponse:
    docx_bytes, docx_name, xlsx_bytes, xlsx_name = await _read_file_pair(standard_file, result_file)
    saved_mapping = await product_service.get_saved_mapping(db, product_id) if product_id else None

    mapping: dict[str, str] = {}
    if manual_mapping:
        try:
            parsed = json.loads(manual_mapping)
        except json.JSONDecodeError as exc:
            raise AppException(status_code=400, message="对应关系的格式不正确，应为 JSON") from exc
        if isinstance(parsed, dict):
            mapping = {str(key): str(value) for key, value in parsed.items()}

    preview = import_service.preview_import(
        docx_bytes,
        docx_name,
        xlsx_bytes,
        xlsx_name,
        saved_mapping=saved_mapping,
        manual_mapping=mapping,
    )
    return QcImportPreviewApiResponse(data=preview)


@router.post("/import/commit", response_model=QcImportCommitApiResponse, summary="确认导入并入库")
async def commit_import_api(
    current_user: RequiredUser,
    standard_file: UploadFile = File(..., description="标准表（docx）"),
    result_file: UploadFile = File(..., description="结果表（xlsx）"),
    name: str = Form(..., description="品种名称"),
    abbr: str = Form(..., description="品名缩写"),
    category: str = Form(..., description="物料分类"),
    quality_standard: str | None = Form(default=None, description="质量标准"),
    manual_mapping: str | None = Form(default=None, description="人工指认的 JSON：{项目名: 列名}"),
    resolutions: str | None = Form(default=None, description='冲突裁决 JSON：{"列号|层": "docx"|"excel"|"none"}'),
) -> StreamingResponse:
    """导入提交。返回 text/event-stream，边写库边推真实进度。

    所有可能失败的校验（文件格式、未裁决冲突）都在流开始前完成，
    仍以普通 JSON + 状态码返回；流里只出现进度、done、error 三类事件。
    """
    docx_bytes, docx_name, xlsx_bytes, xlsx_name = await _read_file_pair(standard_file, result_file)

    mapping: dict[str, str] = {}
    if manual_mapping:
        try:
            parsed = json.loads(manual_mapping)
        except json.JSONDecodeError as exc:
            raise AppException(status_code=400, message="人工指认的格式不正确，应为 JSON") from exc
        if isinstance(parsed, dict):
            mapping = {str(key): str(value) for key, value in parsed.items()}

    choices: dict[str, str] = {}
    if resolutions:
        try:
            parsed_choices = json.loads(resolutions)
        except json.JSONDecodeError as exc:
            raise AppException(status_code=400, message="冲突裁决的格式不正确，应为 JSON") from exc
        if isinstance(parsed_choices, dict):
            choices = {str(key): str(value) for key, value in parsed_choices.items()}

    # 409 / 400 在这里抛出，仍是普通 JSON 响应
    prepared = import_service.prepare_import(
        docx_bytes=docx_bytes,
        docx_name=docx_name,
        xlsx_bytes=xlsx_bytes,
        xlsx_name=xlsx_name,
        name=name,
        abbr=abbr,
        category=category,
        quality_standard=quality_standard,
        manual_mapping=mapping,
        resolutions=choices,
    )

    async def event_stream() -> AsyncIterator[bytes]:
        queue: asyncio.Queue[dict[str, object] | None] = asyncio.Queue()

        async def emit(payload: dict[str, object]) -> None:
            await queue.put(payload)

        async def worker() -> None:
            # 流式响应不能用 get_db（它会在 yield 后自动 commit），这里自建会话
            async with async_session_factory() as session:
                try:
                    result = await import_service.write_prepared(
                        session,
                        prepared,
                        user_id=current_user.id,
                        user_name=current_user.name,
                        on_progress=emit,
                    )
                    await session.commit()
                    await emit(
                        {
                            "stage": "done",
                            "percent": 100,
                            "message": "导入完成",
                            "result": result.model_dump(mode="json"),
                        }
                    )
                except Exception as exc:  # noqa: BLE001 - 任何失败都要回滚并告知前端
                    await session.rollback()
                    logger.exception("qc_report import failed")
                    await emit({"stage": "error", "percent": 100, "message": str(exc)})
                finally:
                    await queue.put(None)

        task = asyncio.create_task(worker())
        try:
            # 首行立即冲刷，避免代理缓冲把整段进度攒到最后
            yield b": connected\n\n"
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n".encode()
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


__all__ = ["router"]
