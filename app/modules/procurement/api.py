from urllib.parse import quote
from uuid import UUID

from fastapi import Depends, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import CurrentUser
from app.core.response import paginated_response, success_response
from app.modules.procurement.contract_generator import (
    generate_contract,
    get_contract_template_metadata,
)
from app.modules.procurement.schemas import (
    ContractCategory,
    ContractGenerateRequest,
    ContractTemplateMetadata,
    InvoiceRecognitionRecordDeleteRequest,
    InvoiceRecognitionRecordDeleteResponse,
    InvoiceRecognitionRecordDeleteResult,
    InvoiceRecognitionRecordListResponse,
    InvoiceRecognitionRecordResponse,
    InvoiceRecognitionResponse,
    PurchaseApprovalRequest,
    PurchaseApprovalRole,
    PurchaseApprovalView,
    PurchaseOrderListResponse,
    PurchaseRequestApiResponse,
    PurchaseRequestCategory,
    PurchaseRequestCreate,
    PurchaseRequestListResponse,
    PurchaseRequestStatus,
    PurchaseRequestUpdate,
)
from app.modules.procurement.service import (
    PURCHASE_CATEGORY_LABELS,
    DuplicateInvoiceError,
    approve_purchase_request,
    batch_delete_invoice_recognition_records,
    create_purchase_request,
    delete_invoice_recognition_record,
    export_purchase_order_lines_xlsx,
    get_purchase_request,
    list_invoice_recognition_records,
    list_purchase_order_lines,
    list_purchase_requests,
    recognize_and_store_invoice_pdf,
    reject_purchase_request,
    submit_purchase_request,
    update_purchase_request,
)
from app.shared.module_api import create_module_router
from app.shared.module_registry import MODULES_BY_CODE

router = create_module_router(MODULES_BY_CODE["procurement"])

settings = get_settings()
MAX_INVOICE_PDF_UPLOAD_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
INVOICE_UPLOAD_CHUNK_SIZE = 1024 * 1024


@router.post(
    "/invoices/recognize",
    summary="识别采购发票 PDF",
    description=(
        "从电子发票 PDF 中识别发票号码、开票日期、销售方名称、"
        "税额合计和价税合计（小写）。开启明细识别时额外识别项目名称、单位和数量。"
    ),
    response_model=InvoiceRecognitionResponse,
)
async def recognize_invoice(
    current_user: CurrentUser,
    include_details: bool = Form(False, description="是否识别发票明细"),
    file: UploadFile = File(..., description="电子发票 PDF 文件"),
    db: AsyncSession = Depends(get_db),
):
    filename = file.filename or ""
    allowed_content_types = {"application/pdf", "application/octet-stream"}
    if file.content_type not in allowed_content_types and not filename.lower().endswith(
        ".pdf"
    ):
        raise HTTPException(status_code=400, detail="请上传 PDF 文件")

    pdf_bytes = await _read_upload_file_with_limit(file)
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="上传文件为空")

    try:
        result = await recognize_and_store_invoice_pdf(
            db,
            pdf_bytes,
            file_name=filename,
            include_details=include_details,
        )
    except DuplicateInvoiceError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"发票识别失败：{exc}") from exc

    return success_response(
        data=InvoiceRecognitionRecordResponse.model_validate(result).model_dump(
            mode="json"
        )
    )


async def _read_upload_file_with_limit(file: UploadFile) -> bytes:
    chunks: list[bytes] = []
    total_size = 0
    while True:
        chunk = await file.read(INVOICE_UPLOAD_CHUNK_SIZE)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > MAX_INVOICE_PDF_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"PDF 文件不能超过 {settings.MAX_UPLOAD_SIZE_MB}MB",
            )
        chunks.append(chunk)

    return b"".join(chunks)


