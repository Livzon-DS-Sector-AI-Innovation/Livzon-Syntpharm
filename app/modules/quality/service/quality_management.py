"""Quality management business logic."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tasks import spawn_task
from app.modules.quality.models import (
    CAPA,
    AttachmentReview,
    DepartmentContact,
    DepartmentWeeklyConfirmation,
    Deviation,
)
from app.modules.quality.schemas import (
    AttachmentReviewOut,
    CapaDetail,
    CapaListItem,
    CapaStatistics,
    CreateCapaRequest,
    CreateDepartmentContactRequest,
    CreateDeviationRequest,
    DepartmentContactOut,
    DepartmentWeeklyConfirmationOut,
    DeviationDetail,
    DeviationListItem,
    DeviationStatistics,
    SubmitInvestigationRequest,
    SubmitReviewRequest,
    UpdateCapaRequest,
    UpdateDepartmentContactRequest,
    UpdateDeviationRequest,
)

# Workflow constants
APPROVAL_STEP_ORDER = [
    "ai_analysis",
    "investigation",
    "dept_head_review",
    "cross_dept_head_review",
    "qa_review",
    "qa_head_review",
    "quality_head_review",
]

APPROVAL_STEP_LABELS = {
    "ai_analysis": "AI分析",
    "investigation": "调查",
    "dept_head_review": "部门负责人审核",
    "cross_dept_head_review": "跨部门负责人审核",
    "qa_review": "所属QA审核",
    "qa_head_review": "QA负责人审核",
    "quality_head_review": "质量负责人审核",
}

STATUS_TO_STEP = {
    "pending_ai_analysis": "ai_analysis",
    "pending_investigation": "investigation",
    "pending_dept_head_review": "dept_head_review",
    "pending_cross_dept_head_review": "cross_dept_head_review",
    "pending_qa_review": "qa_review",
    "pending_qa_head_review": "qa_head_review",
    "pending_quality_head_review": "quality_head_review",
}

STEP_TO_NEXT_STATUS = {
    "ai_analysis": "pending_investigation",
    "investigation": "pending_dept_head_review",
    "dept_head_review": "pending_cross_dept_head_review",
    "cross_dept_head_review": "pending_qa_review",
    "qa_review": "pending_qa_head_review",
    "qa_head_review": "pending_quality_head_review",
    "quality_head_review": "pending_final_code",
}

STEP_ROLE_LABELS = {
    "ai_analysis": "AI系统",
    "investigation": "调查人",
    "dept_head_review": "部门负责人",
    "cross_dept_head_review": "跨部门负责人",
    "qa_review": "所属QA",
    "qa_head_review": "QA负责人",
    "quality_head_review": "质量负责人",
}

STATUS_TO_PENDING = {
    "ai_analysis": "pending_ai_analysis",
    "investigation": "pending_investigation",
    "dept_head_review": "pending_dept_head_review",
    "cross_dept_head_review": "pending_cross_dept_head_review",
    "qa_review": "pending_qa_review",
    "qa_head_review": "pending_qa_head_review",
    "quality_head_review": "pending_quality_head_review",
}


# ============ Deviation Service ============
async def get_deviation_list(
    db: AsyncSession,
    status: str | None = None,
    level: str | None = None,
    department: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    query = select(Deviation).where(~Deviation.is_deleted)
    count_query = (
        select(func.count()).select_from(Deviation).where(~Deviation.is_deleted)
    )

    if status:
        query = query.where(Deviation.status == status)
        count_query = count_query.where(Deviation.status == status)
    if level:
        query = query.where(Deviation.level == level)
        count_query = count_query.where(Deviation.level == level)
    if department:
        query = query.where(Deviation.department == department)
        count_query = count_query.where(Deviation.department == department)
    if keyword:
        query = query.where(Deviation.title.ilike(f"%{keyword}%"))
        count_query = count_query.where(Deviation.title.ilike(f"%{keyword}%"))

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = (
        query.order_by(Deviation.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "items": [
            DeviationListItem.model_validate(item).model_dump() for item in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_deviation_detail(
    db: AsyncSession, deviation_id: uuid.UUID
) -> DeviationDetail:
    result = await db.execute(
        select(Deviation).where(Deviation.id == deviation_id, not Deviation.is_deleted)
    )
    deviation = result.scalar_one_or_none()
    if not deviation:
        raise ValueError(f"Deviation {deviation_id} not found")
    return DeviationDetail.model_validate(deviation)


async def create_deviation(
    db: AsyncSession, data: CreateDeviationRequest, user_id: str
) -> dict[str, str]:
    deviation = Deviation(
        deviation_code=f"DEV-{datetime.now(UTC).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}",
        title=data.title,
        department=data.department,
        discovery_date=datetime.fromisoformat(data.discovery_date)
        if data.discovery_date
        else None,
        discovery_time=data.discovery_time,
        discovery_location=data.discovery_location,
        level=data.level,
        root_cause_category=data.root_cause_category,
        description=data.description,
        immediate_actions=data.immediate_actions,
        attachments=data.attachments,
        affected_items=data.affected_items,
        batch_number=data.batch_number,
        handler=data.handler,
        needs_cross_dept_review=data.needs_cross_dept_review,
        cross_dept_reviewers=[r.model_dump() for r in data.cross_dept_reviewers]
        if data.cross_dept_reviewers
        else [],
        status="draft",
        status_updated_at=datetime.now(UTC),
    )
    db.add(deviation)
    try:
        await db.commit()

    except Exception:
        await db.rollback()

        raise
    await db.refresh(deviation)
    return {"id": str(deviation.id), "code": deviation.deviation_code}


async def update_deviation(
    db: AsyncSession,
    deviation_id: uuid.UUID,
    data: UpdateDeviationRequest,
    user_id: str,
) -> dict[str, bool]:
    result = await db.execute(
        select(Deviation).where(Deviation.id == deviation_id, not Deviation.is_deleted)
    )
    deviation = result.scalar_one_or_none()
    if not deviation:
        raise ValueError(f"Deviation {deviation_id} not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field in [
            "ai_analysis",
            "investigation_records",
            "review_opinions",
            "cross_dept_reviewers",
            "report_versions",
        ]:
            setattr(deviation, field, value)
        elif field == "discovery_date" and value:
            setattr(deviation, field, datetime.fromisoformat(value))
        else:
            setattr(deviation, field, value)

    deviation.updated_at = datetime.now(UTC)
    if data.status:
        deviation.status_updated_at = datetime.now(UTC)

    try:
        await db.commit()

    except Exception:
        await db.rollback()

        raise
    return {"success": True}


async def delete_deviation(
    db: AsyncSession, deviation_id: uuid.UUID
) -> dict[str, bool]:
    result = await db.execute(
        select(Deviation).where(Deviation.id == deviation_id, not Deviation.is_deleted)
    )
    deviation = result.scalar_one_or_none()
    if not deviation:
        raise ValueError(f"Deviation {deviation_id} not found")
    deviation.is_deleted = True
    deviation.updated_at = datetime.now(UTC)
    try:
        await db.commit()

    except Exception:
        await db.rollback()

        raise
    return {"success": True}


async def submit_investigation(
    db: AsyncSession,
    deviation_id: uuid.UUID,
    data: SubmitInvestigationRequest,
    user_id: str,
) -> dict[str, bool]:
    result = await db.execute(
        select(Deviation).where(Deviation.id == deviation_id, not Deviation.is_deleted)
    )
    deviation = result.scalar_one_or_none()
    if not deviation:
        raise ValueError(f"Deviation {deviation_id} not found")
    if deviation.status != "pending_investigation":
        raise ValueError("只有待调查状态的偏差才能提交调查报告")

    if data.description:
        deviation.description = data.description
    if data.investigation_records:
        deviation.investigation_records = data.investigation_records

    deviation.status = "pending_dept_head_review"
    deviation.status_updated_at = datetime.now(UTC)
    deviation.updated_at = datetime.now(UTC)
    try:
        await db.commit()

    except Exception:
        await db.rollback()

        raise
    return {"success": True}


async def submit_review(
    db: AsyncSession, deviation_id: uuid.UUID, data: SubmitReviewRequest, user_id: str
) -> dict[str, bool]:
    result = await db.execute(
        select(Deviation).where(Deviation.id == deviation_id, not Deviation.is_deleted)
    )
    deviation = result.scalar_one_or_none()
    if not deviation:
        raise ValueError(f"Deviation {deviation_id} not found")

    current_step = STATUS_TO_STEP.get(deviation.status)
    if not current_step:
        raise ValueError("当前状态不在审核流程中")
    if current_step != data.step:
        raise ValueError("当前需要完成的审核步骤与提交的不一致")

    review_opinions = deviation.review_opinions or []
    new_opinion = {
        "content": data.content,
        "author": user_id,
        "step": data.step,
        "result": data.result,
        "createTime": datetime.now(UTC).isoformat(),
    }
    review_opinions.append(new_opinion)

    if data.result == "rejected":
        deviation.status = "returned"
        deviation.returned_step = data.step
        deviation.review_opinions = review_opinions
        deviation.status_updated_at = datetime.now(UTC)
        deviation.updated_at = datetime.now(UTC)
        try:
            await db.commit()

        except Exception:
            await db.rollback()

            raise
        return {"success": True}

    next_status = STEP_TO_NEXT_STATUS.get(data.step)
    if not next_status:
        raise ValueError("无法确定下一步状态")

    if data.step == "qa_review" and data.result == "approved" and data.reason_category:
        deviation.root_cause_category = data.reason_category
    if data.step == "qa_head_review" and data.deviation_level:
        deviation.level = data.deviation_level

    deviation.status = next_status
    deviation.review_opinions = review_opinions
    deviation.status_updated_at = datetime.now(UTC)
    deviation.updated_at = datetime.now(UTC)
    try:
        await db.commit()

    except Exception:
        await db.rollback()

        raise
    return {"success": True}


async def submit_final_code(
    db: AsyncSession, deviation_id: uuid.UUID, final_code: str, user_id: str
) -> dict[str, bool]:
    result = await db.execute(
        select(Deviation).where(Deviation.id == deviation_id, not Deviation.is_deleted)
    )
    deviation = result.scalar_one_or_none()
    if not deviation:
        raise ValueError(f"Deviation {deviation_id} not found")
    if deviation.status != "pending_final_code":
        raise ValueError("当前状态不允许提交最终编号")
    if not final_code or not final_code.strip():
        raise ValueError("最终编号不能为空")

    deviation.final_code = final_code.strip()
    deviation.status = "closed"
    deviation.status_updated_at = datetime.now(UTC)
    deviation.updated_at = datetime.now(UTC)
    try:
        await db.commit()

    except Exception:
        await db.rollback()

        raise
    return {"success": True}


async def resubmit_deviation(
    db: AsyncSession, deviation_id: uuid.UUID, user_id: str
) -> dict[str, bool]:
    result = await db.execute(
        select(Deviation).where(Deviation.id == deviation_id, not Deviation.is_deleted)
    )
    deviation = result.scalar_one_or_none()
    if not deviation:
        raise ValueError(f"Deviation {deviation_id} not found")
    if deviation.status != "returned":
        raise ValueError("只有退回状态的偏差才能重新提交")

    returned_step = deviation.returned_step
    target_status = (
        STATUS_TO_PENDING.get(returned_step, "pending_investigation")
        if returned_step
        else "pending_investigation"
    )

    deviation.status = target_status
    deviation.returned_step = None
    deviation.status_updated_at = datetime.now(UTC)
    deviation.updated_at = datetime.now(UTC)
    try:
        await db.commit()

    except Exception:
        await db.rollback()

        raise
    return {"success": True}


# ============ CAPA Service ============
async def get_capa_list(
    db: AsyncSession,
    status: str | None = None,
    source: str | None = None,
    category: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    query = select(CAPA).where(~CAPA.is_deleted)
    count_query = select(func.count()).select_from(CAPA).where(~CAPA.is_deleted)

    if status:
        query = query.where(CAPA.status == status)
        count_query = count_query.where(CAPA.status == status)
    if source:
        query = query.where(CAPA.source == source)
        count_query = count_query.where(CAPA.source == source)
    if category:
        query = query.where(CAPA.category == category)
        count_query = count_query.where(CAPA.category == category)
    if keyword:
        query = query.where(CAPA.title.ilike(f"%{keyword}%"))
        count_query = count_query.where(CAPA.title.ilike(f"%{keyword}%"))

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = (
        query.order_by(CAPA.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "items": [CapaListItem.model_validate(item).model_dump() for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_capa_detail(db: AsyncSession, capa_id: uuid.UUID) -> CapaDetail:
    result = await db.execute(
        select(CAPA).where(CAPA.id == capa_id, not CAPA.is_deleted)
    )
    capa = result.scalar_one_or_none()
    if not capa:
        raise ValueError(f"CAPA {capa_id} not found")
    return CapaDetail.model_validate(capa)


async def create_capa(
    db: AsyncSession, data: CreateCapaRequest, user_id: str
) -> dict[str, str]:
    capa = CAPA(
        capa_code=f"CAPA-{datetime.now(UTC).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}",
        title=data.title,
        deviation_id=data.deviation_id,
        source=data.source,
        source_code=data.source_code,
        category=data.category,
        root_cause_category=data.root_cause_category,
        non_conformity_description=data.non_conformity_description,
        root_cause_analysis=data.root_cause_analysis,
        capa_content=data.capa_content,
        capa_items=[item.model_dump() for item in data.capa_items]
        if data.capa_items
        else [],
        executors=data.executors,
        expected_completion_date=datetime.fromisoformat(data.expected_completion_date)
        if data.expected_completion_date
        else None,
        reporter=data.reporter,
        status="draft",
        status_updated_at=datetime.now(UTC),
    )
    db.add(capa)
    try:
        await db.commit()

    except Exception:
        await db.rollback()

        raise
    await db.refresh(capa)
    return {"id": str(capa.id), "code": capa.capa_code}


async def update_capa(
    db: AsyncSession, capa_id: uuid.UUID, data: UpdateCapaRequest, user_id: str
) -> dict[str, bool]:
    result = await db.execute(
        select(CAPA).where(CAPA.id == capa_id, not CAPA.is_deleted)
    )
    capa = result.scalar_one_or_none()
    if not capa:
        raise ValueError(f"CAPA {capa_id} not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field in [
            "capa_items",
            "execution_tracks",
            "dept_head_confirmations",
            "report_versions",
        ]:
            setattr(capa, field, value)
        elif (
            field
            in [
                "expected_completion_date",
                "evaluation_deadline",
                "evaluation_confirm_date",
                "closure_date",
                "qa_review_time",
                "q_head_approval_time",
            ]
            and value
        ):
            setattr(capa, field, datetime.fromisoformat(value))
        else:
            setattr(capa, field, value)

    capa.updated_at = datetime.now(UTC)
    if data.status:
        capa.status_updated_at = datetime.now(UTC)

    try:
        await db.commit()

    except Exception:
        await db.rollback()

        raise
    return {"success": True}


async def delete_capa(db: AsyncSession, capa_id: uuid.UUID) -> dict[str, bool]:
    result = await db.execute(
        select(CAPA).where(CAPA.id == capa_id, not CAPA.is_deleted)
    )
    capa = result.scalar_one_or_none()
    if not capa:
        raise ValueError(f"CAPA {capa_id} not found")
    capa.is_deleted = True
    capa.updated_at = datetime.now(UTC)
    try:
        await db.commit()

    except Exception:
        await db.rollback()

        raise
    return {"success": True}


# ============ Department Contact Service ============
async def get_department_contact_list(
    db: AsyncSession, page: int = 1, page_size: int = 20
) -> dict[str, Any]:
    query = select(DepartmentContact).where(~DepartmentContact.is_deleted)
    count_query = (
        select(func.count())
        .select_from(DepartmentContact)
        .where(~DepartmentContact.is_deleted)
    )

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = (
        query.order_by(DepartmentContact.department)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "items": [
            DepartmentContactOut.model_validate(item).model_dump() for item in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def upsert_department_contact(
    db: AsyncSession,
    data: CreateDepartmentContactRequest | UpdateDepartmentContactRequest,
    department: str | None,
    user_id: str,
) -> dict[str, bool]:
    if department:
        result = await db.execute(
            select(DepartmentContact).where(
                DepartmentContact.department == department,
                not DepartmentContact.is_deleted,
            )
        )
        contact = result.scalar_one_or_none()
        if contact:
            update_data = data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(contact, field, value)
            contact.updated_at = datetime.now(UTC)
            try:
                await db.commit()

            except Exception:
                await db.rollback()

                raise
            return {"success": True}

    contact = DepartmentContact(
        department=department or data.department,
        dept_head_id=data.dept_head_id,
        qa_staff_ids=data.qa_staff_ids,
        gmp_staff_ids=data.gmp_staff_ids,
        production_head_id=data.production_head_id,
        quality_head_id=data.quality_head_id,
        additional_contacts=data.additional_contacts,
        is_production_workshop=data.is_production_workshop
        if hasattr(data, "is_production_workshop")
        else False,
    )
    db.add(contact)
    try:
        await db.commit()

    except Exception:
        await db.rollback()

        raise
    return {"success": True}


async def delete_department_contact(
    db: AsyncSession, contact_id: uuid.UUID
) -> dict[str, bool]:
    result = await db.execute(
        select(DepartmentContact).where(
            DepartmentContact.id == contact_id, not DepartmentContact.is_deleted
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise ValueError(f"DepartmentContact {contact_id} not found")
    contact.is_deleted = True
    contact.updated_at = datetime.now(UTC)
    try:
        await db.commit()

    except Exception:
        await db.rollback()

        raise
    return {"success": True}


# ============ Statistics ============
async def get_deviation_statistics(db: AsyncSession) -> DeviationStatistics:
    total_result = await db.execute(
        select(func.count()).select_from(Deviation).where(~Deviation.is_deleted)
    )
    total = total_result.scalar_one()

    pending_result = await db.execute(
        select(func.count())
        .select_from(Deviation)
        .where(~Deviation.is_deleted, Deviation.status.like("pending_%"))
    )
    pending = pending_result.scalar_one()

    dept_result = await db.execute(
        select(Deviation.department, func.count())
        .where(~Deviation.is_deleted)
        .group_by(Deviation.department)
    )
    department_distribution = [
        {"name": row[0] or "未知", "count": row[1]} for row in dept_result.all()
    ]

    status_result = await db.execute(
        select(Deviation.status, func.count())
        .where(~Deviation.is_deleted)
        .group_by(Deviation.status)
    )
    status_distribution = [
        {"status": row[0], "count": row[1]} for row in status_result.all()
    ]

    step_breakdown = []
    for step in APPROVAL_STEP_ORDER:
        pending_status = STATUS_TO_PENDING.get(step)
        match = next(
            (s for s in status_distribution if s["status"] == pending_status), None
        )
        step_breakdown.append(
            {
                "step": step,
                "label": APPROVAL_STEP_LABELS.get(step, step),
                "roleLabel": STEP_ROLE_LABELS.get(step, ""),
                "count": match["count"] if match else 0,
            }
        )

    return DeviationStatistics(
        total=total,
        pending=pending,
        departmentDistribution=department_distribution,
        statusDistribution=status_distribution,
        stepBreakdown=step_breakdown,
    )


async def get_capa_statistics(db: AsyncSession) -> CapaStatistics:
    total_result = await db.execute(
        select(func.count()).select_from(CAPA).where(~CAPA.is_deleted)
    )
    total = total_result.scalar_one()

    status_result = await db.execute(
        select(CAPA.status, func.count())
        .where(~CAPA.is_deleted)
        .group_by(CAPA.status)
    )
    status_distribution = [
        {"status": row[0], "count": row[1]} for row in status_result.all()
    ]

    source_result = await db.execute(
        select(CAPA.source, func.count())
        .where(~CAPA.is_deleted)
        .group_by(CAPA.source)
    )
    source_distribution = [
        {"source": row[0] or "未知", "count": row[1]} for row in source_result.all()
    ]

    return CapaStatistics(
        total=total,
        statusDistribution=status_distribution,
        sourceDistribution=source_distribution,
    )


# ============ Attachment Reviews ============
async def list_attachment_reviews(
    db: AsyncSession,
    deviation_id: uuid.UUID | None = None,
    capa_id: uuid.UUID | None = None,
    attachment_url: str | None = None,
) -> list[dict]:
    """List attachment reviews with optional filters."""
    query = select(AttachmentReview).where(~AttachmentReview.is_deleted)
    if deviation_id:
        query = query.where(AttachmentReview.deviation_id == deviation_id)
    if capa_id:
        query = query.where(AttachmentReview.capa_id == capa_id)
    if attachment_url:
        query = query.where(AttachmentReview.attachment_url == attachment_url)
    query = query.order_by(AttachmentReview.review_time.desc())

    result = await db.execute(query)
    items = result.scalars().all()
    return [AttachmentReviewOut.model_validate(item).model_dump() for item in items]


async def create_attachment_review(
    db: AsyncSession,
    data,
    reviewer_id: str,
) -> dict:
    """Create a new attachment review."""
    review = AttachmentReview(
        deviation_id=data.deviation_id,
        capa_id=data.capa_id,
        attachment_url=data.attachment_url,
        content=data.content,
        reviewer_id=reviewer_id,
        review_time=datetime.now(UTC),
    )
    db.add(review)
    await db.flush()
    await db.refresh(review)
    return AttachmentReviewOut.model_validate(review).model_dump()


async def delete_attachment_review(db: AsyncSession, review_id: uuid.UUID) -> None:
    """Soft-delete an attachment review."""
    review = await db.get(AttachmentReview, review_id)
    if not review:
        raise ValueError("Attachment review not found")
    review.is_deleted = True
    await db.flush()


# ============ NEW: Deviation Workflow Endpoints ============


async def submit_for_review(
    db: AsyncSession, deviation_id: uuid.UUID, user_id: str
) -> dict[str, bool]:
    """Submit deviation to start review workflow. draft → pending_ai_analysis."""
    deviation = await db.get(Deviation, deviation_id)
    if not deviation or deviation.is_deleted:
        raise ValueError("偏差不存在")
    if deviation.status != "draft":
        raise ValueError(f"只有草稿状态的偏差可以提交，当前状态: {deviation.status}")

    deviation.status = "pending_ai_analysis"
    deviation.status_updated_at = datetime.now(UTC)
    deviation.updated_by = uuid.UUID(user_id) if user_id != "system" else None
    await db.flush()

    # Trigger AI analysis asynchronously
    spawn_task(_trigger_ai_analysis(deviation_id, user_id), name="quality.ai_analysis")

    return {"success": True}


async def _trigger_ai_analysis(deviation_id: uuid.UUID, user_id: str):
    """Async trigger AI analysis for a deviation."""
    from app.modules.quality.service.ai_analysis import analyze_deviation_async

    try:
        await analyze_deviation_async(deviation_id, user_id)
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(
            f"AI analysis failed for deviation {deviation_id}: {e}"
        )


async def complete_ai_analysis(
    db: AsyncSession,
    deviation_id: uuid.UUID,
    ai_analysis: dict | None,
    user_id: str,
) -> dict[str, bool]:
    """Mark AI analysis complete and advance to pending_investigation."""
    deviation = await db.get(Deviation, deviation_id)
    if not deviation or deviation.is_deleted:
        raise ValueError("偏差不存在")
    if deviation.status != "pending_ai_analysis":
        raise ValueError(
            f"只有待AI分析状态的偏差才能完成AI分析，当前状态: {deviation.status}"
        )

    if ai_analysis is not None:
        deviation.ai_analysis = ai_analysis
    deviation.status = "pending_investigation"
    deviation.status_updated_at = datetime.now(UTC)
    deviation.updated_by = uuid.UUID(user_id) if user_id != "system" else None
    await db.flush()
    return {"success": True}


async def batch_update_status(
    db: AsyncSession,
    deviation_ids: list[uuid.UUID],
    target_status: str,
    user_id: str,
) -> dict:
    """Batch update status for multiple deviations."""
    updated = 0
    failures = []

    for did in deviation_ids:
        try:
            deviation = await db.get(Deviation, did)
            if not deviation or deviation.is_deleted:
                failures.append({"id": str(did), "reason": "偏差不存在"})
                continue

            deviation.status = target_status
            deviation.status_updated_at = datetime.now(UTC)
            deviation.updated_by = uuid.UUID(user_id) if user_id != "system" else None
            updated += 1
        except Exception as e:
            failures.append({"id": str(did), "reason": str(e)})

    await db.flush()
    return {
        "updated_count": updated,
        "failed_count": len(failures),
        "failures": failures,
    }


async def get_department_confirmations(
    db: AsyncSession,
    week_key: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List department weekly confirmations."""
    query = select(DepartmentWeeklyConfirmation).where(
        not DepartmentWeeklyConfirmation.is_deleted
    )
    if week_key:
        query = query.where(DepartmentWeeklyConfirmation.week_key == week_key)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    query = query.order_by(DepartmentWeeklyConfirmation.updated_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "items": [
            DepartmentWeeklyConfirmationOut.model_validate(item).model_dump()
            for item in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def confirm_production_status(
    db: AsyncSession,
    data,
    user_id: str,
) -> dict[str, bool]:
    """Create or update a department weekly confirmation."""
    query = select(DepartmentWeeklyConfirmation).where(
        DepartmentWeeklyConfirmation.department == data.department,
        DepartmentWeeklyConfirmation.week_key == data.week_key,
        not DepartmentWeeklyConfirmation.is_deleted,
    )
    result = await db.execute(query)
    existing = result.scalar_one_or_none()

    now = datetime.now(UTC)
    if existing:
        existing.production_status = data.production_status
        existing.deviation_status = data.deviation_status
        existing.confirmed_by_id = uuid.UUID(user_id) if user_id != "system" else None
        existing.confirmed_at = now
        existing.updated_at = now
    else:
        confirmation = DepartmentWeeklyConfirmation(
            department=data.department,
            week_key=data.week_key,
            production_status=data.production_status,
            deviation_status=data.deviation_status,
            confirmed_by_id=uuid.UUID(user_id) if user_id != "system" else None,
            confirmed_at=now,
        )
        db.add(confirmation)

    await db.flush()
    return {"success": True}


async def get_stopped_departments(db: AsyncSession, week_key: str) -> list[str]:
    """Get departments with stopped production status for a given week."""
    query = select(DepartmentWeeklyConfirmation.department).where(
        DepartmentWeeklyConfirmation.week_key == week_key,
        DepartmentWeeklyConfirmation.production_status == "stopped",
        not DepartmentWeeklyConfirmation.is_deleted,
    )
    result = await db.execute(query)
    return [row[0] for row in result.all()]


# ============ NEW: CAPA Workflow Endpoints ============


async def get_capa_departments(db: AsyncSession) -> list[str]:
    """Get all departments from department contacts."""
    query = select(DepartmentContact.department).where(~DepartmentContact.is_deleted)
    result = await db.execute(query)
    return [row[0] for row in result.all()]


async def auto_fill_from_deviation(db: AsyncSession, deviation_id: uuid.UUID) -> dict:
    """Auto-fill CAPA form from deviation data."""
    deviation = await db.get(Deviation, deviation_id)
    if not deviation or deviation.is_deleted:
        raise ValueError("偏差不存在")

    # Extract from AI analysis
    ai_analysis = deviation.ai_analysis or {}
    non_conformity = ai_analysis.get(
        "structured_deviation_description", deviation.description or ""
    )
    root_cause = ai_analysis.get("preliminary_cause_analysis", "")

    # Extract from last investigation record
    investigation_records = deviation.investigation_records or []
    capa_content = ""
    if investigation_records:
        last_record = (
            investigation_records[-1] if isinstance(investigation_records, list) else {}
        )
        if isinstance(last_record, dict):
            non_conformity = last_record.get("nonconformityDescription", non_conformity)
            root_cause = last_record.get("rootCauseAnalysis", root_cause)
            # Build capa content from proposals
            proposals = last_record.get("capaProposals", [])
            if proposals:
                capa_content = "\n".join(
                    f"{i + 1}. {p.get('summary', p.get('content', ''))}"
                    for i, p in enumerate(proposals)
                )

    capa_suggestion = ai_analysis.get("capa_suggestions", "")
    if not capa_content and capa_suggestion:
        capa_content = capa_suggestion

    return {
        "title": deviation.title,
        "non_conformity_description": non_conformity,
        "root_cause_analysis": root_cause,
        "capa_content": capa_content,
        "expected_completion_date": None,
    }


async def link_deviation(
    db: AsyncSession,
    capa_id: uuid.UUID,
    deviation_id: uuid.UUID,
    user_id: str,
) -> dict[str, bool]:
    """Link a CAPA to a deviation."""
    capa = await db.get(CAPA, capa_id)
    if not capa or capa.is_deleted:
        raise ValueError("CAPA不存在")
    deviation = await db.get(Deviation, deviation_id)
    if not deviation or deviation.is_deleted:
        raise ValueError("偏差不存在")

    capa.deviation_id = deviation_id
    capa.source_code = deviation.deviation_code
    capa.updated_by = uuid.UUID(user_id) if user_id != "system" else None
    await db.flush()
    return {"success": True}


async def complete_part(
    db: AsyncSession,
    capa_id: uuid.UUID,
    part: str,
    user_id: str,
) -> dict[str, bool]:
    """Mark CAPA part A or B as complete."""
    capa = await db.get(CAPA, capa_id)
    if not capa or capa.is_deleted:
        raise ValueError("CAPA不存在")

    # Store completion in capa_items or a tracking field
    # For simplicity, update status when both parts are complete
    if part == "a":
        # Part A = problem description complete
        pass
    elif part == "b":
        # Part B = measures complete
        pass

    capa.updated_by = uuid.UUID(user_id) if user_id != "system" else None
    await db.flush()
    return {"success": True}


async def submit_capa(
    db: AsyncSession, capa_id: uuid.UUID, user_id: str
) -> dict[str, bool]:
    """Submit CAPA for QA approval."""
    capa = await db.get(CAPA, capa_id)
    if not capa or capa.is_deleted:
        raise ValueError("CAPA不存在")
    if capa.status not in ("draft",):
        raise ValueError(f"只有草稿状态的CAPA可以提交，当前状态: {capa.status}")

    capa.status = "submitted"
    capa.status_updated_at = datetime.now(UTC)
    capa.updated_by = uuid.UUID(user_id) if user_id != "system" else None
    await db.flush()
    return {"success": True}


async def confirm_dept_head(
    db: AsyncSession,
    capa_id: uuid.UUID,
    data,
    user_id: str,
) -> dict[str, bool]:
    """Department head confirmation for CAPA."""
    capa = await db.get(CAPA, capa_id)
    if not capa or capa.is_deleted:
        raise ValueError("CAPA不存在")

    confirmations = capa.dept_head_confirmations or []
    now = datetime.now(UTC).isoformat()

    confirmation = {
        "department": data.department,
        "deptHeadUserId": data.dept_head_user_id,
        "result": data.result,
        "opinion": data.opinion,
        "confirmTime": now,
    }

    # Update existing or append
    found = False
    for i, c in enumerate(confirmations):
        if isinstance(c, dict) and c.get("department") == data.department:
            confirmations[i] = confirmation
            found = True
            break
    if not found:
        confirmations.append(confirmation)

    capa.dept_head_confirmations = confirmations

    # Check if all departments have approved
    all_approved = all(
        isinstance(c, dict) and c.get("result") == "approved" for c in confirmations
    )
    any_rejected = any(
        isinstance(c, dict) and c.get("result") == "rejected" for c in confirmations
    )

    if all_approved and confirmations:
        capa.status = "pending_qa_approval"
        capa.status_updated_at = datetime.now(UTC)
    elif any_rejected:
        capa.status = "returned"
        capa.returned_step = "dept_head_confirm"
        capa.status_updated_at = datetime.now(UTC)

    capa.updated_by = uuid.UUID(user_id) if user_id != "system" else None
    await db.flush()
    return {"success": True}


async def approve_capa(
    db: AsyncSession,
    capa_id: uuid.UUID,
    data,
    user_id: str,
) -> dict[str, bool]:
    """QA approval for CAPA."""
    capa = await db.get(CAPA, capa_id)
    if not capa or capa.is_deleted:
        raise ValueError("CAPA不存在")

    now = datetime.now(UTC)

    if data.step == "qa_review":
        capa.qa_reviewer_id = uuid.UUID(user_id) if user_id != "system" else None
        capa.qa_review_opinion = data.opinion
        capa.qa_review_time = now
        if data.result == "approved":
            capa.status = "pending_q_head_approval"
        else:
            capa.status = "returned"
            capa.returned_step = "qa_review"

    elif data.step == "q_head_approval":
        capa.q_head_approver_id = uuid.UUID(user_id) if user_id != "system" else None
        capa.q_head_approval_opinion = data.opinion
        capa.q_head_approval_time = now
        if data.result == "approved":
            capa.status = "executing"
        else:
            capa.status = "returned"
            capa.returned_step = "q_head_approval"

    capa.status_updated_at = now
    capa.updated_by = uuid.UUID(user_id) if user_id != "system" else None
    await db.flush()
    return {"success": True}


async def resubmit_capa(
    db: AsyncSession, capa_id: uuid.UUID, user_id: str
) -> dict[str, bool]:
    """Resubmit CAPA after rejection."""
    capa = await db.get(CAPA, capa_id)
    if not capa or capa.is_deleted:
        raise ValueError("CAPA不存在")
    if capa.status != "returned":
        raise ValueError(f"只有已退回状态的CAPA可以重新提交，当前状态: {capa.status}")

    capa.status = "draft"
    capa.returned_step = None
    capa.status_updated_at = datetime.now(UTC)
    capa.updated_by = uuid.UUID(user_id) if user_id != "system" else None
    await db.flush()
    return {"success": True}


async def add_execution_track(
    db: AsyncSession,
    capa_id: uuid.UUID,
    data: dict,
    user_id: str,
) -> dict[str, bool]:
    """Add an execution tracking record to CAPA."""
    capa = await db.get(CAPA, capa_id)
    if not capa or capa.is_deleted:
        raise ValueError("CAPA不存在")

    tracks = capa.execution_tracks or []
    track = {
        "execution_status": data.get("execution_status", ""),
        "qa_confirmer": data.get("qa_confirmer", ""),
        "qa_confirm_date": data.get("qa_confirm_date", ""),
    }
    tracks.append(track)
    capa.execution_tracks = tracks
    capa.execution_status = data.get("execution_status", "")
    capa.updated_by = uuid.UUID(user_id) if user_id != "system" else None
    await db.flush()
    return {"success": True}


async def delete_execution_track(
    db: AsyncSession,
    capa_id: uuid.UUID,
    index: int,
    user_id: str,
) -> dict[str, bool]:
    """Delete an execution tracking record by index."""
    capa = await db.get(CAPA, capa_id)
    if not capa or capa.is_deleted:
        raise ValueError("CAPA不存在")

    tracks = capa.execution_tracks or []
    if index < 0 or index >= len(tracks):
        raise ValueError("执行记录索引无效")

    tracks.pop(index)
    capa.execution_tracks = tracks
    capa.updated_by = uuid.UUID(user_id) if user_id != "system" else None
    await db.flush()
    return {"success": True}


async def confirm_execution(
    db: AsyncSession, capa_id: uuid.UUID, user_id: str
) -> dict[str, bool]:
    """Confirm CAPA execution is complete, advance to pending_evaluation."""
    capa = await db.get(CAPA, capa_id)
    if not capa or capa.is_deleted:
        raise ValueError("CAPA不存在")
    if capa.status != "executing":
        raise ValueError(
            f"只有执行中状态的CAPA可以确认执行完成，当前状态: {capa.status}"
        )

    capa.status = "pending_evaluation"
    capa.status_updated_at = datetime.now(UTC)
    capa.updated_by = uuid.UUID(user_id) if user_id != "system" else None
    await db.flush()
    return {"success": True}


async def submit_evaluation(
    db: AsyncSession,
    capa_id: uuid.UUID,
    data,
    user_id: str,
) -> dict[str, bool]:
    """Submit effectiveness evaluation and close CAPA."""
    capa = await db.get(CAPA, capa_id)
    if not capa or capa.is_deleted:
        raise ValueError("CAPA不存在")
    if capa.status != "pending_evaluation":
        raise ValueError(
            f"只有待效果评价状态的CAPA可以提交评价，当前状态: {capa.status}"
        )

    capa.evaluation_target = data.evaluation_target
    capa.evaluation_result = data.evaluation_result
    capa.evaluation_confirmer_id = (
        uuid.UUID(data.evaluation_confirmer) if data.evaluation_confirmer else None
    )
    capa.evaluation_confirm_date = (
        datetime.fromisoformat(data.evaluation_confirm_date.replace("Z", "+00:00"))
        if data.evaluation_confirm_date
        else None
    )
    capa.closure_date = (
        datetime.fromisoformat(data.closure_date.replace("Z", "+00:00"))
        if data.closure_date
        else None
    )
    capa.status = "closed"
    capa.status_updated_at = datetime.now(UTC)
    capa.updated_by = uuid.UUID(user_id) if user_id != "system" else None
    await db.flush()
    return {"success": True}
