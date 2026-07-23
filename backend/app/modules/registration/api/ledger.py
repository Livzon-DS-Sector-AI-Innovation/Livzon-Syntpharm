"""Registration ledger API endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import TypeAdapter
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.core.response import error_response, success_response
from app.modules.registration.schemas.ledger import (
    CoppCertificateCreate,
    CoppCertificateResponse,
    DomesticApprovalCreate,
    DomesticApprovalResponse,
    InternationalReviewCreate,
    InternationalReviewResponse,
    LedgerSummary,
    OverseasApprovalCreate,
    OverseasApprovalResponse,
    WcCertificateCreate,
    WcCertificateResponse,
)
from app.modules.registration.service import ledger as ledger_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Domestic Approvals ─────────────────────────────────────────────


@router.get("/domestic-approvals")
async def get(
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> Any:
    items = await ledger_service.list_domestic_approvals(db, skip, limit)
    adapter = TypeAdapter(list[DomesticApprovalResponse])
    validated = adapter.validate_python(items)
    return success_response(data=adapter.dump_python(validated, mode="json"))


@router.post("/domestic-approvals", response_model=DomesticApprovalResponse)
async def post(
    current_user: CurrentUser,
    data: DomesticApprovalCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    item = await ledger_service.create_domestic_approval(db, data)
    return item


@router.post("/domestic-approvals/import")  # type: ignore[no-redef]
async def post(  # noqa: F811
    current_user: CurrentUser,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> Any:
    try:
        content = await file.read()
        file_size = len(content)
        filename = file.filename or "unknown.xlsx"

        # 解析 Excel
        parse_result = ledger_service.import_domestic_approvals_from_excel(content)

        # 记录日志
        logger.info(f"📥 Import file: {filename}, size: {file_size} bytes")
        logger.info(
            f"📊 Parse result: total={parse_result['total_rows']}, "
            f"success={parse_result['success_count']}, "
            f"skipped={parse_result['skipped_count']}, "
            f"errors={parse_result['error_count']}"
        )
        if parse_result["errors"]:
            logger.info(f"⚠️ Parse errors: {parse_result['errors'][:5]}")

        # 如果解析失败，直接返回
        if parse_result["success_count"] == 0:
            error_msg = parse_result["errors"][0] if parse_result["errors"] else "未解析到有效数据"
            return success_response(
                data={
                    "count": 0,
                    "message": f"文件已解析但未导入有效数据: {error_msg}",
                    "total_rows": parse_result["total_rows"],
                    "success_count": 0,
                    "skipped_count": parse_result["skipped_count"],
                    "error_count": parse_result["error_count"],
                    "errors": parse_result["errors"],
                }
            )

        # 写入数据库
        created = []
        db_errors = []
        for i, item in enumerate(parse_result["items"], 1):
            try:
                obj = await ledger_service.create_domestic_approval(db, item)
                created.append(obj)
            except IntegrityError:
                await db.rollback()
                db_errors.append(f"第{i}行: 数据冲突或格式错误")
            except SQLAlchemyError:
                await db.rollback()
                db_errors.append(f"第{i}行: 数据库错误")

        all_errors = parse_result["errors"] + db_errors
        message = f"成功导入 {len(created)} 条记录"
        if db_errors:
            message += f"，{len(db_errors)} 条数据库写入失败"

        return success_response(
            data={
                "count": len(created),
                "message": message,
                "total_rows": parse_result["total_rows"],
                "success_count": len(created),
                "skipped_count": parse_result["skipped_count"],
                "error_count": parse_result["error_count"] + len(db_errors),
                "errors": all_errors,
            }
        )
    except Exception as e:
        logger.error(f"❌ Import failed: {str(e)}", exc_info=True)
        return error_response(message=f"文件解析失败: {str(e)}", status_code=400)


@router.get("/domestic-approvals/export")  # type: ignore[no-redef]
async def get(  # noqa: F811
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    items = await ledger_service.list_domestic_approvals(db)
    excel_bytes = ledger_service.export_domestic_approvals_to_excel(items)

    return StreamingResponse(
        iter([excel_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=domestic_approvals.xlsx"},
    )


# ── Overseas Approvals ─────────────────────────────────────────────


@router.get("/overseas-approvals")  # type: ignore[no-redef]
async def get(  # noqa: F811
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> Any:
    items = await ledger_service.list_overseas_approvals(db, skip, limit)
    adapter = TypeAdapter(list[OverseasApprovalResponse])
    validated = adapter.validate_python(items)
    return success_response(data=adapter.dump_python(validated, mode="json"))


@router.post("/overseas-approvals", response_model=OverseasApprovalResponse)  # type: ignore[no-redef]
async def post(  # noqa: F811
    current_user: CurrentUser,
    data: OverseasApprovalCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    item = await ledger_service.create_overseas_approval(db, data)
    return item


@router.post("/overseas-approvals/import")  # type: ignore[no-redef]
async def post(  # noqa: F811
    current_user: CurrentUser,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> Any:
    try:
        content = await file.read()
        file_size = len(content)
        filename = file.filename or "unknown.xlsx"

        # 记录日志
        logger.info(f"📥 Import file: {filename}, size: {file_size} bytes")

        parse_result = ledger_service.import_overseas_approvals_from_excel(content)

        logger.info(
            f"📊 Parse result: total={parse_result['total_rows']}, "
            f"success={parse_result['success_count']}, "
            f"skipped={parse_result['skipped_count']}, "
            f"errors={parse_result['error_count']}"
        )
        if parse_result["errors"]:
            logger.info(f"⚠️ Parse errors: {parse_result['errors'][:5]}")

        if parse_result["success_count"] == 0:
            error_msg = parse_result["errors"][0] if parse_result["errors"] else "未解析到有效数据"
            return success_response(
                data={
                    "count": 0,
                    "message": f"文件已解析但未导入有效数据: {error_msg}",
                    "total_rows": parse_result["total_rows"],
                    "success_count": 0,
                    "skipped_count": parse_result["skipped_count"],
                    "error_count": parse_result["error_count"],
                    "errors": parse_result["errors"],
                }
            )

        created = []
        db_errors = []
        for i, item in enumerate(parse_result["items"], 1):
            try:
                obj = await ledger_service.create_overseas_approval(db, item)
                created.append(obj)
            except IntegrityError:
                await db.rollback()
                db_errors.append(f"第{i}行: 数据冲突")
            except SQLAlchemyError:
                await db.rollback()
                db_errors.append(f"第{i}行: 数据库错误")

        all_errors = parse_result["errors"] + db_errors
        message = f"成功导入 {len(created)} 条记录"
        if db_errors:
            message += f"，{len(db_errors)} 条数据库写入失败"

        return success_response(
            data={
                "count": len(created),
                "message": message,
                "total_rows": parse_result["total_rows"],
                "success_count": len(created),
                "skipped_count": parse_result["skipped_count"],
                "error_count": parse_result["error_count"] + len(db_errors),
                "errors": all_errors,
            }
        )
    except Exception as e:
        return error_response(message=f"文件解析失败: {str(e)}", status_code=400)


@router.get("/overseas-approvals/export")  # type: ignore[no-redef]
async def get(  # noqa: F811
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    items = await ledger_service.list_overseas_approvals(db)
    excel_bytes = ledger_service.export_overseas_approvals_to_excel(items)

    return StreamingResponse(
        iter([excel_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=overseas_approvals.xlsx"},
    )


# ── International Reviews ──────────────────────────────────────────


@router.get("/international-reviews")  # type: ignore[no-redef]
async def get(  # noqa: F811
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> Any:
    items = await ledger_service.list_international_reviews(db, skip, limit)
    adapter = TypeAdapter(list[InternationalReviewResponse])
    validated = adapter.validate_python(items)
    return success_response(data=adapter.dump_python(validated, mode="json"))


@router.post("/international-reviews", response_model=InternationalReviewResponse)  # type: ignore[no-redef]
async def post(  # noqa: F811
    current_user: CurrentUser,
    data: InternationalReviewCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    item = await ledger_service.create_international_review(db, data)
    return item


@router.post("/international-reviews/import")  # type: ignore[no-redef]
async def post(  # noqa: F811
    current_user: CurrentUser,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> Any:
    try:
        content = await file.read()
        parse_result = ledger_service.import_international_reviews_from_excel(content)

        if parse_result["success_count"] == 0:
            error_msg = parse_result["errors"][0] if parse_result["errors"] else "未解析到有效数据"
            return success_response(
                data={
                    "count": 0,
                    "message": f"文件已解析但未导入有效数据: {error_msg}",
                    "total_rows": parse_result["total_rows"],
                    "success_count": 0,
                    "skipped_count": parse_result["skipped_count"],
                    "error_count": parse_result["error_count"],
                    "errors": parse_result["errors"],
                }
            )

        created = []
        db_errors = []
        for i, item in enumerate(parse_result["items"], 1):
            try:
                obj = await ledger_service.create_international_review(db, item)
                created.append(obj)
            except IntegrityError:
                await db.rollback()
                db_errors.append(f"第{i}行: 数据冲突")
            except SQLAlchemyError:
                await db.rollback()
                db_errors.append(f"第{i}行: 数据库错误")

        all_errors = parse_result["errors"] + db_errors
        message = f"成功导入 {len(created)} 条记录"
        if db_errors:
            message += f"，{len(db_errors)} 条数据库写入失败"

        return success_response(
            data={
                "count": len(created),
                "message": message,
                "total_rows": parse_result["total_rows"],
                "success_count": len(created),
                "skipped_count": parse_result["skipped_count"],
                "error_count": parse_result["error_count"] + len(db_errors),
                "errors": all_errors,
            }
        )
    except Exception as e:
        return error_response(message=f"文件解析失败: {str(e)}", status_code=400)


@router.get("/international-reviews/export")  # type: ignore[no-redef]
async def get(  # noqa: F811
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    items = await ledger_service.list_international_reviews(db)
    excel_bytes = ledger_service.export_international_reviews_to_excel(items)

    return StreamingResponse(
        iter([excel_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=international_reviews.xlsx"},
    )


# ── COPP Certificates ──────────────────────────────────────────────


@router.get("/copp-certificates")  # type: ignore[no-redef]
async def get(  # noqa: F811
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> Any:
    items = await ledger_service.list_copp_certificates(db, skip, limit)
    adapter = TypeAdapter(list[CoppCertificateResponse])
    validated = adapter.validate_python(items)
    return success_response(data=adapter.dump_python(validated, mode="json"))


@router.post("/copp-certificates", response_model=CoppCertificateResponse)  # type: ignore[no-redef]
async def post(  # noqa: F811
    current_user: CurrentUser,
    data: CoppCertificateCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    item = await ledger_service.create_copp_certificate(db, data)
    return item


@router.post("/copp-certificates/import")  # type: ignore[no-redef]
async def post(  # noqa: F811
    current_user: CurrentUser,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> Any:
    try:
        content = await file.read()
        parse_result = ledger_service.import_copp_certificates_from_excel(content)

        if parse_result["success_count"] == 0:
            error_msg = parse_result["errors"][0] if parse_result["errors"] else "未解析到有效数据"
            return success_response(
                data={
                    "count": 0,
                    "message": f"文件已解析但未导入有效数据: {error_msg}",
                    "total_rows": parse_result["total_rows"],
                    "success_count": 0,
                    "skipped_count": parse_result["skipped_count"],
                    "error_count": parse_result["error_count"],
                    "errors": parse_result["errors"],
                }
            )

        created = []
        db_errors = []
        for i, item in enumerate(parse_result["items"], 1):
            try:
                obj = await ledger_service.create_copp_certificate(db, item)
                created.append(obj)
            except IntegrityError:
                await db.rollback()
                db_errors.append(f"第{i}行: 数据冲突")
            except SQLAlchemyError:
                await db.rollback()
                db_errors.append(f"第{i}行: 数据库错误")

        all_errors = parse_result["errors"] + db_errors
        message = f"成功导入 {len(created)} 条记录"
        if db_errors:
            message += f"，{len(db_errors)} 条数据库写入失败"

        return success_response(
            data={
                "count": len(created),
                "message": message,
                "total_rows": parse_result["total_rows"],
                "success_count": len(created),
                "skipped_count": parse_result["skipped_count"],
                "error_count": parse_result["error_count"] + len(db_errors),
                "errors": all_errors,
            }
        )
    except Exception as e:
        return error_response(message=f"文件解析失败: {str(e)}", status_code=400)


@router.get("/copp-certificates/export")  # type: ignore[no-redef]
async def get(  # noqa: F811
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    items = await ledger_service.list_copp_certificates(db)
    excel_bytes = ledger_service.export_copp_certificates_to_excel(items)

    return StreamingResponse(
        iter([excel_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=copp_certificates.xlsx"},
    )


# ── WC Certificates ────────────────────────────────────────────────


@router.get("/wc-certificates")  # type: ignore[no-redef]
async def get(  # noqa: F811
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> Any:
    items = await ledger_service.list_wc_certificates(db, skip, limit)
    adapter = TypeAdapter(list[WcCertificateResponse])
    validated = adapter.validate_python(items)
    return success_response(data=adapter.dump_python(validated, mode="json"))


@router.post("/wc-certificates", response_model=WcCertificateResponse)  # type: ignore[no-redef]
async def post(  # noqa: F811
    current_user: CurrentUser,
    data: WcCertificateCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    item = await ledger_service.create_wc_certificate(db, data)
    return item


@router.post("/wc-certificates/import")  # type: ignore[no-redef]
async def post(  # noqa: F811
    current_user: CurrentUser,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> Any:
    try:
        content = await file.read()
        parse_result = ledger_service.import_wc_certificates_from_excel(content)

        if parse_result["success_count"] == 0:
            error_msg = parse_result["errors"][0] if parse_result["errors"] else "未解析到有效数据"
            return success_response(
                data={
                    "count": 0,
                    "message": f"文件已解析但未导入有效数据: {error_msg}",
                    "total_rows": parse_result["total_rows"],
                    "success_count": 0,
                    "skipped_count": parse_result["skipped_count"],
                    "error_count": parse_result["error_count"],
                    "errors": parse_result["errors"],
                }
            )

        created = []
        db_errors = []
        for i, item in enumerate(parse_result["items"], 1):
            try:
                obj = await ledger_service.create_wc_certificate(db, item)
                created.append(obj)
            except IntegrityError:
                await db.rollback()
                db_errors.append(f"第{i}行: 数据冲突")
            except SQLAlchemyError:
                await db.rollback()
                db_errors.append(f"第{i}行: 数据库错误")

        all_errors = parse_result["errors"] + db_errors
        message = f"成功导入 {len(created)} 条记录"
        if db_errors:
            message += f"，{len(db_errors)} 条数据库写入失败"

        return success_response(
            data={
                "count": len(created),
                "message": message,
                "total_rows": parse_result["total_rows"],
                "success_count": len(created),
                "skipped_count": parse_result["skipped_count"],
                "error_count": parse_result["error_count"] + len(db_errors),
                "errors": all_errors,
            }
        )
    except Exception as e:
        return error_response(message=f"文件解析失败: {str(e)}", status_code=400)


@router.get("/wc-certificates/export")  # type: ignore[no-redef]
async def get(  # noqa: F811
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    items = await ledger_service.list_wc_certificates(db)
    excel_bytes = ledger_service.export_wc_certificates_to_excel(items)

    return StreamingResponse(
        iter([excel_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=wc_certificates.xlsx"},
    )


# ── Dashboard Summary ──────────────────────────────────────────────


@router.get("/summary")  # type: ignore[no-redef]
async def get(  # noqa: F811
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    summary = await ledger_service.get_ledger_summary(db)
    adapter = TypeAdapter(LedgerSummary)
    return success_response(data=adapter.dump_python(summary, mode="json"))


# ── Reviewing (from drugs table) ───────────────────────────────────


@router.get("/reviewing")  # type: ignore[no-redef]
async def get(  # noqa: F811
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """从 drugs 表获取审评中的品种"""
    from sqlalchemy import select

    from app.modules.registration.models.drug import Drug, DrugNode

    stmt = select(Drug).where(~Drug.is_deleted).order_by(Drug.acceptance_date.desc())
    result = await db.execute(stmt)
    drugs = result.scalars().all()

    items = []
    for drug in drugs:
        # 获取节点信息
        node_stmt = (
            select(DrugNode).where(DrugNode.drug_id == drug.id, ~DrugNode.is_deleted).order_by(DrugNode.node_index)
        )
        node_result = await db.execute(node_stmt)
        nodes = node_result.scalars().all()

        node_info = {}
        for node in nodes:
            node_info[f"node_{node.node_index}"] = node.actual_date.isoformat() if node.actual_date else None

        items.append(
            {
                "id": str(drug.id),
                "product_name": drug.name,
                "drug_type": drug.type,
                "acceptance_date": drug.acceptance_date.isoformat() if drug.acceptance_date else None,
                "current_node": drug.current_node,
                **node_info,
                "created_at": drug.created_at.isoformat() if drug.created_at else None,
                "updated_at": drug.updated_at.isoformat() if drug.updated_at else None,
            }
        )

    return success_response(data=items)