@router.get(
    "/invoices/recognition-records",
    summary="查询采购发票识别记录",
    description="查询已经保存到数据库的采购发票识别结果，支持按关键字、销售方和发票号码筛选。",
    response_model=InvoiceRecognitionRecordListResponse,
)
async def list_invoice_records(
    current_user: CurrentUser,
    keyword: str | None = Query(None, description="文件名、发票号码或销售方关键词"),
    seller_name: str | None = Query(None, description="销售方名称"),
    invoice_number: str | None = Query(None, description="发票号码"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    db: AsyncSession = Depends(get_db),
):
    records, total = await list_invoice_recognition_records(
        db,
        keyword=keyword,
        seller_name=seller_name,
        invoice_number=invoice_number,
        page=page,
        page_size=page_size,
    )
    data = [
        InvoiceRecognitionRecordResponse.model_validate(record).model_dump(mode="json")
        for record in records
    ]
    return paginated_response(data, page, page_size, total)


@router.delete(
    "/invoices/recognition-records/{record_id}",
    summary="删除采购发票识别记录",
    description="软删除单条采购发票识别历史记录。",
    response_model=InvoiceRecognitionRecordDeleteResponse,
)
async def delete_invoice_record(
    current_user: CurrentUser,
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    deleted = await delete_invoice_recognition_record(db, record_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="识别记录不存在或已删除")

    return success_response(
        data=InvoiceRecognitionRecordDeleteResult(
            success_count=1,
            fail_count=0,
        ).model_dump(mode="json"),
        message="识别记录删除成功",
    )


@router.post(
    "/invoices/recognition-records/batch-delete",
    summary="批量删除采购发票识别记录",
    description="软删除多条采购发票识别历史记录。",
    response_model=InvoiceRecognitionRecordDeleteResponse,
)
async def batch_delete_invoice_records(
    current_user: CurrentUser,
    payload: InvoiceRecognitionRecordDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    deleted_count = await batch_delete_invoice_recognition_records(db, payload.ids)
    return success_response(
        data=InvoiceRecognitionRecordDeleteResult(
            success_count=deleted_count,
            fail_count=max(0, len(payload.ids) - deleted_count),
        ).model_dump(mode="json"),
        message="识别记录删除成功",
    )


@router.get(
    "/purchase-orders",
    summary="查询采购订单月度汇总",
    description="按采购分类、年份和月份汇总整月已审批通过的采购申请明细。",
    response_model=PurchaseOrderListResponse,
)
async def list_purchase_order_records(
    current_user: CurrentUser,
    category: PurchaseRequestCategory | None = Query(None, description="采购分类"),
    year: int = Query(..., ge=2000, le=2100, description="年份"),
    month: int = Query(..., ge=1, le=12, description="月份"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    db: AsyncSession = Depends(get_db),
):
    lines, total = await list_purchase_order_lines(
        db,
        category=category.value if category else None,
        year=year,
        month=month,
        page=page,
        page_size=page_size,
    )
    data = [line.model_dump(mode="json") for line in lines]
    return paginated_response(data, page, page_size, total)


@router.get(
    "/purchase-orders/export",
    summary="导出采购订单月度汇总 Excel",
    description="按采购分类、年份和月份导出整月已审批通过的采购申请明细 Excel。",
)
async def export_purchase_order_records(
    current_user: CurrentUser,
    category: PurchaseRequestCategory | None = Query(None, description="采购分类"),
    year: int = Query(..., ge=2000, le=2100, description="年份"),
    month: int = Query(..., ge=1, le=12, description="月份"),
    db: AsyncSession = Depends(get_db),
):
    xlsx_bytes = await export_purchase_order_lines_xlsx(
        db,
        category=category.value if category else None,
        year=year,
        month=month,
    )
    category_label = (
        PURCHASE_CATEGORY_LABELS.get(category.value, category.value)
        if category
        else "全部类别"
    )
    filename = f"采购订单_{category_label}_{year}-{month:02d}.xlsx"
    encoded_filename = quote(filename, safe="")
    return Response(
        content=xlsx_bytes,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": f"attachment; filename*=utf-8''{encoded_filename}"
        },
    )


@router.get(
    "/purchase-requests",
    summary="查询采购申请",
    description="按采购分类、流程状态、审批角色或申购部门关键词查询采购申请。",
    response_model=PurchaseRequestListResponse,
)
async def list_purchase_request_records(
    current_user: CurrentUser,
    category: PurchaseRequestCategory | None = Query(None, description="采购分类"),
    status: PurchaseRequestStatus | None = Query(None, description="流程状态"),
    approval_role: PurchaseApprovalRole | None = Query(
        None,
        description="审批角色。与 approval_view 一起筛选该角色的审批列表。",
    ),
    approval_view: PurchaseApprovalView = Query(
        PurchaseApprovalView.pending,
        description="审批视图：待审批、审批完成或审批驳回。",
    ),
    keyword: str | None = Query(None, description="申购部门关键词"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    db: AsyncSession = Depends(get_db),
):
    requests, total = await list_purchase_requests(
        db,
        category=category.value if category else None,
        status=status.value if status else None,
        approval_role=approval_role,
        approval_view=approval_view,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    data = [request.model_dump(mode="json") for request in requests]
    return paginated_response(data, page, page_size, total)


@router.post(
    "/purchase-requests",
    summary="创建采购申请",
    description="保存采购申请草稿，并按数量和单价自动计算明细总额与合计。",
    response_model=PurchaseRequestApiResponse,
)
async def create_purchase_request_record(
    current_user: CurrentUser,
    payload: PurchaseRequestCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        request = await create_purchase_request(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return success_response(
        data=request.model_dump(mode="json"),
        message="采购申请已保存",
    )


@router.get(
    "/purchase-requests/{request_id}",
    summary="获取采购申请详情",
    response_model=PurchaseRequestApiResponse,
)
async def get_purchase_request_record(
    current_user: CurrentUser,
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    try:
        request = await get_purchase_request(db, request_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return success_response(data=request.model_dump(mode="json"))


@router.put(
    "/purchase-requests/{request_id}",
    summary="更新采购申请",
    description="仅草稿或已驳回的采购申请允许编辑。",
    response_model=PurchaseRequestApiResponse,
)
async def update_purchase_request_record(
    current_user: CurrentUser,
    request_id: UUID,
    payload: PurchaseRequestUpdate,
    db: AsyncSession = Depends(get_db),
):
    try:
        request = await update_purchase_request(db, request_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return success_response(
        data=request.model_dump(mode="json"),
        message="采购申请已更新",
    )


@router.post(
    "/purchase-requests/{request_id}/submit",
    summary="提交采购申请",
    description="将采购申请提交到部门负责人审批。",
    response_model=PurchaseRequestApiResponse,
)
async def submit_purchase_request_record(
    current_user: CurrentUser,
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    try:
        request = await submit_purchase_request(db, request_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return success_response(
        data=request.model_dump(mode="json"),
        message="采购申请已提交",
    )


@router.post(
    "/purchase-requests/{request_id}/approve",
    summary="通过采购申请审批",
    response_model=PurchaseRequestApiResponse,
)
async def approve_purchase_request_record(
    current_user: CurrentUser,
    request_id: UUID,
    payload: PurchaseApprovalRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        request = await approve_purchase_request(db, request_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return success_response(data=request.model_dump(mode="json"), message="审批已通过")


@router.post(
    "/purchase-requests/{request_id}/reject",
    summary="驳回采购申请审批",
    response_model=PurchaseRequestApiResponse,
)
async def reject_purchase_request_record(
    current_user: CurrentUser,
    request_id: UUID,
    payload: PurchaseApprovalRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        request = await reject_purchase_request(db, request_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return success_response(data=request.model_dump(mode="json"), message="审批已驳回")


@router.get(
    "/contracts/templates/{category}",
    summary="获取采购合同模板字段",
    description="返回指定合同分类的可填写字段，用于前端动态展示合同生成表单。",
    response_model=ContractTemplateMetadata,
)
async def get_contract_template(category: ContractCategory, current_user: CurrentUser):
    metadata = get_contract_template_metadata(category)
    return success_response(data=metadata.model_dump(mode="json"))


@router.post(
    "/contracts/generate",
    summary="生成采购合同",
    description="根据合同分类、基础信息、供应商信息和明细行生成 Word 合同。",
)
async def create_contract(payload: ContractGenerateRequest, current_user: CurrentUser):
    try:
        buffer, filename, media_type = generate_contract(payload)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    encoded_filename = quote(filename, safe="")
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename*=utf-8''{encoded_filename}"
        },
    )
