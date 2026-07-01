"""Quality management API endpoints."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.core.exceptions import AppException, NotFoundException
from app.core.response import paginated_response, success_response
from app.modules.quality import service
from app.modules.quality.schemas import (
    BatchUpdateStatusRequest,
    CapaApprovalRequest,
    CapaDeptHeadConfirmRequest,
    CapaEvaluationRequest,
    CompleteAiAnalysisRequest,
    CompletePartRequest,
    ConfirmProductionStatusRequest,
    CreateAttachmentReviewRequest,
    CreateCapaRequest,
    CreateDepartmentContactRequest,
    CreateDeviationRequest,
    ExecutionTrack,
    LinkDeviationRequest,
    SubmitInvestigationRequest,
    SubmitReviewRequest,
    UpdateCapaRequest,
    UpdateDeviationRequest,
)

router = APIRouter()


# ============ Deviations ============


@router.get("/deviations", summary="获取偏差列表")
async def list_deviations(
    current_user: CurrentUser,
    status: str | None = None,
    level: str | None = None,
    department: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):

    result = await service.get_deviation_list(
        db, status, level, department, keyword, page, page_size
    )

    return paginated_response(
        data=result["items"],
        page=result["page"],
        page_size=result["page_size"],
        total=result["total"],
    )


@router.patch("/deviations/batch", summary="批量更新偏差状态")
async def batch_update_deviation_status(
    data: BatchUpdateStatusRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):

    result = await service.batch_update_status(
        db, data.deviation_ids, data.target_status, "system"
    )

    return success_response(data=result)


@router.get("/deviations/department-confirmations", summary="获取部门周确认列表")
async def list_department_confirmations(
    current_user: CurrentUser,
    week_key: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):

    result = await service.get_department_confirmations(db, week_key, page, page_size)

    return paginated_response(
        data=result["items"],
        page=result["page"],
        page_size=result["page_size"],
        total=result["total"],
    )


@router.post("/deviations/department-confirmations", summary="确认部门生产状态")
async def confirm_department_status(
    data: ConfirmProductionStatusRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):

    result = await service.confirm_production_status(db, data, "system")

    return success_response(data=result)


@router.get("/deviations/stopped-departments", summary="获取停产部门列表")
async def get_stopped_departments(
    week_key: str, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):

    departments = await service.get_stopped_departments(db, week_key)

    return success_response(data=departments)


@router.get("/deviations/{deviation_id}", summary="获取偏差详情")
async def get_deviation(
    deviation_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):

    try:
        detail = await service.get_deviation_detail(db, deviation_id)

        return success_response(data=detail.model_dump())

    except ValueError as e:
        raise NotFoundException(detail=str(e))


@router.post("/deviations", summary="创建偏差")
async def create_deviation(
    data: CreateDeviationRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):

    result = await service.create_deviation(db, data, "system")

    return success_response(data=result)


@router.put("/deviations/{deviation_id}", summary="更新偏差")
async def update_deviation(
    deviation_id: uuid.UUID,
    data: UpdateDeviationRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):

    try:
        result = await service.update_deviation(db, deviation_id, data, "system")

        return success_response(data=result)

    except ValueError as e:
        raise AppException(status_code=400, message=str(e))


@router.delete("/deviations/{deviation_id}", summary="删除偏差")
async def delete_deviation(
    deviation_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):

    try:
        result = await service.delete_deviation(db, deviation_id)

        return success_response(data=result)

    except ValueError as e:
        raise NotFoundException(detail=str(e))


@router.post("/deviations/{deviation_id}/submit", summary="提交偏差启动审核流程")
async def submit_deviation_for_review(
    deviation_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):

    try:
        result = await service.submit_for_review(db, deviation_id, "system")

        return success_response(data=result)

    except ValueError as e:
        raise AppException(status_code=400, message=str(e))


@router.post("/deviations/{deviation_id}/complete-ai-analysis", summary="完成AI分析")
async def complete_ai_analysis(
    deviation_id: uuid.UUID,
    data: CompleteAiAnalysisRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):

    try:
        result = await service.complete_ai_analysis(
            db, deviation_id, data.ai_analysis, "system"
        )

        return success_response(data=result)

    except ValueError as e:
        raise AppException(status_code=400, message=str(e))


@router.post("/deviations/{deviation_id}/submit-investigation", summary="提交调查报告")
async def submit_investigation(
    deviation_id: uuid.UUID,
    data: SubmitInvestigationRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):

    try:
        result = await service.submit_investigation(db, deviation_id, data, "system")

        return success_response(data=result)

    except ValueError as e:
        raise AppException(status_code=400, message=str(e))


@router.post("/deviations/{deviation_id}/submit-review", summary="提交审核意见")
async def submit_review(
    deviation_id: uuid.UUID,
    data: SubmitReviewRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):

    try:
        result = await service.submit_review(db, deviation_id, data, "system")

        return success_response(data=result)

    except ValueError as e:
        raise AppException(status_code=400, message=str(e))


@router.post("/deviations/{deviation_id}/submit-final-code", summary="提交最终编号")
async def submit_final_code(
    deviation_id: uuid.UUID,
    final_code: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):

    try:
        result = await service.submit_final_code(db, deviation_id, final_code, "system")

        return success_response(data=result)

    except ValueError as e:
        raise AppException(status_code=400, message=str(e))


@router.post("/deviations/{deviation_id}/resubmit", summary="重新提交偏差")
async def resubmit_deviation(
    deviation_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):

    try:
        result = await service.resubmit_deviation(db, deviation_id, "system")

        return success_response(data=result)

    except ValueError as e:
        raise AppException(status_code=400, message=str(e))


# ============ CAPAs ============


@router.get("/capas", summary="获取CAPA列表")
async def list_capas(
    current_user: CurrentUser,
    status: str | None = None,
    source: str | None = None,
    category: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):

    result = await service.get_capa_list(
        db, status, source, category, keyword, page, page_size
    )

    return paginated_response(
        data=result["items"],
        page=result["page"],
        page_size=result["page_size"],
        total=result["total"],
    )


@router.get("/capas/departments", summary="获取所有部门列表")
async def get_capa_departments(
    current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):

    departments = await service.get_capa_departments(db)

    return success_response(data=departments)


@router.get("/capas/auto-fill/{deviation_id}", summary="从偏差自动填充CAPA表单")
async def auto_fill_capa_from_deviation(
    deviation_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):

    try:
        result = await service.auto_fill_from_deviation(db, deviation_id)

        return success_response(data=result)

    except ValueError as e:
        raise NotFoundException(detail=str(e))


@router.get("/capas/{capa_id}", summary="获取CAPA详情")
async def get_capa(
    capa_id: uuid.UUID, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):

    try:
        detail = await service.get_capa_detail(db, capa_id)

        return success_response(data=detail.model_dump())

    except ValueError as e:
        raise NotFoundException(detail=str(e))


@router.post("/capas", summary="创建CAPA")
async def create_capa(
    data: CreateCapaRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):

    result = await service.create_capa(db, data, "system")

    return success_response(data=result)


@router.put("/capas/{capa_id}", summary="更新CAPA")
async def update_capa(
    capa_id: uuid.UUID,
    data: UpdateCapaRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):

    try:
        result = await service.update_capa(db, capa_id, data, "system")

        return success_response(data=result)

    except ValueError as e:
        raise AppException(status_code=400, message=str(e))


@router.delete("/capas/{capa_id}", summary="删除CAPA")
async def delete_capa(
    capa_id: uuid.UUID, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):

    try:
        result = await service.delete_capa(db, capa_id)

        return success_response(data=result)

    except ValueError as e:
        raise NotFoundException(detail=str(e))


@router.post("/capas/{capa_id}/link-deviation", summary="关联偏差到CAPA")
async def link_capa_to_deviation(
    capa_id: uuid.UUID,
    data: LinkDeviationRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):

    try:
        result = await service.link_deviation(db, capa_id, data.deviation_id, "system")

        return success_response(data=result)

    except ValueError as e:
        raise AppException(status_code=400, message=str(e))


@router.post("/capas/{capa_id}/complete-part", summary="完成CAPA部分")
async def complete_capa_part(
    capa_id: uuid.UUID,
    data: CompletePartRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):

    try:
        result = await service.complete_part(db, capa_id, data.part, "system")

        return success_response(data=result)

    except ValueError as e:
        raise AppException(status_code=400, message=str(e))


@router.post("/capas/{capa_id}/submit", summary="提交CAPA审核")
async def submit_capa_for_review(
    capa_id: uuid.UUID, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):

    try:
        result = await service.submit_capa(db, capa_id, "system")

        return success_response(data=result)

    except ValueError as e:
        raise AppException(status_code=400, message=str(e))


@router.post("/capas/{capa_id}/confirm-dept-head", summary="部门主管确认CAPA")
async def confirm_capa_by_dept_head(
    capa_id: uuid.UUID,
    data: CapaDeptHeadConfirmRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):

    try:
        result = await service.confirm_dept_head(db, capa_id, data, "system")

        return success_response(data=result)

    except ValueError as e:
        raise AppException(status_code=400, message=str(e))


@router.post("/capas/{capa_id}/approve", summary="QA审批CAPA")
async def approve_capa(
    capa_id: uuid.UUID,
    data: CapaApprovalRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):

    try:
        result = await service.approve_capa(db, capa_id, data, "system")

        return success_response(data=result)

    except ValueError as e:
        raise AppException(status_code=400, message=str(e))


@router.post("/capas/{capa_id}/resubmit", summary="重新提交CAPA")
async def resubmit_capa(
    capa_id: uuid.UUID, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):

    try:
        result = await service.resubmit_capa(db, capa_id, "system")

        return success_response(data=result)

    except ValueError as e:
        raise AppException(status_code=400, message=str(e))


@router.post("/capas/{capa_id}/add-execution-track", summary="添加CAPA执行记录")
async def add_capa_execution_track(
    capa_id: uuid.UUID,
    data: ExecutionTrack,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):

    try:
        result = await service.add_execution_track(
            db, capa_id, data.model_dump(), "system"
        )

        return success_response(data=result)

    except ValueError as e:
        raise AppException(status_code=400, message=str(e))


@router.post("/capas/{capa_id}/delete-execution-track", summary="删除CAPA执行记录")
async def delete_capa_execution_track(
    capa_id: uuid.UUID,
    index: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):

    try:
        result = await service.delete_execution_track(db, capa_id, index, "system")

        return success_response(data=result)

    except ValueError as e:
        raise AppException(status_code=400, message=str(e))


@router.post("/capas/{capa_id}/confirm-execution", summary="确认CAPA执行完成")
async def confirm_capa_execution(
    capa_id: uuid.UUID, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):

    try:
        result = await service.confirm_execution(db, capa_id, "system")

        return success_response(data=result)

    except ValueError as e:
        raise AppException(status_code=400, message=str(e))


@router.post("/capas/{capa_id}/submit-evaluation", summary="提交CAPA效果评价")
async def submit_capa_evaluation(
    capa_id: uuid.UUID,
    data: CapaEvaluationRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):

    try:
        result = await service.submit_evaluation(db, capa_id, data, "system")

        return success_response(data=result)

    except ValueError as e:
        raise AppException(status_code=400, message=str(e))


# ============ Department Contacts ============


@router.get("/department-contacts", summary="获取部门联系人列表")
async def list_department_contacts(
    current_user: CurrentUser,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):

    result = await service.get_department_contact_list(db, page, page_size)

    return paginated_response(
        data=result["items"],
        page=result["page"],
        page_size=result["page_size"],
        total=result["total"],
    )


@router.post("/department-contacts", summary="创建/更新部门联系人")
async def upsert_department_contact(
    data: CreateDepartmentContactRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):

    result = await service.upsert_department_contact(db, data, None, "system")

    return success_response(data=result)


@router.delete("/department-contacts/{contact_id}", summary="删除部门联系人")
async def delete_department_contact(
    contact_id: uuid.UUID, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):

    try:
        result = await service.delete_department_contact(db, contact_id)

        return success_response(data=result)

    except ValueError as e:
        raise NotFoundException(detail=str(e))


# ============ Statistics ============


@router.get("/statistics/deviations", summary="获取偏差统计")
async def get_deviation_statistics(
    current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):

    stats = await service.get_deviation_statistics(db)

    return success_response(data=stats.model_dump())


@router.get("/statistics/capas", summary="获取CAPA统计")
async def get_capa_statistics(
    current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):

    stats = await service.get_capa_statistics(db)

    return success_response(data=stats.model_dump())


# ============ Attachment Reviews ============


@router.get("/attachment-reviews", summary="获取附件审阅列表")
async def list_attachment_reviews(
    current_user: CurrentUser,
    deviation_id: uuid.UUID | None = None,
    capa_id: uuid.UUID | None = None,
    attachment_url: str | None = None,
    db: AsyncSession = Depends(get_db),
):

    items = await service.list_attachment_reviews(
        db, deviation_id, capa_id, attachment_url
    )

    return success_response(data=items)


@router.post("/attachment-reviews", summary="创建附件审阅")
async def create_attachment_review(
    data: CreateAttachmentReviewRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):

    result = await service.create_attachment_review(db, data, "system")

    return success_response(data=result)


@router.delete("/attachment-reviews/{review_id}", summary="删除附件审阅")
async def delete_attachment_review(
    review_id: uuid.UUID, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):

    try:
        await service.delete_attachment_review(db, review_id)

        return success_response(data={"success": True})

    except ValueError as e:
        raise NotFoundException(detail=str(e))
